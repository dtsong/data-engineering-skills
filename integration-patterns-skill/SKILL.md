---
name: integration-patterns-skill
description: "Use when designing enterprise integrations — iPaaS platforms (Workato, MuleSoft, Boomi), API patterns, event-driven architectures, CDC, webhooks, Reverse ETL, or making systems talk to each other"
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# Integration Patterns Skill for Claude

This skill provides expert guidance for designing, implementing, and troubleshooting enterprise data integrations. Whether you're connecting SaaS applications, building event-driven architectures, implementing Change Data Capture pipelines, or selecting between iPaaS platforms and custom code, this skill helps you make informed architectural decisions and write production-ready integration code.

## When to Use This Skill

Activate this skill when:

- Designing integrations between SaaS platforms (Salesforce, NetSuite, Stripe, Workday, ServiceNow)
- Evaluating iPaaS platforms (Workato, MuleSoft, Boomi, Zapier, Tray.io) vs custom code
- Implementing Change Data Capture (CDC) with Debezium, Snowflake Streams, or BigQuery CDC
- Building event-driven architectures with Kafka, Google Pub/Sub, or AWS EventBridge
- Designing webhook receivers with signature verification and retry logic
- Implementing Reverse ETL or data activation patterns (Hightouch, Census, custom)
- Creating API integrations with pagination, rate limiting, and error handling
- Building data synchronization patterns between operational and analytical systems
- Implementing file-based integrations (S3/GCS → data warehouse patterns)
- Designing canonical data models and crosswalk tables for multi-system environments

Don't use this skill for:

- Basic REST API calls that Claude already knows how to handle
- BI tool configuration (Looker, Tableau, Power BI dashboards)
- dbt transformations and analytics engineering workflows
- Infrastructure provisioning (use Terraform/IaC skills instead)
- Database query optimization (use database-specific skills)

## Core Principles

**Loose Coupling**: Design integrations so systems can fail independently without cascading failures. Use message queues, event buses, and asynchronous patterns to decouple producers from consumers. Avoid tight bindings where one system's downtime immediately breaks another. Implement circuit breakers to prevent cascading failures.

**Idempotency**: Every integration operation must be safe to retry. Use idempotency keys for API requests, upsert patterns for database writes, and deduplication logic for event processing. Design systems assuming network failures and duplicate messages will occur. Track processed message IDs to prevent duplicate processing.

**Contract-First Design**: Define schemas, API contracts, and data models before writing implementation code. Use OpenAPI specs for REST APIs, Protocol Buffers for gRPC, Avro/JSON Schema for events. Version your contracts and implement backward-compatible changes. Enforce schema validation at system boundaries.

**Error Isolation**: Failures in one integration should not cascade to other systems. Implement dead letter queues for failed messages, separate retry logic per integration, and monitoring with clear failure boundaries. Use circuit breakers to prevent overwhelming downstream systems. Log errors with context for troubleshooting.

**Data Freshness Awareness**: Understand the SLA for each integration pattern. Real-time webhooks provide sub-second latency, CDC offers near-real-time updates, batch files may be hours old. Choose patterns based on business requirements, not technical preference. Monitor actual vs expected data freshness.

**Canonical Data Models**: Establish a shared vocabulary across systems using canonical models. Map external system schemas to your canonical model at integration boundaries. Maintain crosswalk tables for ID mapping between systems. Version your canonical models and handle schema evolution gracefully.

## Integration Pattern Decision Matrix

| Pattern | Latency | Volume | Complexity | Best For |
|---------|---------|--------|------------|----------|
| Request/Reply (REST, gRPC) | Low (ms-sec) | Low-Medium | Low | User-facing features, on-demand queries, CRUD operations |
| Pub/Sub Events | Low-Medium (sec) | High | Medium | Event notifications, microservice communication, fan-out patterns |
| CDC (Change Data Capture) | Low (sec) | High | Medium-High | Database replication, real-time analytics, audit logs |
| Batch/File-based | High (hours) | Very High | Low | Bulk data transfers, daily reports, large historical loads |
| Webhooks | Low (sec) | Medium | Medium | External system notifications, SaaS integrations, real-time alerts |
| Reverse ETL | Medium (min-hours) | Medium | Medium | Data activation, warehouse → CRM/marketing tools, enrichment |

## Pattern Catalog with Code Examples

### REST API Integration

```python
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Generator, Dict, Any

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def fetch_page(url: str, headers: Dict[str, str], params: Dict[str, Any]) -> Dict:
    """Fetch single page with exponential backoff retry."""
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def paginate_api(base_url: str, api_key: str) -> Generator[Dict, None, None]:
    """Paginate through cursor-based API."""
    headers = {"Authorization": f"Bearer {api_key}"}
    cursor = None

    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor

        data = fetch_page(base_url, headers, params)

        for item in data.get("results", []):
            yield item

        cursor = data.get("next_cursor")
        if not cursor:
            break

# Usage
for record in paginate_api("https://api.example.com/v1/customers", api_key="xxx"):
    process_record(record)
```

### gRPC Service

```protobuf
// customer_service.proto
syntax = "proto3";

package customer;

service CustomerService {
  rpc GetCustomer(GetCustomerRequest) returns (Customer);
  rpc StreamCustomers(StreamRequest) returns (stream Customer);
}

message GetCustomerRequest {
  string customer_id = 1;
}

message StreamRequest {
  google.protobuf.Timestamp since = 1;
}

message Customer {
  string id = 1;
  string email = 2;
  google.protobuf.Timestamp created_at = 3;
}
```

```python
# Python client
import grpc
from customer_pb2 import GetCustomerRequest
from customer_pb2_grpc import CustomerServiceStub

channel = grpc.insecure_channel('localhost:50051')
stub = CustomerServiceStub(channel)

request = GetCustomerRequest(customer_id="cust_123")
customer = stub.GetCustomer(request)
print(f"Customer: {customer.email}")
```

### Event-Driven Pub/Sub

```python
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
from datetime import datetime

# Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Wait for all replicas
    retries=3
)

def publish_event(topic: str, event: dict):
    """Publish event with error handling."""
    event['timestamp'] = datetime.utcnow().isoformat()
    future = producer.send(topic, value=event, key=event['id'].encode('utf-8'))

    try:
        record_metadata = future.get(timeout=10)
        print(f"Published to {record_metadata.topic}:{record_metadata.partition}")
    except KafkaError as e:
        print(f"Failed to publish: {e}")
        raise

# Consumer
consumer = KafkaConsumer(
    'customer.created',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='customer-sync',
    enable_auto_commit=False,
    auto_offset_reset='earliest'
)

processed_ids = set()  # Deduplication

for message in consumer:
    event = message.value
    event_id = event['id']

    if event_id in processed_ids:
        continue  # Skip duplicates

    try:
        process_customer_created(event)
        consumer.commit()
        processed_ids.add(event_id)
    except Exception as e:
        print(f"Processing failed: {e}")
        # Don't commit - will retry
```

### CDC with Debezium

```yaml
# docker-compose.yml
version: '3'
services:
  postgres:
    image: debezium/postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092

  debezium:
    image: debezium/connect:2.3
    depends_on:
      - kafka
      - postgres
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: debezium_configs
      OFFSET_STORAGE_TOPIC: debezium_offsets
```

```json
// Debezium connector config
{
  "name": "customers-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "mydb",
    "table.include.list": "public.customers,public.orders",
    "topic.prefix": "dbserver1",
    "plugin.name": "pgoutput",
    "publication.autocreate.mode": "filtered",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState"
  }
}
```

### Webhook Receiver

```python
from fastapi import FastAPI, Request, HTTPException, Header
import hmac
import hashlib
from typing import Optional

app = FastAPI()

WEBHOOK_SECRET = "your_webhook_secret"

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC signature from webhook provider."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """Handle Stripe webhook with signature verification."""
    payload = await request.body()

    if not stripe_signature or not verify_signature(payload, stripe_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_id = event.get("id")

    # Idempotency check
    if await is_event_processed(event_id):
        return {"status": "already_processed"}

    try:
        await process_stripe_event(event)
        await mark_event_processed(event_id)
        return {"status": "success"}
    except Exception as e:
        # Log error, will be retried by Stripe
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Processing failed")
```

### File-Based Integration

```sql
-- S3 → Snowflake pattern with staging and error handling
CREATE OR REPLACE STAGE s3_stage
  URL = 's3://my-bucket/incoming/'
  CREDENTIALS = (AWS_KEY_ID = 'xxx' AWS_SECRET_KEY = 'yyy');

CREATE OR REPLACE FILE FORMAT csv_format
  TYPE = CSV
  FIELD_DELIMITER = ','
  SKIP_HEADER = 1
  NULL_IF = ('NULL', 'null', '')
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

-- Stage with validation
CREATE OR REPLACE TABLE customers_staging (
  customer_id VARCHAR,
  email VARCHAR,
  created_at TIMESTAMP,
  _filename VARCHAR,
  _load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Load with error handling
COPY INTO customers_staging (customer_id, email, created_at, _filename)
FROM (
  SELECT
    $1, $2, $3,
    METADATA$FILENAME
  FROM @s3_stage
)
FILE_FORMAT = csv_format
PATTERN = '.*customers_.*\.csv'
ON_ERROR = CONTINUE
RETURN_FAILED_ONLY = TRUE;

-- Merge into production table with deduplication
MERGE INTO customers c
USING (
  SELECT DISTINCT
    customer_id,
    email,
    created_at
  FROM customers_staging
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _load_timestamp DESC) = 1
) s
ON c.customer_id = s.customer_id
WHEN MATCHED AND (c.email != s.email OR c.created_at != s.created_at) THEN
  UPDATE SET email = s.email, created_at = s.created_at, updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (customer_id, email, created_at, updated_at)
  VALUES (s.customer_id, s.email, s.created_at, CURRENT_TIMESTAMP());
```

## iPaaS Platform Decision Matrix

| Platform | Best For | Pricing Model | Complexity | When to Choose |
|----------|----------|---------------|------------|----------------|
| Workato | Business operations teams, pre-built connectors, rapid deployment | Per-task pricing, volume discounts | Low | Need 100+ connectors, business user self-service, quick time-to-value |
| MuleSoft | Enterprise API management, complex transformations, governance | License + runtime, expensive | High | Large enterprises, API-first architecture, need API gateway + integration |
| Boomi | Multi-cloud integrations, B2B/EDI, master data management | Per-connection pricing | Medium-High | B2B integrations, complex data mapping, need MDM capabilities |
| Zapier | Simple automations, SMB use cases, individual productivity | Per-task pricing, affordable | Very Low | Non-technical users, simple SaaS-to-SaaS, small scale (<10k tasks/mo) |
| Tray.io | Advanced logic, developer-friendly, flexible workflows | Per-task pricing, enterprise tier | Medium | Need custom logic, API-first connectors, technical teams |
| Custom Code | Unique requirements, cost optimization at scale, full control | Development + infrastructure costs | High | Non-standard integrations, high volume, need full control, have engineering team |

## Enterprise System Connector Patterns

### Salesforce
- Preferred API: Bulk API 2.0 for large data transfers, REST API for real-time operations
- Auth: OAuth 2.0 with refresh tokens, connected app with IP restrictions
- Rate Limits: 15,000 API calls/24h (varies by edition), Bulk API has separate limits
- Pagination: Use `nextRecordsUrl` for query results, batch API for bulk operations
- Best Practice: Use composite API to reduce API call consumption, implement query locators for large result sets

### NetSuite
- Preferred API: SuiteTalk (SOAP) for comprehensive access, RESTlet for custom endpoints
- Auth: Token-based authentication (TBA), avoid password-based auth
- Rate Limits: Governance points vary by account, monitor via `X-NetSuite-Governance` header
- Pagination: Saved search with pagination for large datasets, limit 1000 records per call
- Best Practice: Use SuiteQL for analytics queries, implement retry logic for concurrency limits

### Stripe
- Preferred API: REST API v1 with versioning header
- Auth: Secret keys for server-side, publishable keys for client-side, restricted keys for least privilege
- Rate Limits: 100 read/sec, 100 write/sec in test mode, much higher in production
- Pagination: Cursor-based with `starting_after` parameter, returns `has_more` flag
- Best Practice: Use webhooks for event-driven updates, implement idempotency keys for write operations

### Workday
- Preferred API: REST API for most operations, SOAP for legacy integrations
- Auth: OAuth 2.0 with refresh tokens, API client registration required
- Rate Limits: Varies by tenant, typically 10-20 requests/second
- Pagination: Limit/offset for REST, page-based for SOAP
- Best Practice: Use bulk loading for large data sets, implement incremental sync with effective dating

### ServiceNow
- Preferred API: REST Table API for CRUD, Import Set API for bulk loads
- Auth: Basic auth for scripts, OAuth 2.0 for integrations
- Rate Limits: Varies by instance size, monitor via `X-RateLimit-*` headers
- Pagination: Offset-based with `sysparm_limit` and `sysparm_offset`
- Best Practice: Use encoded queries for filtering, implement update sets for configuration changes

## Reverse ETL / Data Activation Patterns

Reverse ETL moves data from analytical warehouses back to operational systems, enabling data activation in CRMs, marketing tools, and customer-facing applications.

| Tool | Sync Modes | Warehouse Support | Pricing |
|------|------------|-------------------|---------|
| Hightouch | Upsert, mirror, append, custom SQL | Snowflake, BigQuery, Redshift, Databricks, Postgres | Per-row pricing, starts ~$500/mo |
| Census | Upsert, mirror, append, delete | Snowflake, BigQuery, Redshift, Databricks, Postgres | Per-row pricing, starts ~$1000/mo |
| Custom | Full control | Any warehouse | Development + infrastructure costs |

```python
# Custom Reverse ETL pattern: Snowflake → Salesforce
from snowflake.connector import connect
from simple_salesforce import Salesforce
from typing import List, Dict
import os

def extract_from_warehouse(query: str) -> List[Dict]:
    """Extract data from Snowflake."""
    conn = connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse='COMPUTE_WH',
        database='ANALYTICS',
        schema='CORE'
    )

    cursor = conn.cursor()
    cursor.execute(query)

    columns = [col[0] for col in cursor.description]
    results = []

    for row in cursor:
        results.append(dict(zip(columns, row)))

    return results

def load_to_salesforce(records: List[Dict], sf: Salesforce, object_name: str):
    """Bulk upsert to Salesforce with batching."""
    batch_size = 200

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        try:
            # Upsert using external ID field
            result = sf.bulk.__getattr__(object_name).upsert(
                batch,
                'External_Id__c',
                batch_size=batch_size
            )

            for idx, res in enumerate(result):
                if not res['success']:
                    print(f"Failed to sync {batch[idx]}: {res['errors']}")

        except Exception as e:
            print(f"Batch failed: {e}")
            # Log to dead letter queue for retry

# Main sync job
sf = Salesforce(
    username=os.getenv('SF_USERNAME'),
    password=os.getenv('SF_PASSWORD'),
    security_token=os.getenv('SF_SECURITY_TOKEN')
)

# Extract customer scores from warehouse
customer_scores = extract_from_warehouse("""
    SELECT
        customer_id as External_Id__c,
        ltv_score as LTV_Score__c,
        churn_risk as Churn_Risk__c,
        last_updated_at as Last_Score_Update__c
    FROM ml_models.customer_scores
    WHERE last_updated_at > DATEADD(hour, -1, CURRENT_TIMESTAMP())
""")

# Load to Salesforce Account object
load_to_salesforce(customer_scores, sf, 'Account')
```

## Error Handling & Retry Strategy

Implement robust error handling with exponential backoff, dead letter queues, and circuit breakers to build resilient integrations.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import time
from datetime import datetime
from typing import Callable, Any
import json

class CircuitBreaker:
    """Circuit breaker to prevent overwhelming failing systems."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failures = 0
        self.state = 'closed'

    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = 'open'

class DeadLetterQueue:
    """Simple dead letter queue for failed messages."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def send(self, message: dict, error: str):
        """Write failed message to DLQ."""
        with open(self.file_path, 'a') as f:
            dlq_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'message': message,
                'error': str(error)
            }
            f.write(json.dumps(dlq_entry) + '\n')

# Retry with exponential backoff
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def call_external_api(url: str, payload: dict) -> dict:
    """Call external API with retry logic."""
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

# Usage with circuit breaker and DLQ
circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
dlq = DeadLetterQueue('/var/log/integration-dlq.jsonl')

def process_message(message: dict):
    """Process message with full error handling."""
    try:
        result = circuit_breaker.call(
            call_external_api,
            'https://api.example.com/v1/process',
            message
        )
        return result
    except Exception as e:
        print(f"Failed to process message after retries: {e}")
        dlq.send(message, str(e))
        raise
```

## Data Mapping & Crosswalks

Establish canonical data models to maintain consistency across integrations. Use crosswalk tables to map external system IDs to internal canonical IDs.

For detailed guidance on canonical model design, field mapping strategies, and schema drift detection, see the [Deep dive →](references/data-mapping-crosswalks.md)

## API Design for Data Pipelines

When building APIs for data pipelines, implement proper pagination, rate limiting, and idempotency patterns.

```python
from fastapi import FastAPI, Query, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import hashlib

app = FastAPI()

# Idempotency key tracking
processed_keys = set()

class DataRecord(BaseModel):
    id: str
    data: dict
    created_at: datetime

@app.get("/api/v1/records")
async def get_records(
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(100, le=1000, description="Records per page")
) -> dict:
    """
    Cursor-based pagination for efficient data retrieval.

    Returns:
        - records: List of data records
        - next_cursor: Cursor for next page (null if no more pages)
    """
    # Decode cursor to get last ID
    last_id = decode_cursor(cursor) if cursor else None

    # Fetch records after cursor
    records = fetch_records_after(last_id, limit)

    # Generate next cursor if more records exist
    next_cursor = None
    if len(records) == limit:
        next_cursor = encode_cursor(records[-1].id)

    return {
        "records": records,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None
    }

@app.post("/api/v1/records")
async def create_record(
    record: DataRecord,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
) -> dict:
    """
    Create record with idempotency key support.

    Clients should provide Idempotency-Key header to prevent duplicate writes.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header required"
        )

    # Check if already processed
    if idempotency_key in processed_keys:
        return {
            "status": "already_processed",
            "record_id": record.id
        }

    # Process record
    result = save_record(record)
    processed_keys.add(idempotency_key)

    return {
        "status": "created",
        "record_id": result.id
    }

def encode_cursor(last_id: str) -> str:
    """Encode cursor from last record ID."""
    import base64
    return base64.b64encode(last_id.encode()).decode()

def decode_cursor(cursor: str) -> str:
    """Decode cursor to get last record ID."""
    import base64
    return base64.b64decode(cursor.encode()).decode()
```

## Reference Files

This skill includes detailed reference documentation for deep dives into specific integration patterns:

- [Enterprise Connectors →](references/enterprise-connectors.md) — Salesforce, NetSuite, Stripe, Workday, ServiceNow deep dives with code examples, auth patterns, and best practices
- [Event-Driven Architecture →](references/event-driven-architecture.md) — Kafka, Google Pub/Sub, AWS EventBridge, schema registry, event sourcing patterns
- [iPaaS Platforms →](references/ipaas-platforms.md) — Workato, MuleSoft, Boomi detailed comparison, recipe examples, pricing analysis
- [CDC Patterns →](references/cdc-patterns.md) — Debezium setup, Snowflake Streams, BigQuery CDC, change tracking strategies
- [Data Mapping & Crosswalks →](references/data-mapping-crosswalks.md) — Canonical model design, crosswalk table patterns, schema drift detection
