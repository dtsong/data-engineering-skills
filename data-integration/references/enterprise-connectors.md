# Enterprise Connectors

## Salesforce

**API selection:** SOQL for < 10K records (real-time). Bulk API 2.0 for > 10K records (batch). Streaming API / Platform Events for real-time CDC.

**Auth:** Prefer OAuth 2.0 JWT Bearer flow for server-to-server (no user interaction). Generate JWT with consumer key + private key, exchange for access token.

**Rate limits:** REST/SOAP: 15,000 + 1,000/user per 24h. Bulk API: 15,000 batches, 150M records/day. Streaming: 20 topics, 40 clients.

**Pagination:** Use `query_all()` or follow `nextRecordsUrl` for large result sets.

**Incremental sync:** Filter by `SystemModstamp > {last_sync_time}`. Detect deletes with `IsDeleted = true ALL ROWS`.

**Anti-patterns:**
- Don't use SOQL for large analytics queries -- export to warehouse instead
- Don't query in loops -- use relationship queries (subselects)
- Don't hardcode record IDs -- query by DeveloperName (IDs differ across sandbox/prod)

**CDC:** Subscribe to `/data/AccountChangeEvent` via Streaming API for real-time change notifications (CREATE, UPDATE, DELETE).

## NetSuite

**APIs:** SuiteTalk SOAP (comprehensive, mature), RESTlet (custom logic, high perf), REST Web Services (standard CRUD, newer).

**Auth:** Token-Based Authentication (TBA) with OAuth1 (HMAC-SHA256). Avoid password-based auth.

**SuiteQL:** SQL-like queries via REST endpoint. Pagination with `OFFSET/FETCH NEXT`. Supports joins and aggregates.

```python
def execute_suiteql(query):
    url = f'https://{ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql'
    response = requests.post(url, json={'q': query}, headers={'Prefer': 'transient'}, auth=oauth1_auth)
    return response.json()
```

**Rate limits:** 10 concurrent requests per integration, 1,000/hour, RESTlet 25/minute, 10,000 governance units/hour.

**Common entities:** Transactions (`type = 'SalesOrd'`), Customers (`companyname, email, lastmodifieddate`), Items (`quantityavailable, isinactive`).

**Incremental sync:** Filter by `lastmodifieddate > TIMESTAMP '{iso_time}'`.

## Stripe

**Webhook-first architecture:** Use webhooks for real-time events instead of polling. Lower latency, fewer API calls, built-in retries.

**Critical events:** `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`, `customer.subscription.created/deleted`, `invoice.payment_succeeded/failed`.

**Signature verification:** Always verify `Stripe-Signature` header using `stripe.Webhook.construct_event()`. Return 200 on success, 500 to trigger retry.

**Idempotency:** Use `idempotency_key` on all write operations. Generate unique key per logical operation. Stripe returns cached response for duplicate keys.

**Pagination:** Cursor-based with `starting_after` parameter. Use `auto_paging_iter()` for convenience or manual pagination for control.

**Deduplication:** Track processed `event.id` in database/Redis. Check before processing, mark after success. Return 200 for duplicates.

**Test vs Live:** Use separate API keys via env vars. Store in separate database tables to prevent test data polluting production.

## Workday

**APIs:** SOAP (WWS) for comprehensive HR data with response groups. REST API for simpler CRUD. RaaS (Report as a Service) for custom reports.

**Auth:** OAuth 2.0 with refresh token flow, or basic auth for scripts.

**Worker extraction:** Use SOAP `Get_Workers` with `Response_Group` flags for personal info, employment, compensation, organizations. REST API at `/ccx/api/v1/{tenant}/workers` with limit/offset pagination.

**RaaS reports:** Custom reports exposed as REST endpoints. Format as JSON. URL: `/ccx/service/customreport2/{tenant}/{owner}/{report_name}`.

**Incremental:** SOAP: `Last_Modified_From/To` in Response_Filter. REST: query parameter filtering.

## ServiceNow

**Table API:** REST CRUD on any table. Use encoded queries: `active=true^priority=1`. Pagination via `sysparm_limit` + `sysparm_offset`.

**Import Set API:** Bulk data loading with transform maps.

**Performance optimization:**
- `sysparm_display_value=false` (avoid lookup overhead)
- `sysparm_fields` to select only needed columns
- Encoded queries for complex conditions (`^` = AND, `^OR` = OR)

**Common tables:** `incident`, `change_request`, `cmdb_ci`, `sys_user`.

**Incremental sync:** Filter by `sys_updated_on>{last_sync_time}` (format: `YYYY-MM-DD HH:MM:SS`).

**Scripted REST APIs:** Custom server-side GlideRecord scripts exposed as REST endpoints for complex queries not possible with standard Table API.
