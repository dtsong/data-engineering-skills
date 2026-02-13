# Enterprise Connectors

> **Part of:** [integration-patterns-skill](../SKILL.md)
> **Purpose:** Deep dive into connecting with major enterprise platforms — Salesforce, NetSuite, Stripe, Workday, ServiceNow

## Table of Contents

- [Salesforce Integration](#salesforce-integration)
- [NetSuite Integration](#netsuite-integration)
- [Stripe Integration](#stripe-integration)
- [Workday Integration](#workday-integration)
- [ServiceNow Integration](#servicenow-integration)

---

## Salesforce Integration

### SOQL Queries and Bulk API 2.0

Use SOQL for small-to-medium queries (under 10,000 records) and Bulk API 2.0 for large-scale data extraction.

**SOQL Query Example:**

```python
from simple_salesforce import Salesforce

sf = Salesforce(
    username='user@example.com',
    password='password',
    security_token='token'
)

# Query accounts modified in last 24 hours
query = """
    SELECT Id, Name, Industry, CreatedDate, SystemModstamp
    FROM Account
    WHERE SystemModstamp > YESTERDAY
    ORDER BY SystemModstamp
"""

results = sf.query_all(query)
for record in results['records']:
    print(record['Name'], record['SystemModstamp'])
```

**Bulk API 2.0 Example:**

```python
from simple_salesforce import Salesforce
import requests
import time

sf = Salesforce(username='...', password='...', security_token='...')

# Create bulk job
job_url = f"{sf.base_url}jobs/query"
job_data = {
    "operation": "query",
    "query": "SELECT Id, Name FROM Account WHERE SystemModstamp > 2024-01-01T00:00:00Z"
}

headers = {
    "Authorization": f"Bearer {sf.session_id}",
    "Content-Type": "application/json"
}

response = requests.post(job_url, json=job_data, headers=headers)
job_id = response.json()['id']

# Poll for completion
status_url = f"{job_url}/{job_id}"
while True:
    status = requests.get(status_url, headers=headers).json()
    if status['state'] in ['JobComplete', 'Failed']:
        break
    time.sleep(5)

# Download results
results_url = f"{job_url}/{job_id}/results"
results = requests.get(results_url, headers=headers)
print(results.text)
```

**When to Use Each:**

| Scenario | Use SOQL | Use Bulk API 2.0 |
|----------|----------|------------------|
| Records < 10K | Yes | No |
| Records > 10K | No | Yes |
| Real-time query | Yes | No |
| Batch extraction | No | Yes |
| Complex joins | Yes | Limited |
| Governor limits concern | No | Yes |

### Salesforce Change Data Capture

Subscribe to platform events to receive real-time change notifications.

```python
import asyncio
from aiosfstream import SalesforceStreamingClient

async def stream_changes():
    async with SalesforceStreamingClient(
        consumer_key='your_consumer_key',
        consumer_secret='your_consumer_secret',
        username='user@example.com',
        password='password'
    ) as client:

        # Subscribe to Account changes
        await client.subscribe('/data/AccountChangeEvent')

        async for message in client:
            payload = message['payload']
            change_type = message['payload']['ChangeEventHeader']['changeType']

            if change_type == 'CREATE':
                print(f"New account: {payload['Name']}")
            elif change_type == 'UPDATE':
                print(f"Updated account: {payload['Name']}")
            elif change_type == 'DELETE':
                print(f"Deleted account ID: {payload['Id']}")

asyncio.run(stream_changes())
```

### OAuth 2.0 JWT Bearer Flow

Use JWT for server-to-server authentication without user interaction.

```python
import jwt
import time
import requests

# Generate JWT
private_key = open('salesforce_private_key.pem', 'r').read()

payload = {
    'iss': 'your_consumer_key',
    'sub': 'user@example.com',
    'aud': 'https://login.salesforce.com',  # or test.salesforce.com for sandbox
    'exp': int(time.time()) + 300  # 5 minutes
}

token = jwt.encode(payload, private_key, algorithm='RS256')

# Exchange JWT for access token
auth_url = 'https://login.salesforce.com/services/oauth2/token'
data = {
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'assertion': token
}

response = requests.post(auth_url, data=data)
access_token = response.json()['access_token']
instance_url = response.json()['instance_url']

print(f"Access Token: {access_token}")
print(f"Instance URL: {instance_url}")
```

### Rate Limits and Governor Limits

| API Type | Daily Limit | Concurrent Limit | Notes |
|----------|-------------|------------------|-------|
| REST API | 15,000 + (1,000 × users) | 25 | Per org per 24 hours |
| Bulk API 2.0 | 15,000 batches | 100 concurrent jobs | 150M records/day |
| SOAP API | 15,000 + (1,000 × users) | 25 | Shared with REST |
| Streaming API | 20 topics | 40 clients | Per org |
| Platform Events | 250,000 events/day | N/A | Enterprise edition |

**Monitor API Usage:**

```python
# Check remaining API calls
response = sf.restful('limits/')
api_requests = response['DailyApiRequests']
print(f"Used: {api_requests['Remaining']} / {api_requests['Max']}")
```

### Pagination with QueryLocator

Handle large result sets efficiently.

```python
def fetch_all_records(sf, query):
    """Fetch all records using pagination."""
    all_records = []

    # Initial query
    response = sf.query(query)
    all_records.extend(response['records'])

    # Paginate through remaining records
    while not response['done']:
        response = sf.query_more(
            response['nextRecordsUrl'],
            identifier_is_url=True
        )
        all_records.extend(response['records'])

    return all_records

# Usage
query = "SELECT Id, Name FROM Account LIMIT 50000"
accounts = fetch_all_records(sf, query)
print(f"Retrieved {len(accounts)} accounts")
```

### Common Patterns: Full Sync vs Incremental

**Full Sync Pattern:**

```python
def full_sync_accounts(sf):
    """Extract all accounts."""
    query = """
        SELECT Id, Name, Industry, BillingCity, CreatedDate
        FROM Account
        WHERE IsDeleted = false
    """
    return fetch_all_records(sf, query)
```

**Incremental Sync Pattern:**

```python
from datetime import datetime, timedelta

def incremental_sync_accounts(sf, last_sync_time):
    """Extract accounts modified since last sync."""
    # SystemModstamp tracks last modification time
    query = f"""
        SELECT Id, Name, Industry, BillingCity, SystemModstamp
        FROM Account
        WHERE SystemModstamp > {last_sync_time.isoformat()}
        ORDER BY SystemModstamp
    """
    return fetch_all_records(sf, query)

# Usage
last_sync = datetime.utcnow() - timedelta(hours=1)
updated_accounts = incremental_sync_accounts(sf, last_sync)
```

**Handle Deleted Records:**

```python
def get_deleted_records(sf, start_date, end_date):
    """Retrieve deleted records from recycle bin."""
    query = f"""
        SELECT Id, Name FROM Account
        WHERE IsDeleted = true
        AND SystemModstamp >= {start_date.isoformat()}
        AND SystemModstamp < {end_date.isoformat()}
        ALL ROWS
    """
    return sf.query_all(query)
```

### Anti-Patterns to Avoid

**Don't use SOQL for large analytics queries:**

```python
# BAD: This will hit governor limits
bad_query = """
    SELECT Id, Name, Amount, CloseDate,
           (SELECT Id, Name FROM OpportunityLineItems)
    FROM Opportunity
    WHERE CloseDate > 2020-01-01
"""

# GOOD: Use Bulk API 2.0 or export to data warehouse
# Then run analytics queries in BigQuery/Snowflake
```

**Don't ignore relationship queries optimization:**

```python
# BAD: Multiple queries in a loop
for account in accounts:
    contacts = sf.query(f"SELECT Id FROM Contact WHERE AccountId = '{account['Id']}'")

# GOOD: Single query with relationship
query = """
    SELECT Id, Name,
           (SELECT Id, FirstName, LastName FROM Contacts)
    FROM Account
"""
accounts_with_contacts = sf.query_all(query)
```

**Don't hardcode IDs across environments:**

```python
# BAD: Record IDs differ between sandbox and production
record_type_id = '012xx0000001234'

# GOOD: Query by developer name
query = """
    SELECT Id FROM RecordType
    WHERE SObjectType = 'Account'
    AND DeveloperName = 'Enterprise_Account'
"""
record_type = sf.query(query)['records'][0]['Id']
```

---

## NetSuite Integration

### SuiteTalk SOAP API vs RESTlet vs REST Web Services

**Comparison:**

| Feature | SOAP (SuiteTalk) | RESTlet | REST Web Services |
|---------|------------------|---------|-------------------|
| Maturity | Mature, stable | Mature | Beta (2021+) |
| Use Case | Standard CRUD | Custom logic | Standard CRUD |
| Performance | Medium | High | High |
| Complexity | High | Medium | Low |
| Authentication | TBA or OAuth 2.0 | TBA or OAuth 2.0 | OAuth 2.0 |

### Token-Based Authentication Setup

```python
import requests
from requests_oauthlib import OAuth1

# NetSuite TBA credentials
ACCOUNT_ID = '1234567'
CONSUMER_KEY = 'your_consumer_key'
CONSUMER_SECRET = 'your_consumer_secret'
TOKEN_ID = 'your_token_id'
TOKEN_SECRET = 'your_token_secret'

def create_netsuite_auth():
    """Create OAuth1 session for NetSuite."""
    return OAuth1(
        client_key=CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=TOKEN_ID,
        resource_owner_secret=TOKEN_SECRET,
        realm=ACCOUNT_ID,
        signature_method='HMAC-SHA256'
    )

# REST API request example
url = f'https://{ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/record/v1/customer'
auth = create_netsuite_auth()

response = requests.get(url, auth=auth)
customers = response.json()
```

### SuiteQL for SQL-like Querying

```python
def execute_suiteql(query):
    """Execute SuiteQL query."""
    url = f'https://{ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql'

    headers = {
        'Content-Type': 'application/json',
        'Prefer': 'transient'
    }

    payload = {
        'q': query
    }

    auth = create_netsuite_auth()
    response = requests.post(url, json=payload, headers=headers, auth=auth)

    return response.json()

# Query customers with SuiteQL
query = """
    SELECT
        id,
        companyname,
        email,
        datecreated,
        lastmodifieddate
    FROM
        customer
    WHERE
        lastmodifieddate > TO_DATE('2024-01-01', 'YYYY-MM-DD')
    ORDER BY
        lastmodifieddate
    OFFSET 0 ROWS
    FETCH NEXT 1000 ROWS ONLY
"""

results = execute_suiteql(query)
for item in results.get('items', []):
    print(item)
```

### Saved Search API for Complex Reports

```python
def get_saved_search_results(search_id, offset=0, limit=1000):
    """Retrieve results from a saved search."""
    url = f'https://{ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql'

    # Use saved search via SuiteQL
    query = f"""
        SELECT * FROM transaction
        WHERE id IN (
            SELECT id FROM transaction
            WHERE /* saved search criteria */
        )
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
    """

    # Alternative: Use RESTlet to execute saved search
    restlet_url = f'https://{ACCOUNT_ID}.restlets.api.netsuite.com/app/site/hosting/restlet.nl'

    params = {
        'script': '123',  # Saved search script ID
        'deploy': '1',
        'searchId': search_id,
        'offset': offset,
        'limit': limit
    }

    auth = create_netsuite_auth()
    response = requests.get(restlet_url, params=params, auth=auth)

    return response.json()
```

### Rate Limits and Concurrency Governance

| Limit Type | Value | Notes |
|------------|-------|-------|
| Concurrent requests | 10 per integration | Per TBA token |
| Request rate | 1,000/hour | Burst allowed |
| Search API | 100 concurrent | Shared across searches |
| RESTlet execution | 25/minute | Per script deployment |
| Governance units | 10,000/hour | For SuiteScript execution |

**Handle Rate Limiting:**

```python
import time
from requests.exceptions import HTTPError

def netsuite_request_with_retry(url, auth, max_retries=3):
    """Make NetSuite request with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, auth=auth)
            response.raise_for_status()
            return response.json()

        except HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise

    raise Exception("Max retries exceeded")
```

### Common Entities

**Transaction Records:**

```python
def get_sales_orders(start_date):
    """Retrieve sales orders."""
    query = f"""
        SELECT
            t.id,
            t.tranid,
            t.trandate,
            t.entity,
            t.status,
            t.total
        FROM
            transaction t
        WHERE
            t.type = 'SalesOrd'
            AND t.trandate >= '{start_date}'
    """
    return execute_suiteql(query)
```

**Customer Records:**

```python
def get_customers_incremental(last_modified):
    """Get customers modified since last sync."""
    query = f"""
        SELECT
            c.id,
            c.companyname,
            c.email,
            c.phone,
            c.lastmodifieddate
        FROM
            customer c
        WHERE
            c.lastmodifieddate > TIMESTAMP '{last_modified}'
        ORDER BY
            c.lastmodifieddate
    """
    return execute_suiteql(query)
```

**Item Records:**

```python
def get_inventory_items():
    """Retrieve inventory items with current quantities."""
    query = """
        SELECT
            i.id,
            i.itemid,
            i.displayname,
            i.quantityavailable,
            i.quantityonhand,
            i.lastmodifieddate
        FROM
            item i
        WHERE
            i.isinactive = 'F'
    """
    return execute_suiteql(query)
```

### Incremental Sync via lastModifiedDate

```python
from datetime import datetime, timezone

def incremental_sync_entity(entity_type, last_sync_time):
    """Generic incremental sync for any entity."""

    # Store last sync time in ISO format
    last_sync_iso = last_sync_time.isoformat()

    query = f"""
        SELECT
            *
        FROM
            {entity_type}
        WHERE
            lastmodifieddate > TIMESTAMP '{last_sync_iso}'
        ORDER BY
            lastmodifieddate
    """

    results = execute_suiteql(query)

    # Update sync timestamp
    new_sync_time = datetime.now(timezone.utc)

    return results, new_sync_time

# Usage
last_sync = datetime(2024, 1, 1, tzinfo=timezone.utc)
customers, new_timestamp = incremental_sync_entity('customer', last_sync)
```

---

## Stripe Integration

### Webhook-First Architecture

Use webhooks to react to events in real-time rather than polling the API.

**Why Webhooks Over Polling:**

| Aspect | Webhooks | Polling |
|--------|----------|---------|
| Latency | Real-time (seconds) | Minutes to hours |
| API calls | Minimal | Constant |
| Cost | Low | High (rate limits) |
| Reliability | High (retries) | Depends on frequency |
| Data freshness | Immediate | Delayed |

### Critical Event Types

| Event Type | Purpose | Priority |
|------------|---------|----------|
| `payment_intent.succeeded` | Payment completed | Critical |
| `payment_intent.payment_failed` | Payment failed | Critical |
| `charge.refunded` | Refund processed | High |
| `customer.subscription.created` | New subscription | High |
| `customer.subscription.deleted` | Subscription cancelled | High |
| `invoice.payment_succeeded` | Invoice paid | High |
| `invoice.payment_failed` | Invoice payment failed | High |
| `payout.paid` | Funds transferred to bank | Medium |
| `customer.created` | New customer | Medium |
| `customer.updated` | Customer details changed | Low |

### Webhook Signature Verification

```python
import stripe
import hashlib
import hmac
from flask import Flask, request, jsonify

app = Flask(__name__)

STRIPE_WEBHOOK_SECRET = 'whsec_your_webhook_secret'

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle specific event types
    event_type = event['type']
    event_data = event['data']['object']

    if event_type == 'payment_intent.succeeded':
        handle_successful_payment(event_data)
    elif event_type == 'customer.subscription.deleted':
        handle_cancelled_subscription(event_data)

    return jsonify({'status': 'success'}), 200

def handle_successful_payment(payment_intent):
    """Process successful payment."""
    print(f"Payment {payment_intent['id']} succeeded")
    print(f"Amount: {payment_intent['amount']} {payment_intent['currency']}")

    # Store in database, send confirmation email, etc.

def handle_cancelled_subscription(subscription):
    """Process cancelled subscription."""
    print(f"Subscription {subscription['id']} cancelled")
    print(f"Customer: {subscription['customer']}")

    # Update customer access, send notification, etc.

if __name__ == '__main__':
    app.run(port=5000)
```

### Stripe API Pagination

```python
import stripe

stripe.api_key = 'sk_test_your_api_key'

def fetch_all_customers():
    """Fetch all customers using auto-pagination."""
    all_customers = []

    # Auto-pagination with stripe-python
    for customer in stripe.Customer.list(limit=100).auto_paging_iter():
        all_customers.append(customer)

    return all_customers

def fetch_customers_manual_pagination():
    """Manual pagination for more control."""
    all_customers = []
    starting_after = None

    while True:
        params = {'limit': 100}
        if starting_after:
            params['starting_after'] = starting_after

        customers = stripe.Customer.list(**params)
        all_customers.extend(customers.data)

        if not customers.has_more:
            break

        starting_after = customers.data[-1].id

    return all_customers
```

### Idempotency Keys for Safe Retries

```python
import uuid
import stripe

def create_payment_intent_idempotent(amount, currency, customer_id):
    """Create payment intent with idempotency key."""

    # Generate unique idempotency key
    idempotency_key = str(uuid.uuid4())

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            idempotency_key=idempotency_key
        )
        return payment_intent

    except stripe.error.IdempotencyError:
        # Request with same key already processed
        print("Duplicate request detected")
        return None

# Safe retry with same idempotency key
def create_charge_with_retry(amount, currency, source, max_retries=3):
    """Create charge with automatic retry."""
    idempotency_key = str(uuid.uuid4())

    for attempt in range(max_retries):
        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency=currency,
                source=source,
                idempotency_key=idempotency_key
            )
            return charge

        except stripe.error.APIConnectionError:
            if attempt == max_retries - 1:
                raise
            continue
```

### Common Data Models

**Charges:**

```python
def get_charges_in_date_range(start_date, end_date):
    """Retrieve charges within date range."""
    charges = stripe.Charge.list(
        created={
            'gte': int(start_date.timestamp()),
            'lte': int(end_date.timestamp())
        },
        limit=100
    )

    for charge in charges.auto_paging_iter():
        print(f"Charge {charge.id}: {charge.amount} {charge.currency}")
        print(f"Status: {charge.status}")
        print(f"Customer: {charge.customer}")
```

**Subscriptions:**

```python
def get_active_subscriptions():
    """Get all active subscriptions."""
    subscriptions = stripe.Subscription.list(
        status='active',
        limit=100
    )

    for sub in subscriptions.auto_paging_iter():
        print(f"Subscription {sub.id}")
        print(f"Customer: {sub.customer}")
        print(f"Plan: {sub.items.data[0].price.id}")
        print(f"Current period: {sub.current_period_start} - {sub.current_period_end}")
```

**Invoices:**

```python
def get_unpaid_invoices():
    """Retrieve all unpaid invoices."""
    invoices = stripe.Invoice.list(
        status='open',
        limit=100
    )

    for invoice in invoices.auto_paging_iter():
        print(f"Invoice {invoice.id}: {invoice.amount_due} {invoice.currency}")
        print(f"Customer: {invoice.customer}")
        print(f"Due date: {invoice.due_date}")
```

### Webhook Replay and Deduplication

```python
import json
from datetime import datetime

# Simple in-memory deduplication (use Redis/database in production)
processed_events = set()

def is_duplicate_event(event_id):
    """Check if event has been processed."""
    return event_id in processed_events

def mark_event_processed(event_id):
    """Mark event as processed."""
    processed_events.add(event_id)

@app.route('/webhook', methods=['POST'])
def stripe_webhook_with_deduplication():
    """Handle webhook with deduplication."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    event_id = event['id']

    # Check for duplicate
    if is_duplicate_event(event_id):
        print(f"Duplicate event {event_id} detected, skipping")
        return jsonify({'status': 'duplicate'}), 200

    # Process event
    process_stripe_event(event)

    # Mark as processed
    mark_event_processed(event_id)

    return jsonify({'status': 'success'}), 200

def process_stripe_event(event):
    """Process Stripe event with error handling."""
    try:
        event_type = event['type']

        handlers = {
            'payment_intent.succeeded': handle_successful_payment,
            'customer.subscription.deleted': handle_cancelled_subscription,
            # Add more handlers
        }

        handler = handlers.get(event_type)
        if handler:
            handler(event['data']['object'])
        else:
            print(f"Unhandled event type: {event_type}")

    except Exception as e:
        print(f"Error processing event {event['id']}: {e}")
        raise  # Let Stripe retry
```

### Test Mode vs Live Mode Data Separation

```python
import os

# Use environment variables for API keys
STRIPE_TEST_KEY = os.environ.get('STRIPE_TEST_KEY')
STRIPE_LIVE_KEY = os.environ.get('STRIPE_LIVE_KEY')

def get_stripe_client(mode='test'):
    """Get Stripe client for specific mode."""
    if mode == 'live':
        stripe.api_key = STRIPE_LIVE_KEY
    else:
        stripe.api_key = STRIPE_TEST_KEY

    return stripe

# Separate database tables for test vs live data
def store_payment(payment_intent, mode='test'):
    """Store payment in appropriate table."""
    table_name = f"payments_{mode}"

    # Insert into correct table based on mode
    # This prevents test data from polluting production analytics
```

---

## Workday Integration

### Workday Web Services (WWS) — SOAP-based

```python
from zeep import Client
from zeep.wsse.username import UsernameToken
from requests import Session

# Workday credentials
WORKDAY_USERNAME = 'integration_user@tenant'
WORKDAY_PASSWORD = 'password'
WORKDAY_TENANT = 'your_tenant'
WORKDAY_WSDL_URL = f'https://wd2-impl-services1.workday.com/ccx/service/{WORKDAY_TENANT}/Human_Resources/v38.2?wsdl'

def create_workday_client(wsdl_url):
    """Create Workday SOAP client."""
    session = Session()
    session.auth = (WORKDAY_USERNAME, WORKDAY_PASSWORD)

    client = Client(
        wsdl=wsdl_url,
        wsse=UsernameToken(WORKDAY_USERNAME, WORKDAY_PASSWORD)
    )

    return client

def get_workers():
    """Retrieve workers using SOAP API."""
    client = create_workday_client(WORKDAY_WSDL_URL)

    # Create request
    response = client.service.Get_Workers(
        version='v38.2'
    )

    for worker in response.Response_Data.Worker:
        print(f"Worker: {worker.Worker_Reference.ID[0].value}")
        print(f"Name: {worker.Worker_Data.Personal_Data.Name_Data.Legal_Name_Data.Name_Detail_Data.Formatted_Name}")
```

### Workday REST API

```python
import requests
from requests.auth import HTTPBasicAuth

WORKDAY_REST_BASE = f'https://wd2-impl-services1.workday.com/ccx/api/v1/{WORKDAY_TENANT}'

def get_workers_rest(limit=100, offset=0):
    """Retrieve workers using REST API."""
    url = f'{WORKDAY_REST_BASE}/workers'

    params = {
        'limit': limit,
        'offset': offset
    }

    response = requests.get(
        url,
        auth=HTTPBasicAuth(WORKDAY_USERNAME, WORKDAY_PASSWORD),
        params=params
    )

    return response.json()

# Pagination
def get_all_workers_rest():
    """Fetch all workers with pagination."""
    all_workers = []
    offset = 0
    limit = 100

    while True:
        data = get_workers_rest(limit=limit, offset=offset)
        workers = data.get('data', [])

        if not workers:
            break

        all_workers.extend(workers)
        offset += limit

    return all_workers
```

### RaaS (Report as a Service)

```python
def get_raas_report(report_url):
    """Fetch Workday RaaS report."""

    # RaaS URL format:
    # https://wd2-impl-services1.workday.com/ccx/service/customreport2/{tenant}/{report_owner}/{report_name}

    response = requests.get(
        report_url,
        auth=HTTPBasicAuth(WORKDAY_USERNAME, WORKDAY_PASSWORD),
        params={'format': 'json'}
    )

    return response.json()

# Example: Custom worker report
raas_url = f'https://wd2-impl-services1.workday.com/ccx/service/customreport2/{WORKDAY_TENANT}/ISU_Admin/Worker_Extract'
workers_report = get_raas_report(raas_url)

for worker in workers_report.get('Report_Entry', []):
    print(worker)
```

### OAuth 2.0 Authentication

```python
import requests

# OAuth 2.0 credentials
CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REFRESH_TOKEN = 'your_refresh_token'
TOKEN_URL = f'https://wd2-impl-services1.workday.com/ccx/oauth2/{WORKDAY_TENANT}/token'

def get_access_token():
    """Get OAuth 2.0 access token."""
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=data)
    return response.json()['access_token']

def workday_api_call_oauth(endpoint):
    """Make Workday API call with OAuth."""
    access_token = get_access_token()

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    url = f'{WORKDAY_REST_BASE}/{endpoint}'
    response = requests.get(url, headers=headers)

    return response.json()
```

### Common Data Extraction

**Workers:**

```python
def extract_worker_data():
    """Extract comprehensive worker data."""
    client = create_workday_client(WORKDAY_WSDL_URL)

    response = client.service.Get_Workers(
        Response_Filter={
            'As_Of_Effective_Date': '2024-01-01',
            'As_Of_Entry_DateTime': '2024-01-01T00:00:00'
        },
        Response_Group={
            'Include_Personal_Information': True,
            'Include_Employment_Information': True,
            'Include_Compensation': True,
            'Include_Organizations': True
        }
    )

    workers = []
    for worker in response.Response_Data.Worker:
        worker_data = {
            'id': worker.Worker_Reference.ID[0].value,
            'name': worker.Worker_Data.Personal_Data.Name_Data.Legal_Name_Data.Name_Detail_Data.Formatted_Name,
            'email': worker.Worker_Data.Personal_Data.Contact_Data.Email_Address_Data[0].Email_Address,
            'hire_date': worker.Worker_Data.Employment_Data.Worker_Job_Data[0].Position_Data.Start_Date
        }
        workers.append(worker_data)

    return workers
```

**Organizations:**

```python
def get_organizations():
    """Retrieve organization hierarchy."""
    url = f'{WORKDAY_REST_BASE}/organizations'

    response = requests.get(
        url,
        auth=HTTPBasicAuth(WORKDAY_USERNAME, WORKDAY_PASSWORD)
    )

    return response.json()
```

### Incremental Extraction Patterns

```python
from datetime import datetime, timedelta

def get_workers_modified_since(last_sync_time):
    """Get workers modified since last sync."""
    client = create_workday_client(WORKDAY_WSDL_URL)

    response = client.service.Get_Workers(
        Response_Filter={
            'Last_Modified_From': last_sync_time.isoformat(),
            'Last_Modified_To': datetime.utcnow().isoformat()
        }
    )

    return response.Response_Data.Worker

# Usage
last_sync = datetime.utcnow() - timedelta(hours=24)
updated_workers = get_workers_modified_since(last_sync)
```

---

## ServiceNow Integration

### Table API (REST) for CRUD Operations

```python
import requests
from requests.auth import HTTPBasicAuth

SERVICENOW_INSTANCE = 'your-instance.service-now.com'
SERVICENOW_USER = 'admin'
SERVICENOW_PASSWORD = 'password'

BASE_URL = f'https://{SERVICENOW_INSTANCE}/api/now'

def get_records(table, query=None, limit=1000):
    """Get records from ServiceNow table."""
    url = f'{BASE_URL}/table/{table}'

    params = {
        'sysparm_limit': limit,
        'sysparm_display_value': 'false'  # Return sys_ids instead of display values
    }

    if query:
        params['sysparm_query'] = query

    response = requests.get(
        url,
        auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
        params=params
    )

    return response.json()['result']

# Example: Get incidents
incidents = get_records('incident', query='active=true^priority=1')
for incident in incidents:
    print(f"Incident {incident['number']}: {incident['short_description']}")
```

### Import Set API for Bulk Data Loading

```python
def bulk_insert_via_import_set(table, records):
    """Bulk insert records using Import Set API."""
    url = f'{BASE_URL}/import/{table}'

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    results = []
    for record in records:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
            headers=headers,
            json=record
        )
        results.append(response.json())

    return results

# Example: Bulk insert CIs
ci_records = [
    {'name': 'Server001', 'ip_address': '10.0.0.1', 'u_department': 'IT'},
    {'name': 'Server002', 'ip_address': '10.0.0.2', 'u_department': 'Finance'}
]

results = bulk_insert_via_import_set('u_import_cmdb_ci', ci_records)
```

### Scripted REST APIs

```javascript
// ServiceNow Server-side Script
(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {

    var table = request.queryParams.table;
    var query = request.queryParams.query;

    var gr = new GlideRecord(table);
    gr.addEncodedQuery(query);
    gr.query();

    var results = [];
    while (gr.next()) {
        results.push({
            sys_id: gr.getValue('sys_id'),
            number: gr.getValue('number'),
            state: gr.getValue('state')
        });
    }

    return results;

})(request, response);
```

**Call Scripted REST API:**

```python
def call_scripted_api(endpoint, params=None):
    """Call custom scripted REST API."""
    url = f'https://{SERVICENOW_INSTANCE}/api/x_custom/v1/{endpoint}'

    response = requests.get(
        url,
        auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
        params=params
    )

    return response.json()

# Usage
data = call_scripted_api('custom_query', params={'table': 'incident', 'query': 'active=true'})
```

### Pagination

```python
def get_all_records_paginated(table, query=None, page_size=1000):
    """Fetch all records with pagination."""
    all_records = []
    offset = 0

    while True:
        url = f'{BASE_URL}/table/{table}'

        params = {
            'sysparm_limit': page_size,
            'sysparm_offset': offset,
            'sysparm_display_value': 'false'
        }

        if query:
            params['sysparm_query'] = query

        response = requests.get(
            url,
            auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
            params=params
        )

        records = response.json()['result']

        if not records:
            break

        all_records.extend(records)
        offset += page_size

    return all_records

# Usage
all_incidents = get_all_records_paginated('incident', query='active=true')
print(f"Retrieved {len(all_incidents)} incidents")
```

### Common Tables

**Incident Table:**

```python
def get_recent_incidents(days=7):
    """Get incidents created in last N days."""
    query = f'sys_created_onONLast {days} days@javascript:gs.daysAgoStart({days})@javascript:gs.daysAgoEnd(0)'

    incidents = get_records('incident', query=query)

    for incident in incidents:
        print(f"{incident['number']}: {incident['short_description']}")
        print(f"Priority: {incident['priority']}, State: {incident['state']}")
```

**Change Request Table:**

```python
def get_scheduled_changes():
    """Get scheduled change requests."""
    query = 'state=scheduled^start_dateONToday'

    changes = get_records('change_request', query=query)

    for change in changes:
        print(f"{change['number']}: {change['short_description']}")
        print(f"Scheduled start: {change['start_date']}")
```

**CMDB CI Table:**

```python
def get_servers_by_department(department):
    """Get servers for specific department."""
    query = f'u_department={department}^sys_class_name=cmdb_ci_server'

    servers = get_records('cmdb_ci', query=query)

    for server in servers:
        print(f"{server['name']}: {server['ip_address']}")
```

### Incremental Sync via sys_updated_on

```python
from datetime import datetime

def incremental_sync_table(table, last_sync_time):
    """Sync records updated since last sync."""

    # Format: YYYY-MM-DD HH:MM:SS
    last_sync_str = last_sync_time.strftime('%Y-%m-%d %H:%M:%S')

    query = f'sys_updated_on>{last_sync_str}'

    updated_records = get_all_records_paginated(table, query=query)

    print(f"Found {len(updated_records)} updated records")

    # Update sync timestamp
    new_sync_time = datetime.utcnow()

    return updated_records, new_sync_time

# Usage
last_sync = datetime(2024, 1, 1, 0, 0, 0)
updated_incidents, new_timestamp = incremental_sync_table('incident', last_sync)
```

### Performance Optimization

**Use display_value=false:**

```python
# SLOW: Returns display values (additional lookups)
params = {'sysparm_display_value': 'true'}

# FAST: Returns sys_ids only
params = {'sysparm_display_value': 'false'}

# Get both sys_id and display value
params = {'sysparm_display_value': 'all'}
```

**Select specific fields:**

```python
def get_incidents_optimized():
    """Get incidents with only needed fields."""
    url = f'{BASE_URL}/table/incident'

    params = {
        'sysparm_fields': 'number,short_description,priority,state,sys_updated_on',
        'sysparm_display_value': 'false',
        'sysparm_limit': 1000
    }

    response = requests.get(
        url,
        auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
        params=params
    )

    return response.json()['result']
```

**Use encoded queries:**

```python
# Build encoded query for complex conditions
def build_encoded_query():
    """Build encoded query programmatically."""
    conditions = [
        'active=true',
        'priority IN 1,2',
        'assigned_toISEMPTY'
    ]

    query = '^'.join(conditions)
    return query

# Use in API call
query = build_encoded_query()
incidents = get_records('incident', query=query)
```

---

Back to [main skill](../SKILL.md)
