> **Part of:** [data-observability](../SKILL.md)

# Alerting Patterns for Data Observability

Configurations for routing alerts from data monitors to notification channels. The goal is actionable signal with zero alert fatigue.

## Severity Levels (P0-P3 Classification)

| Severity | Definition | Response Time | Notification | Example |
|----------|-----------|---------------|--------------|---------|
| P0 | Complete data outage or corruption | 15 min | PagerDuty + Slack + Phone | Zero rows in production table, wrong data served to customers |
| P1 | Critical SLA breach | 1 hour | Slack alert channel + email | Dashboard data >24h stale, >50% volume drop |
| P2 | Warning threshold crossed | 4 hours | Slack warning channel | Schema change detected, volume deviation 30-50% |
| P3 | Informational / drift detected | Next business day | Slack info channel or log | Distribution drift, minor schema evolution |

---

## Dagster Alerting

**Freshness policies (asset-native monitoring):**
```python
from dagster import asset, FreshnessPolicy

@asset(
    freshness_policy=FreshnessPolicy(
        maximum_lag_minutes=60 * 24,  # 24-hour SLA
        cron_schedule="0 8 * * *",    # expect refresh by 8am
    )
)
def fct_orders():
    ...
```

**Slack integration via sensors:**
```python
from dagster import sensor, RunRequest
from dagster_slack import make_slack_on_run_failure_sensor

# Alert on any asset materialization failure
slack_failure_sensor = make_slack_on_run_failure_sensor(
    channel="#data-alerts",
    slack_token={"env": "SLACK_BOT_TOKEN"},  # SECURITY: token from env var only
    monitor_all_code_locations=True,
)
```

**Custom freshness sensor:**
```python
from dagster import sensor, SensorEvaluationContext

@sensor(minimum_interval_seconds=300)
def freshness_alert_sensor(context: SensorEvaluationContext):
    # Query freshness status from monitoring table
    stale_sources = check_freshness_slas()
    for source in stale_sources:
        send_slack_alert(
            channel="#data-alerts",
            message=f"STALE: {source['table']} last loaded {source['staleness']} ago (SLA: {source['sla']})"
        )
```

---

## Airflow Alerting

**Failure callbacks:**
```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def on_failure_callback(context):
    task_instance = context["task_instance"]
    slack_alert = SlackWebhookOperator(
        task_id="slack_alert",
        slack_webhook_conn_id="slack_webhook",
        message=f"Task Failed: {task_instance.task_id}\n"
                f"DAG: {task_instance.dag_id}\n"
                f"Execution: {context['execution_date']}\n"
                f"Log: {task_instance.log_url}",
    )
    slack_alert.execute(context=context)

# Apply to DAG
dag = DAG(
    "data_pipeline",
    default_args={"on_failure_callback": on_failure_callback},
    sla_miss_callback=sla_miss_alert,
)
```

**SLA miss alerting:**
```python
from datetime import timedelta

def sla_miss_alert(dag, task_list, blocking_task_list, slas, blocking_tis):
    send_slack_alert(
        channel="#data-alerts",
        message=f"SLA MISS: DAG {dag.dag_id} missed SLA. "
                f"Tasks: {[t.task_id for t in task_list]}"
    )

task = PythonOperator(
    task_id="transform_orders",
    sla=timedelta(hours=2),  # must complete within 2 hours
    ...
)
```

---

## Standalone Alerting (Slack Webhooks)

For pipelines without Dagster/Airflow:

```python
# alerting/slack_alerter.py
import requests
import json

class DataAlertSender:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url  # SECURITY: load from env var

    def send(self, severity: str, title: str, details: str, runbook_url: str = None):
        color_map = {"P0": "#FF0000", "P1": "#FF6600", "P2": "#FFCC00", "P3": "#0066FF"}
        payload = {
            "attachments": [{
                "color": color_map.get(severity, "#CCCCCC"),
                "title": f"[{severity}] {title}",
                "text": details,
                "fields": [
                    {"title": "Severity", "value": severity, "short": True},
                    {"title": "Runbook", "value": runbook_url or "N/A", "short": True},
                ],
                "footer": "data-observability | automated alert",
            }]
        }
        response = requests.post(self.webhook_url, json=payload, timeout=10)
        response.raise_for_status()
```

---

## Alert Fatigue Prevention

Rules to keep signal-to-noise ratio high:

**Deduplication:**
```python
# Do not re-alert for the same issue within cooldown window
ALERT_COOLDOWN = {
    "P0": 900,    # 15 minutes
    "P1": 3600,   # 1 hour
    "P2": 14400,  # 4 hours
    "P3": 86400,  # 24 hours
}
```

**Grouping rules:**
- Group multiple freshness alerts for the same source into one message
- Batch P2/P3 alerts into a daily digest instead of individual messages
- Suppress P3 alerts during weekends and holidays

**Escalation policy:**
```yaml
# observability/escalation_policy.yml
escalation:
  P0:
    - channel: "#data-alerts"
      delay_minutes: 0
    - channel: "pagerduty"
      delay_minutes: 5
    - channel: "#engineering-leads"
      delay_minutes: 15
  P1:
    - channel: "#data-alerts"
      delay_minutes: 0
    - channel: "email:data-team@company.com"
      delay_minutes: 30
  P2:
    - channel: "#data-warnings"
      delay_minutes: 0
  P3:
    - channel: "#data-info"
      delay_minutes: 0
      batch: daily_digest
```

---

## Runbook Generation

Every alert must link to a runbook. Template for runbook references:

```yaml
# observability/alert_runbooks.yml
alerts:
  - name: freshness_sla_breach
    severity: P1
    runbook: "docs/runbooks/freshness-breach.md"
    owner: data-team
    steps:
      - "Check orchestrator logs for failed runs"
      - "Verify source system availability"
      - "Trigger manual backfill if needed"
      - "Confirm data freshness restored"

  - name: volume_anomaly
    severity: P1
    runbook: "docs/runbooks/volume-anomaly.md"
    owner: data-team
    steps:
      - "Compare row count against 7-day baseline"
      - "Check for duplicate loads or partial loads"
      - "Verify upstream source system changes"
      - "Re-run pipeline if source is confirmed healthy"
```
