# iPaaS Platforms

> **Part of:** [integration-patterns-skill](../SKILL.md)
> **Purpose:** Deep dive into iPaaS platforms, when to use iPaaS vs custom code, recipe patterns, and governance

## Table of Contents

- [iPaaS vs Custom Code Decision Framework](#ipaas-vs-custom-code-decision-framework)
- [Workato](#workato)
- [MuleSoft (Anypoint Platform)](#mulesoft-anypoint-platform)
- [Boomi](#boomi)
- [Zapier & Lightweight iPaaS](#zapier--lightweight-ipaas)
- [iPaaS Governance](#ipaas-governance)

---

## iPaaS vs Custom Code Decision Framework

### Decision Matrix

| Factor | iPaaS Wins | Custom Code Wins |
|--------|------------|------------------|
| **Volume** | < 100k records/day | > 1M records/day |
| **Complexity** | Standard transformations | Complex business logic, ML models |
| **Speed to Market** | Days to weeks | Weeks to months |
| **Maintainers** | Citizen integrators, low-code teams | Software engineers |
| **Connector Availability** | Standard SaaS apps (Salesforce, NetSuite) | Custom APIs, legacy systems |
| **Cost at Scale** | Lower initial, higher at volume | Higher initial, lower at volume |
| **Flexibility** | Limited by platform capabilities | Full control over logic and performance |
| **Testing** | Built-in test framework | Custom test suite required |
| **Monitoring** | Platform-native dashboards | Custom observability stack |
| **Compliance** | SOC2/HIPAA certified platforms | Full data control and audit trail |

### Total Cost of Ownership Comparison

**iPaaS (Workato example):**
```
Year 1:
- Platform license: $60,000/year (25 recipes)
- Implementation: 2 weeks × $150/hr × 80hrs = $12,000
- Training: $3,000
Total: $75,000

Year 2+:
- License: $60,000
- Maintenance: 10hrs/month × $150/hr × 12 = $18,000
Annual: $78,000
```

**Custom Code (Python + Airflow):**
```
Year 1:
- Infrastructure (cloud): $12,000/year
- Development: 8 weeks × $175/hr × 320hrs = $56,000
- CI/CD setup: $8,000
Total: $76,000

Year 2+:
- Infrastructure: $12,000
- Maintenance: 20hrs/month × $175/hr × 12 = $42,000
Annual: $54,000
```

**Break-even analysis:** iPaaS costs more at scale due to recipe/task limits. Custom code amortizes development cost over time.

### Hybrid Approaches

**Pattern 1: iPaaS for Orchestration, Custom for Heavy Lifting**

```python
# Workato calls custom API endpoint for complex transform
@app.route('/transform/customer_scoring', methods=['POST'])
def score_customers():
    """Complex ML-based customer scoring unavailable in iPaaS"""
    batch = request.json['customers']

    # Load ML model
    model = load_model('customer_lifetime_value.pkl')

    # Feature engineering
    features = engineer_features(batch)

    # Predict
    scores = model.predict(features)

    return jsonify({
        'scored_customers': [
            {**cust, 'ltv_score': score}
            for cust, score in zip(batch, scores)
        ]
    })
```

**Workato recipe step:**
```
1. Trigger: Salesforce new account batch
2. Action: Call HTTP endpoint /transform/customer_scoring
3. Action: Upsert scored data to Snowflake
```

**Pattern 2: Custom Code for Extraction, iPaaS for Distribution**

```python
# Airflow DAG extracts from complex legacy system
@dag(schedule_interval='@daily')
def extract_mainframe_orders():
    @task
    def extract():
        # Complex COBOL file parsing
        orders = parse_ebcdic_file('/data/orders.dat')
        upload_to_s3(orders, 'staging/orders.json')

    # Trigger Workato webhook when complete
    @task
    def trigger_distribution(s3_path):
        requests.post(
            'https://hooks.workato.com/webhooks/rest/xyz',
            json={'s3_path': s3_path, 'record_count': len(orders)}
        )
```

**Workato picks up from webhook and distributes to 10 downstream systems via pre-built connectors.**

### When to Choose What

**Choose iPaaS when:**
- Integrating 3+ standard SaaS applications
- Business users need self-service integration capability
- Time-to-value matters more than cost-per-transaction
- Volume stays under platform limits
- Pre-built connectors cover 80%+ of needs

**Choose Custom Code when:**
- Processing millions of records daily
- Complex transformation logic (ML, graph algorithms)
- Sub-second latency requirements
- Working with proprietary protocols or legacy systems
- Need full control over data flow and security

**Choose Hybrid when:**
- Need both speed-to-market AND scale
- Have mix of standard SaaS and custom systems
- Want to isolate complex logic from orchestration
- Team has both engineers and citizen integrators

---

## Workato

### Recipe Architecture

Workato recipes consist of:
- **Trigger:** Event that starts recipe execution
- **Actions:** Steps performed in sequence or parallel
- **Conditions:** If/else logic for branching
- **Repeat/For-each:** Iteration over arrays
- **Call Recipe:** Invoke sub-workflows

**Basic Recipe Structure:**

```ruby
# Trigger
When Salesforce Account is created or updated

# Conditions
If Account.Industry equals "Healthcare"
  AND Account.AnnualRevenue > 1000000

# Actions
  1. Search for matching customer in NetSuite

  2. If NetSuite customer exists:
       Update NetSuite customer with Salesforce data
     Else:
       Create new NetSuite customer

  3. Log activity to Snowflake audit table

  4. Call recipe: "Send welcome email to high-value customer"
```

### Connector Ecosystem and Custom Connectors

**Pre-built Connectors (1000+):**
- CRM: Salesforce, HubSpot, Dynamics
- ERP: NetSuite, SAP, Oracle
- Data Warehouses: Snowflake, BigQuery, Redshift
- Productivity: Slack, Teams, Gmail

**Custom Connector SDK Example:**

```ruby
# custom_api_connector.rb
{
  title: 'Custom ERP System',

  connection: {
    fields: [
      { name: 'api_key', control_type: 'password' },
      { name: 'base_url' }
    ],

    authorization: {
      type: 'custom_auth',
      apply: lambda do |connection|
        headers('Authorization': "Bearer #{connection['api_key']}")
      end
    },

    base_uri: lambda do |connection|
      connection['base_url']
    end
  },

  object_definitions: {
    order: {
      fields: lambda do
        [
          { name: 'order_id', type: 'integer' },
          { name: 'customer_id', type: 'string' },
          { name: 'total_amount', type: 'number' },
          { name: 'order_date', type: 'date_time' },
          { name: 'line_items', type: 'array', of: 'object',
            properties: [
              { name: 'sku', type: 'string' },
              { name: 'quantity', type: 'integer' },
              { name: 'unit_price', type: 'number' }
            ]
          }
        ]
      end
    }
  },

  actions: {
    get_order: {
      input_fields: lambda do
        [{ name: 'order_id', type: 'integer', required: true }]
      end,

      execute: lambda do |connection, input|
        get("/api/v2/orders/#{input['order_id']}")
      end,

      output_fields: lambda do |object_definitions|
        object_definitions['order']
      end
    }
  }
}
```

### Workato Recipes vs Callable Recipes

**Regular Recipe:**
- Triggered by external event (webhook, polling, schedule)
- Runs independently
- Cannot be invoked by other recipes

**Callable Recipe (Sub-workflow):**

```ruby
# Callable Recipe: "Enrich Customer Data"
# Input Schema:
{
  customer_email: { type: 'string', required: true },
  customer_id: { type: 'string' }
}

# Steps:
1. Call Clearbit API to enrich email
2. Call ZoomInfo for company data
3. Return enriched data

# Output Schema:
{
  email: 'string',
  full_name: 'string',
  company_name: 'string',
  company_size: 'integer',
  industry: 'string',
  technologies: 'array'
}
```

**Calling from Parent Recipe:**

```ruby
When new lead in Marketo:
  1. Call recipe "Enrich Customer Data"
       Input: { customer_email: Lead.Email }

  2. Update Marketo lead with enrichment data
       Company: Step1.company_name
       Industry: Step1.industry

  3. If Step1.company_size > 1000:
       Create opportunity in Salesforce
```

### Data Mapping and Transformation Formulas

**Formula Examples:**

```ruby
# String manipulation
"#{first_name} #{last_name}".upcase
# => "JOHN SMITH"

email.split('@').last
# => "acme.com" from "john@acme.com"

# Date/time
created_at.beginning_of_month
updated_at.strftime('%Y-%m-%d')

# Math
(subtotal * 1.08).round(2)  # Add 8% tax

# Arrays
line_items.pluck('quantity').sum
order_lines.map { |line| line['price'] * line['qty'] }.sum

# Conditionals
amount > 10000 ? 'Enterprise' : 'Standard'

# Null handling
customer_name.presence || 'Unknown'
```

**Complex Transformation Example:**

```ruby
# Transform Salesforce opportunity to NetSuite sales order
{
  'externalId': salesforce_opp['Id'],
  'entity': {
    'internalId': netsuite_customer_lookup['internal_id']
  },
  'tranDate': salesforce_opp['CloseDate'],
  'otherRefNum': salesforce_opp['OpportunityNumber'],
  'customFieldList': {
    'customField': [
      {
        'scriptId': 'custbody_sf_opp_id',
        'value': salesforce_opp['Id']
      },
      {
        'scriptId': 'custbody_sales_rep',
        'value': salesforce_opp['Owner']['Name']
      }
    ]
  },
  'itemList': {
    'item': salesforce_opp['OpportunityLineItems'].map do |line|
      {
        'item': { 'internalId': sku_mapping[line['ProductCode']] },
        'quantity': line['Quantity'],
        'rate': line['UnitPrice'],
        'amount': line['TotalPrice']
      }
    end
  }
}
```

### Error Handling

**Retry Policies:**

```ruby
Configure recipe settings:
- Retry count: 3
- Retry interval: 5 minutes (exponential backoff)
- Stop recipe on repeated failures: Yes (after 5 consecutive failures)
```

**Error Handler Blocks:**

```ruby
When Salesforce account updated:

  1. Update NetSuite customer

  Monitor action:
    On error:
      1. Log error to Snowflake
           INSERT INTO integration_errors VALUES (
             error_message: error_message,
             recipe_name: recipe_name,
             record_id: salesforce_account['Id'],
             timestamp: now
           )

      2. Send Slack alert to #data-ops
           Message: "NetSuite sync failed for account #{account_name}: #{error_message}"

      3. Create ticket in Jira
           Project: DATA
           Summary: "Integration failure: Salesforce -> NetSuite"
           Description: Full error details
```

### Best Practices

**Recipe Naming Convention:**

```
[Source] -> [Destination]: [Entity] [Action]

Examples:
- Salesforce -> NetSuite: Account Sync
- Marketo -> Snowflake: Lead Export (Hourly)
- Webhook -> Slack: Order Notification
```

**Folder Organization:**

```
/Integrations
  /CRM
    /Salesforce-NetSuite
      - Account Sync
      - Opportunity Sync
      - Contact Sync
    /Salesforce-Marketo
      - Lead Bidirectional Sync
  /Data Warehouse
    /Snowflake Exports
      - Daily Order Export
      - Customer Master Export
  /Notifications
    - Order Alerts
    - Error Notifications
  /Utilities
    - Callable: Enrich Customer
    - Callable: Validate Address
```

**Connection Management:**

- Use separate connections for dev/test/prod
- Rotate API keys quarterly
- Use service accounts (not personal accounts)
- Document connection owners and purpose

### Example Recipe: Salesforce → Snowflake Sync

```ruby
# Recipe: Salesforce -> Snowflake: Account Daily Sync
# Schedule: Daily at 2 AM UTC

Trigger: Scheduled event (Daily 2:00 AM UTC)

Actions:
  1. Search Salesforce accounts
       Created or updated in last 24 hours
       Fields: Id, Name, Industry, AnnualRevenue, BillingAddress, Owner.Name
       Batch size: 2000

  2. For each batch of accounts:

       2a. Transform to Snowflake schema
            accounts_batch = step1.accounts.map do |acc|
              {
                sf_account_id: acc['Id'],
                account_name: acc['Name'],
                industry: acc['Industry'],
                annual_revenue: acc['AnnualRevenue'],
                billing_city: acc['BillingAddress']['city'],
                billing_state: acc['BillingAddress']['state'],
                billing_country: acc['BillingAddress']['country'],
                owner_name: acc['Owner']['Name'],
                last_modified_date: acc['LastModifiedDate'],
                synced_at: now
              }
            end

       2b. Execute Snowflake SQL
            MERGE INTO raw.salesforce.accounts tgt
            USING (
              SELECT
                parse_json(column1) as src
              FROM TABLE(FLATTEN(input => parse_json(:json_array)))
            ) src
            ON tgt.sf_account_id = src:sf_account_id::string
            WHEN MATCHED THEN UPDATE SET
              account_name = src:account_name::string,
              industry = src:industry::string,
              annual_revenue = src:annual_revenue::number,
              billing_city = src:billing_city::string,
              billing_state = src:billing_state::string,
              billing_country = src:billing_country::string,
              owner_name = src:owner_name::string,
              last_modified_date = src:last_modified_date::timestamp,
              synced_at = src:synced_at::timestamp
            WHEN NOT MATCHED THEN INSERT (
              sf_account_id, account_name, industry, annual_revenue,
              billing_city, billing_state, billing_country, owner_name,
              last_modified_date, synced_at
            ) VALUES (
              src:sf_account_id::string,
              src:account_name::string,
              src:industry::string,
              src:annual_revenue::number,
              src:billing_city::string,
              src:billing_state::string,
              src:billing_country::string,
              src:owner_name::string,
              src:last_modified_date::timestamp,
              src:synced_at::timestamp
            );

            Parameters:
              json_array: accounts_batch.to_json

  3. Log summary to Snowflake audit table
       INSERT INTO ops.recipe_runs VALUES (
         :recipe_id, :recipe_name, :started_at, :completed_at,
         :records_processed, :status, :error_message
       )

  Monitor all actions:
    On error: Send Slack alert + create Jira ticket
```

### Recipe Lifecycle: Dev → Test → Prod

**Development Environment:**
- Use sandbox Salesforce org
- Use dev Snowflake database
- Test with small data sets
- Enable verbose logging

**Testing:**
- Export recipe package
- Import to test workspace
- Update connections to test environment
- Run test cases (happy path + error scenarios)
- Verify data quality and idempotency

**Production Promotion:**

```bash
# Export recipe package (via UI)
# Download: salesforce_snowflake_sync_v1.2.zip

# Import via API
curl -X POST https://www.workato.com/api/packages/import \
  -H "Authorization: Bearer $PROD_API_TOKEN" \
  -F "file=@salesforce_snowflake_sync_v1.2.zip" \
  -F "folder_id=12345"

# Update connections to prod
# Start recipe
# Monitor first few runs
```

**Version Control:**
- Export recipe packages on every change
- Store in Git with semantic versioning
- Document changes in CHANGELOG.md

---

## MuleSoft (Anypoint Platform)

### Mule 4 Architecture

**Core Concepts:**
- **Flows:** Sequences of event processors
- **Connectors:** Pre-built integrations (Database, HTTP, Salesforce, etc.)
- **DataWeave:** Transformation language for data mapping
- **Error Handlers:** Centralized error management
- **Configuration Properties:** Environment-specific settings

**Flow Structure:**

```xml
<!-- src/main/mule/salesforce-to-database-sync.xml -->
<mule xmlns="http://www.mulesoft.org/schema/mule/core">

  <flow name="sync-salesforce-accounts">
    <!-- Source/Trigger -->
    <scheduler doc:name="Daily Scheduler">
      <scheduling-strategy>
        <cron expression="0 0 2 * * ?" timeZone="UTC"/>
      </scheduling-strategy>
    </scheduler>

    <!-- Query Salesforce -->
    <salesforce:query doc:name="Query Accounts"
                      config-ref="Salesforce_Config">
      <salesforce:salesforce-query>
        SELECT Id, Name, Industry, AnnualRevenue
        FROM Account
        WHERE LastModifiedDate = YESTERDAY
      </salesforce:salesforce-query>
    </salesforce:query>

    <!-- Transform -->
    <ee:transform doc:name="Map to DB Schema">
      <ee:message>
        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
payload map {
  sf_id: $.Id,
  name: $.Name,
  industry: $.Industry,
  revenue: $.AnnualRevenue,
  synced_at: now()
}]]></ee:set-payload>
      </ee:message>
    </ee:transform>

    <!-- Insert to Database -->
    <db:bulk-insert doc:name="Bulk Insert"
                    config-ref="Database_Config">
      <db:sql>
        INSERT INTO accounts (sf_id, name, industry, revenue, synced_at)
        VALUES (:sf_id, :name, :industry, :revenue, :synced_at)
      </db:sql>
    </db:bulk-insert>

    <!-- Log Success -->
    <logger level="INFO"
            message="#['Synced ' ++ sizeOf(payload) ++ ' accounts']"/>
  </flow>

  <!-- Error Handler -->
  <error-handler>
    <on-error-propagate type="SALESFORCE:CONNECTIVITY">
      <logger level="ERROR" message="Salesforce connection failed"/>
      <http:request method="POST" url="${slack.webhook.url}">
        <http:body>#[{text: "Salesforce sync failed: connection error"}]</http:body>
      </http:request>
    </on-error-propagate>

    <on-error-continue type="DB:QUERY_EXECUTION">
      <logger level="ERROR" message="Database insert failed"/>
      <!-- Retry logic or dead letter queue -->
    </on-error-continue>
  </error-handler>
</mule>
```

### API-led Connectivity

**Three-Layer Architecture:**

1. **System APIs:** Direct access to systems of record
2. **Process APIs:** Orchestrate business processes
3. **Experience APIs:** Tailored for specific channels (mobile, web, partners)

**Example System API (Customer System API):**

```xml
<!-- get-customer-flow.xml -->
<flow name="get-customer">
  <http:listener path="/customers/{customerId}"
                 method="GET"
                 config-ref="HTTP_Listener_config"/>

  <db:select config-ref="Database_Config">
    <db:sql>
      SELECT * FROM customers WHERE customer_id = :customerId
    </db:sql>
    <db:input-parameters>#[{customerId: attributes.uriParams.customerId}]</db:input-parameters>
  </db:select>

  <ee:transform>
    <ee:message>
      <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  customerId: payload[0].customer_id,
  firstName: payload[0].first_name,
  lastName: payload[0].last_name,
  email: payload[0].email,
  phone: payload[0].phone
}]]></ee:set-payload>
    </ee:message>
  </ee:transform>
</flow>
```

**Example Process API (Order Fulfillment Process API):**

```xml
<flow name="create-order-process">
  <http:listener path="/orders" method="POST"/>

  <!-- Step 1: Validate customer -->
  <http:request method="GET"
                url="${customer.api.url}/customers/{customerId}"
                config-ref="HTTP_Request_config">
    <http:uri-params>#[{customerId: payload.customerId}]</http:uri-params>
  </http:request>

  <choice doc:name="Customer exists?">
    <when expression="#[attributes.statusCode == 200]">
      <set-variable variableName="customer" value="#[payload]"/>

      <!-- Step 2: Create order in ERP -->
      <http:request method="POST"
                    url="${erp.api.url}/orders"
                    config-ref="ERP_Config">
        <http:body>#[payload]</http:body>
      </http:request>

      <set-variable variableName="orderId" value="#[payload.orderId]"/>

      <!-- Step 3: Initiate shipping -->
      <http:request method="POST"
                    url="${shipping.api.url}/shipments">
        <http:body>#[{
          orderId: vars.orderId,
          address: vars.customer.shippingAddress
        }]</http:body>
      </http:request>

      <!-- Return response -->
      <ee:transform>
        <ee:message>
          <ee:set-payload>#[{
            orderId: vars.orderId,
            status: "CREATED",
            estimatedDelivery: payload.estimatedDelivery
          }]</ee:set-payload>
        </ee:message>
      </ee:transform>
    </when>
    <otherwise>
      <raise-error type="APP:CUSTOMER_NOT_FOUND"/>
    </otherwise>
  </choice>
</flow>
```

### DataWeave Transformation Examples

**Basic Transformations:**

```dataweave
%dw 2.0
output application/json

// Input: Salesforce Account
{
  id: payload.Id,
  name: payload.Name,
  // Conditional field
  tier: if (payload.AnnualRevenue > 1000000) "Enterprise" else "Standard",
  // String manipulation
  domain: payload.Website replace /^https?:\/\// with "" replace /\/$/ with "",
  // Date formatting
  createdDate: payload.CreatedDate as Date {format: "yyyy-MM-dd"},
  // Array transformation
  contacts: payload.Contacts map {
    fullName: $.FirstName ++ " " ++ $.LastName,
    email: $.Email
  }
}
```

**Complex Aggregation:**

```dataweave
%dw 2.0
output application/json

// Input: Array of orders
{
  summary: {
    totalOrders: sizeOf(payload),
    totalRevenue: sum(payload.amount),
    avgOrderValue: avg(payload.amount),
    topCustomers: (payload groupBy $.customerId)
      pluck {
        customerId: $$,
        orderCount: sizeOf($),
        totalSpent: sum($.amount)
      }
      orderBy -$.totalSpent
      take 10
  },
  ordersByStatus: payload groupBy $.status
}
```

**JSON to XML:**

```dataweave
%dw 2.0
output application/xml
---
{
  Order @(id: payload.orderId): {
    Customer: {
      Name: payload.customer.name,
      Email: payload.customer.email
    },
    Items: {
      (payload.lineItems map {
        Item @(sku: $.sku): {
          Quantity: $.quantity,
          Price: $.price
        }
      })
    },
    Total: sum(payload.lineItems.price)
  }
}
```

### Anypoint Exchange

**Publishing Reusable Assets:**

```bash
# Publish connector fragment
mvn clean deploy -DaltDeploymentRepository=exchange::default::https://maven.anypoint.mulesoft.com/api/v1/organizations/${ORG_ID}/maven

# pom.xml
<groupId>com.mycompany.exchange</groupId>
<artifactId>customer-connector</artifactId>
<version>1.2.0</version>
<packaging>mule-extension</packaging>
```

**Using Exchange Assets:**

```xml
<!-- pom.xml -->
<dependency>
  <groupId>com.mycompany.exchange</groupId>
  <artifactId>customer-connector</artifactId>
  <version>1.2.0</version>
  <classifier>mule-plugin</classifier>
</dependency>

<!-- In flow -->
<customer:get-customer config-ref="Customer_Config"
                       customerId="#[attributes.uriParams.id]"/>
```

### CloudHub vs Runtime Fabric vs On-Prem

| Feature | CloudHub | Runtime Fabric | On-Premise |
|---------|----------|----------------|------------|
| **Hosting** | Mulesoft-managed AWS | Customer VPC (AWS/Azure) | Customer data center |
| **Scaling** | Auto-scale workers | Manual/auto-scale replicas | Manual |
| **Deployment** | 1-click from Anypoint | kubectl/Anypoint | Standalone runtime |
| **Networking** | Public endpoints + VPN | Private within VPC | Fully private |
| **Cost** | Per vCore-hour | License + infrastructure | License + hardware |
| **Best For** | Quick deployments, SaaS integrations | Enterprise security, hybrid | Air-gapped, legacy systems |

### Error Handling

**On-Error-Continue (Catch and Continue):**

```xml
<flow name="process-orders">
  <foreach collection="#[payload.orders]">
    <try>
      <http:request url="${erp.url}/orders" method="POST">
        <http:body>#[payload]</http:body>
      </http:request>

      <error-handler>
        <on-error-continue type="HTTP:TIMEOUT">
          <logger message="Order timeout, moving to retry queue"/>
          <jms:publish destination="retry-queue" config-ref="JMS">
            <jms:message>#[payload]</jms:message>
          </jms:publish>
        </on-error-continue>
      </error-handler>
    </try>
  </foreach>
</flow>
```

**On-Error-Propagate (Catch and Fail):**

```xml
<error-handler>
  <on-error-propagate type="DB:CONNECTIVITY">
    <logger level="ERROR" message="Database down, failing flow"/>
    <set-payload value="#[{error: 'Database unavailable'}]"/>
    <set-variable variableName="httpStatus" value="503"/>
  </on-error-propagate>
</error-handler>
```

### Example: REST API → Database Sync Flow

```xml
<!-- sync-api.xml -->
<mule xmlns="http://www.mulesoft.org/schema/mule/core">

  <!-- Configuration -->
  <configuration-properties file="config-${env}.yaml"/>

  <http:listener-config name="HTTP_Listener">
    <http:listener-connection host="0.0.0.0" port="8081"/>
  </http:listener-config>

  <db:config name="Database_Config">
    <db:my-sql-connection
      host="${db.host}"
      port="${db.port}"
      user="${db.user}"
      password="${db.password}"
      database="${db.name}"/>
  </db:config>

  <!-- Main Flow -->
  <flow name="api-to-db-sync">
    <scheduler>
      <scheduling-strategy>
        <fixed-frequency frequency="15" timeUnit="MINUTES"/>
      </scheduling-strategy>
    </scheduler>

    <!-- Call external API -->
    <http:request method="GET"
                  url="${external.api.url}/products"
                  config-ref="External_API_Config">
      <http:headers>#[{
        'Authorization': 'Bearer ' ++ p('api.token'),
        'Accept': 'application/json'
      }]</http:headers>
    </http:request>

    <!-- Validate response -->
    <choice>
      <when expression="#[attributes.statusCode == 200]">
        <flow-ref name="transform-and-load"/>
      </when>
      <otherwise>
        <raise-error type="APP:API_ERROR"
                     description="#['API returned ' ++ attributes.statusCode]"/>
      </otherwise>
    </choice>
  </flow>

  <!-- Sub-flow: Transform and Load -->
  <sub-flow name="transform-and-load">
    <!-- Parse and transform -->
    <ee:transform>
      <ee:message>
        <ee:set-payload><![CDATA[%dw 2.0
output application/java
---
payload.products map {
  product_id: $.id,
  name: $.name,
  category: $.category,
  price: $.price as Number,
  in_stock: $.inventory.quantity > 0,
  last_updated: now()
}]]></ee:set-payload>
      </ee:message>
    </ee:transform>

    <!-- Upsert to database -->
    <foreach collection="#[payload]">
      <db:update config-ref="Database_Config">
        <db:sql><![CDATA[
          INSERT INTO products (product_id, name, category, price, in_stock, last_updated)
          VALUES (:product_id, :name, :category, :price, :in_stock, :last_updated)
          ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            category = VALUES(category),
            price = VALUES(price),
            in_stock = VALUES(in_stock),
            last_updated = VALUES(last_updated)
        ]]></db:sql>
        <db:input-parameters>#[payload]</db:input-parameters>
      </db:update>
    </foreach>

    <!-- Log completion -->
    <logger level="INFO"
            message="#['Synced ' ++ vars.initialPayloadSize ++ ' products']"/>
  </sub-flow>

</mule>
```

### CI/CD with Maven and Anypoint CLI

**Maven Deployment:**

```xml
<!-- pom.xml -->
<plugin>
  <groupId>org.mule.tools.maven</groupId>
  <artifactId>mule-maven-plugin</artifactId>
  <version>3.8.0</version>
  <configuration>
    <cloudHubDeployment>
      <uri>https://anypoint.mulesoft.com</uri>
      <muleVersion>4.4.0</muleVersion>
      <username>${anypoint.username}</username>
      <password>${anypoint.password}</password>
      <applicationName>salesforce-sync-prod</applicationName>
      <environment>Production</environment>
      <region>us-east-1</region>
      <workers>2</workers>
      <workerType>MICRO</workerType>
      <properties>
        <env>prod</env>
        <db.host>${prod.db.host}</db.host>
      </properties>
    </cloudHubDeployment>
  </configuration>
</plugin>
```

**GitHub Actions Pipeline:**

```yaml
# .github/workflows/deploy.yml
name: Deploy to CloudHub

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up JDK 8
        uses: actions/setup-java@v3
        with:
          java-version: 8

      - name: Deploy to CloudHub
        env:
          ANYPOINT_USERNAME: ${{ secrets.ANYPOINT_USERNAME }}
          ANYPOINT_PASSWORD: ${{ secrets.ANYPOINT_PASSWORD }}
        run: |
          mvn clean deploy -DmuleDeploy \
            -Danypoint.username=$ANYPOINT_USERNAME \
            -Danypoint.password=$ANYPOINT_PASSWORD
```

---

## Boomi

### AtomSphere Architecture

**Atom Types:**
- **Atom:** Single-tenant runtime (cloud or on-prem)
- **Molecule:** Clustered runtime for high availability (2-4 nodes)
- **Atom Cloud:** Multi-tenant shared infrastructure

**Deployment Model Decision:**

| Requirement | Recommendation |
|-------------|----------------|
| On-prem database access | Local Atom |
| High availability needed | Molecule (2+ nodes) |
| Simple cloud-to-cloud | Atom Cloud |
| Data residency regulations | Local Atom in specific region |
| High throughput (> 1M docs/day) | Molecule |

### Process Building Blocks

**Process Components:**

```
[Start Shape] → [Connector] → [Map] → [Decision] → [Connector] → [End Shape]
```

**Example Process Structure:**

```
Process: Salesforce to Database Sync

1. [Start: Timer] - Runs daily at 2 AM
   ↓
2. [Salesforce Connector: Query]
   - Operation: Query
   - Object: Account
   - Query: LastModifiedDate = YESTERDAY
   ↓
3. [Data Process: Filter]
   - Condition: Annual Revenue > 100000
   ↓
4. [Map: Transform to DB Schema]
   - Source: Salesforce Account
   - Destination: Database Table Profile
   ↓
5. [Decision: Check Record Count]
   - If > 0: Continue
   - If = 0: Skip to End
   ↓
6. [Database Connector: Insert/Update]
   - Operation: Upsert
   - Table: accounts
   - Match Key: salesforce_id
   ↓
7. [Notify: Email Success]
   - To: data-ops@company.com
   - Subject: Salesforce sync completed
   ↓
8. [Stop]

Error Path (on any failure):
   → [Notify: Slack Alert]
   → [Database: Log Error]
   → [Stop with Error]
```

### Data Maps and Profile-Based Transformations

**Profile Definition (Schema):**

```xml
<!-- Salesforce Account Profile -->
<Profile>
  <Field name="Id" type="String"/>
  <Field name="Name" type="String"/>
  <Field name="Industry" type="String"/>
  <Field name="AnnualRevenue" type="Decimal"/>
  <Field name="BillingAddress" type="Complex">
    <Field name="street" type="String"/>
    <Field name="city" type="String"/>
    <Field name="state" type="String"/>
    <Field name="postalCode" type="String"/>
  </Field>
</Profile>

<!-- Database Table Profile -->
<Profile>
  <Field name="salesforce_id" type="String"/>
  <Field name="company_name" type="String"/>
  <Field name="industry_code" type="String"/>
  <Field name="revenue" type="Number"/>
  <Field name="city" type="String"/>
  <Field name="state" type="String"/>
  <Field name="zip" type="String"/>
  <Field name="last_synced" type="DateTime"/>
</Profile>
```

**Map Configuration:**

```
Source (Salesforce) → Transformation → Destination (Database)

Id                 → [Direct]        → salesforce_id
Name               → [Direct]        → company_name
Industry           → [Scripting]     → industry_code
                     // Lookup industry code
                     if (Industry == "Technology") "TECH"
                     else if (Industry == "Healthcare") "HLTH"
                     else "OTH"

AnnualRevenue      → [Direct]        → revenue
BillingAddress.city → [Direct]       → city
BillingAddress.state → [Direct]      → state
BillingAddress.postalCode → [Direct] → zip
                   → [Function]      → last_synced
                     // Current timestamp
                     dateTimeNow()
```

**Advanced Mapping Functions:**

```javascript
// Concatenate fields
concat(FirstName, " ", LastName)

// Conditional mapping
if(AnnualRevenue > 1000000, "Enterprise", "SMB")

// Date formatting
formatDate(CreatedDate, "yyyy-MM-dd")

// Null handling
nvl(MiddleName, "")

// Lookup from cross-reference table
lookupCrossReference("IndustryCodeMap", Industry)

// Aggregate (in grouped mapping)
sum(LineItems[*].Amount)

// String manipulation
substring(PhoneNumber, 0, 3)  // Area code
upper(Country)
```

### Flow Services (API Creation)

**Create REST API in Boomi:**

```
Flow Service: Customer API

GET /customers/{id}
  → [Database Query Shape]
      SELECT * FROM customers WHERE id = {id}
  → [Map: DB to JSON Response]
  → [Return HTTP 200]

POST /customers
  → [Map: JSON Request to DB Profile]
  → [Database Insert Shape]
      INSERT INTO customers (...)
  → [Map: Success Response]
  → [Return HTTP 201]

PUT /customers/{id}
  → [Database Update Shape]
  → [Return HTTP 200]

DELETE /customers/{id}
  → [Database Delete Shape]
  → [Return HTTP 204]

Error Handling:
  - 400: Invalid JSON
  - 404: Customer not found
  - 500: Database error
```

**API Deployment:**

```
1. Create API in Boomi
2. Deploy to API Gateway (Boomi API Management)
3. Configure authentication (OAuth 2.0, API Key)
4. Set rate limits and quotas
5. Publish to developer portal
```

### Master Data Hub for Golden Records

**MDH Concepts:**
- **Match and Merge:** Identify duplicates and create golden record
- **Match Rules:** Define how to find duplicates
- **Merge Rules:** Define which values to keep
- **Survivorship:** Rules for field-level golden record creation

**Example Configuration:**

```
Entity: Customer

Match Rules:
  - Exact match on email
  - Fuzzy match on (firstName + lastName + company) > 85% similarity
  - Exact match on phone number

Merge Rules (Survivorship):
  Field         | Rule
  --------------|-------------------
  email         | Most recent update
  firstName     | Longest value
  lastName      | Longest value
  company       | Most frequent value
  phone         | Most recent update
  address       | Most complete (fewest nulls)
  revenue       | Maximum value
  created_date  | Minimum (earliest)

Source Priority (when tie-breaking):
  1. Salesforce (CRM of record)
  2. NetSuite (ERP)
  3. Marketo (Marketing)
```

**Golden Record Process:**

```
Process: Customer Golden Record Creation

1. [Start: New/Updated Customer from any source]
   ↓
2. [MDH: Match Existing Records]
   - Apply match rules
   - Return potential duplicates
   ↓
3. [Decision: Match Found?]

   If YES:
     → [MDH: Merge Records]
         - Apply merge/survivorship rules
         - Create/update golden record
     → [Publish: Golden Record to Subscribers]
         - Snowflake data warehouse
         - Salesforce (update if needed)
         - Customer 360 app

   If NO:
     → [MDH: Create New Golden Record]
     → [Publish: New Golden Record]
   ↓
4. [Stop]
```

### Example: ERP → CRM Data Sync Process

```
Process: NetSuite Customer → Salesforce Account Sync

Schedule: Every 15 minutes

1. [Start: Timer - Every 15 min]
   ↓
2. [NetSuite Connector: Query Customers]
   Operation: Search
   Record Type: Customer
   Criteria: Last Modified > {lastRunTime}
   Fields: internalId, companyName, email, phone, billingAddress
   ↓
3. [Decision: Records Found?]
   If NO → Jump to End
   If YES → Continue
   ↓
4. [For Each Customer Record]
   ↓
   4a. [Salesforce Connector: Query Account]
       SOQL: SELECT Id FROM Account WHERE NetSuite_ID__c = '{internalId}'
   ↓
   4b. [Decision: Account Exists?]

       If EXISTS:
         → [Map: NetSuite to Salesforce Update]
             internalId → NetSuite_ID__c
             companyName → Name
             email → Email__c
             phone → Phone
             billingAddress.city → BillingCity
             billingAddress.state → BillingState
         → [Salesforce Connector: Update Account]

       If NOT EXISTS:
         → [Map: NetSuite to Salesforce Create]
             (same mappings as update)
         → [Salesforce Connector: Create Account]
   ↓
   4c. [Database: Log Sync Record]
       INSERT INTO sync_log (
         source_system, source_id, target_system, target_id,
         operation, status, synced_at
       )
   ↓
5. [Email: Send Summary]
   To: data-ops@company.com
   Subject: NetSuite → Salesforce sync completed
   Body:
     Total processed: {recordCount}
     Created: {createCount}
     Updated: {updateCount}
     Errors: {errorCount}
   ↓
6. [Stop]

Error Handler:
  On any connector error:
    → [Try: Retry 3 times with 5 min delay]
    → If still failing:
        → [Slack: Alert #data-ops channel]
        → [Database: Log detailed error]
        → [Email: Send error details]
        → [Move failed record to error queue]
```

---

## Zapier & Lightweight iPaaS

### When Zapier is Enough vs Enterprise iPaaS

**Use Zapier when:**
- Small team (< 50 people)
- Simple workflows (< 10 steps)
- Low volume (< 100k tasks/month)
- Connecting popular SaaS apps (Gmail, Slack, Trello, Sheets)
- Need self-service for non-technical users
- Budget-conscious (< $1000/month)

**Use Enterprise iPaaS when:**
- Large organization (> 100 people)
- Complex workflows with conditional logic, loops, error handling
- High volume (> 1M tasks/month)
- Custom APIs or legacy systems
- Need governance, audit trails, role-based access
- Require SLA guarantees and dedicated support

**Comparison:**

| Feature | Zapier | Workato | MuleSoft |
|---------|--------|---------|----------|
| **Ease of Use** | Excellent | Good | Moderate |
| **Pre-built Apps** | 5000+ | 1000+ | 300+ |
| **Custom Code** | Limited (Code by Zapier) | Python/Ruby formulas | Full DataWeave |
| **Volume Limits** | 50k-2M tasks/month | Unlimited (recipe-based) | Unlimited |
| **Pricing** | $20-800/mo | $10k-100k+/yr | $50k-500k+/yr |
| **Error Handling** | Basic retries | Advanced handlers | Enterprise-grade |
| **Governance** | Minimal | Strong | Enterprise |

### Multi-step Zaps, Paths, Filters

**Basic Multi-step Zap:**

```
Trigger: New Salesforce Opportunity (Stage = Closed Won)
  ↓
Filter: Amount > $10,000
  ↓
Action 1: Create customer in Stripe
  Customer Email: {{opportunity.email}}
  Customer Name: {{opportunity.name}}
  ↓
Action 2: Create invoice in QuickBooks
  Customer: {{stripe_customer.id}}
  Amount: {{opportunity.amount}}
  ↓
Action 3: Send Slack notification to #sales
  Message: "New ${{amount}} deal closed with {{customer_name}}"
  ↓
Action 4: Add row to Google Sheets (Sales Tracker)
  Date: {{opportunity.close_date}}
  Customer: {{opportunity.name}}
  Amount: {{opportunity.amount}}
  Rep: {{opportunity.owner}}
```

**Paths (Conditional Branching):**

```
Trigger: New HubSpot Contact

Paths:

  Path A: Lead Score > 80
    Condition: {{contact.lead_score}} > 80
    ↓
    Action: Create Salesforce Lead (Hot)
    Action: Assign to Sales Rep via Round Robin
    Action: Send Slack alert to #sales-hot-leads

  Path B: Lead Score 50-80
    Condition: {{contact.lead_score}} >= 50 AND <= 80
    ↓
    Action: Add to Marketo nurture campaign
    Action: Send welcome email series

  Path C: Lead Score < 50
    Condition: {{contact.lead_score}} < 50
    ↓
    Action: Add to monthly newsletter list only
```

**Filters:**

```
Trigger: New Gmail Email

Filter 1: From address contains "@acme.com"
  Only continue if: {{from_email}} contains "@acme.com"

Filter 2: Subject contains "Invoice"
  Only continue if: {{subject}} contains "Invoice"

Action: Save attachment to Dropbox
  Folder: /Invoices/{{from_name}}
  File: {{subject}}_{{received_date}}.pdf
```

### Webhooks by Zapier for Custom Integrations

**Catch Webhook (Receive Data):**

```
Step 1: Webhooks by Zapier - Catch Hook
  → Generates unique URL: https://hooks.zapier.com/hooks/catch/123456/abcdef/

Step 2: Test webhook with curl
  curl -X POST https://hooks.zapier.com/hooks/catch/123456/abcdef/ \
    -H "Content-Type: application/json" \
    -d '{
      "customer_id": "12345",
      "event": "purchase",
      "amount": 299.99,
      "timestamp": "2026-02-13T10:30:00Z"
    }'

Step 3: Zapier parses JSON and makes fields available
  {{customer_id}} = "12345"
  {{event}} = "purchase"
  {{amount}} = 299.99

Step 4: Use in subsequent actions
  Action: Update Salesforce Account
    Account ID: {{customer_id}}
    Last Purchase Amount: {{amount}}
    Last Purchase Date: {{timestamp}}
```

**Send Webhook (POST Data):**

```
Trigger: New Stripe payment

Action: Webhooks by Zapier - POST
  URL: https://your-api.com/webhooks/payment
  Payload Type: JSON
  Data:
    {
      "payment_id": "{{stripe.payment_id}}",
      "customer_email": "{{stripe.customer_email}}",
      "amount": {{stripe.amount}},
      "currency": "{{stripe.currency}}",
      "status": "{{stripe.status}}",
      "created_at": "{{stripe.created}}"
    }
  Headers:
    Authorization: Bearer YOUR_API_TOKEN
    Content-Type: application/json
```

**Custom Code for Complex Logic:**

```
Trigger: New Typeform submission

Action: Code by Zapier (Python)
  Input Data:
    responses: {{typeform.answers}}

  Code:
    import json

    # Parse Typeform responses
    responses = input_data['responses']

    # Calculate lead score based on answers
    score = 0

    for response in responses:
        if response['field']['type'] == 'dropdown':
            if 'Enterprise' in response['text']:
                score += 30
            elif 'Professional' in response['text']:
                score += 20

        if response['field']['type'] == 'number':
            company_size = int(response['number'])
            if company_size > 500:
                score += 40
            elif company_size > 100:
                score += 25
            elif company_size > 20:
                score += 10

    # Determine priority
    if score >= 60:
        priority = 'Hot'
        owner = 'enterprise-sales@company.com'
    elif score >= 30:
        priority = 'Warm'
        owner = 'sales@company.com'
    else:
        priority = 'Cold'
        owner = 'marketing@company.com'

    return {
        'lead_score': score,
        'priority': priority,
        'assigned_to': owner
    }

  Output:
    {{lead_score}}
    {{priority}}
    {{assigned_to}}

Next Action: Create Salesforce Lead
  Lead Score: {{lead_score}}
  Priority: {{priority}}
  Owner Email: {{assigned_to}}
```

### Rate Limits and Task-Based Pricing Implications

**Zapier Task Consumption:**

| Action Type | Tasks Consumed |
|-------------|----------------|
| Trigger check (no new data) | 0 |
| Trigger finds new item | 1 per item |
| Action executed | 1 per action |
| Filter (passes) | 0 |
| Filter (stops) | 0 |
| Path evaluation | 0 |
| Looping (3 items) | 3 |

**Example Calculation:**

```
Zap: Salesforce → Slack + Google Sheets

Daily execution:
- 100 new Salesforce opportunities (trigger)
- Filter: 60 pass amount > $5k
- Action 1: Send Slack message (60 executions)
- Action 2: Add to Google Sheets (60 executions)

Daily tasks: 100 (trigger) + 60 (Slack) + 60 (Sheets) = 220 tasks
Monthly tasks: 220 × 30 = 6,600 tasks

Zapier plan needed: Professional ($49/mo for 50k tasks)
```

**Rate Limits:**

- **Trigger frequency:** 1-15 minutes (depending on plan)
- **API rate limits:** Respected per connected app (e.g., Salesforce: 15k API calls/day)
- **Execution time:** 30 seconds per action (5 minutes on premium)
- **Webhook payload:** 10 MB max

**Optimization Strategies:**

```
BAD: Individual triggers for each record
  Trigger: New Salesforce Account
  Process: 1000 new accounts = 1000 Zap runs = 1000+ tasks

GOOD: Batch processing
  Trigger: Schedule (daily)
  Action: Salesforce - Find Records (created yesterday)
  Loop: Process batch = 1 trigger + 1000 actions = 1001 tasks

BETTER: Use Zapier's built-in batching
  Many apps support batch operations (reduces tasks)
```

### Tray.io as Mid-Market Alternative

**Tray.io Advantages:**
- Unlimited workflows (no recipe/zap limits)
- Advanced logic: loops, conditions, error handling
- Better for high-volume (transaction-based pricing)
- GraphQL support
- Better API for programmatic workflow creation

**When to Choose Tray.io:**
- Need > 50 workflows
- Volume > 500k operations/month
- Require advanced data transformations
- Want embedded integration builder (for SaaS products)
- Budget: $20k-100k/year

**Example Tray.io Workflow:**

```
Trigger: Webhook (customer signup)
  ↓
Branch 1: Sync to CRM
  → Salesforce Create Lead
  → Set lead source
  ↓
Branch 2: Provision Services (parallel)
  → Create Stripe customer
  → Create Intercom user
  → Create Zendesk organization
  ↓
Join: Wait for all branches
  ↓
Loop: Send onboarding emails
  Day 1: Welcome email
  Day 3: Getting started guide
  Day 7: Feature highlight
  ↓
End
```

---

## iPaaS Governance

### Connection Credential Management

**Best Practices:**

1. **Use Service Accounts:**
   - Create dedicated integration users (not personal accounts)
   - Name: `integration-salesforce@company.com`
   - Document owner and purpose

2. **Credential Rotation:**
   ```
   Schedule:
   - API keys: Rotate every 90 days
   - OAuth tokens: Refresh automatically
   - Database passwords: Rotate every 180 days

   Process:
   1. Generate new credentials in source system
   2. Update in iPaaS platform (test connection)
   3. Deploy to all environments
   4. Revoke old credentials after 7-day grace period
   ```

3. **Secrets Management:**
   - Store in iPaaS platform's encrypted vault (never in code)
   - Use environment-specific credentials (dev/test/prod)
   - Implement least-privilege access

4. **Connection Monitoring:**
   ```sql
   -- Alert on failing connections
   SELECT
     connection_name,
     last_successful_auth,
     failure_count,
     last_error_message
   FROM integration_connections
   WHERE
     last_successful_auth < CURRENT_DATE - INTERVAL '1 day'
     OR failure_count > 5
   ```

### Environment Promotion Workflows

**Standard Environments:**

```
Development → Test → Staging → Production
```

**Workato Promotion Process:**

```bash
# 1. Export from Development
# Download package: customer-sync-v2.1.zip

# 2. Import to Test
curl -X POST https://www.workato.com/api/packages/import \
  -H "Authorization: Bearer $TEST_API_TOKEN" \
  -F "file=@customer-sync-v2.1.zip" \
  -F "folder_id=67890"

# 3. Update connections to test environment
# Via UI: Connections > Switch to Test Connections

# 4. Run test suite
pytest tests/integration/test_customer_sync.py

# 5. If tests pass, repeat for Staging
# 6. If staging validates, promote to Production (with approval)
```

**Approval Gates:**

```yaml
# .github/workflows/ipaas-deploy.yml
name: Deploy Integration

on:
  push:
    branches: [main]

jobs:
  deploy-test:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Test
        run: ./scripts/deploy-workato.sh test

  deploy-staging:
    needs: deploy-test
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: ./scripts/deploy-workato.sh staging

  deploy-prod:
    needs: deploy-staging
    environment: production  # Requires manual approval
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Production
        run: ./scripts/deploy-workato.sh prod

      - name: Notify deployment
        run: |
          curl -X POST $SLACK_WEBHOOK \
            -d '{"text":"Integration deployed to production: customer-sync-v2.1"}'
```

### Monitoring and Alerting Setup

**Key Metrics to Monitor:**

```
1. Execution Metrics:
   - Recipe/flow success rate
   - Execution duration (p50, p95, p99)
   - Records processed per hour
   - Error rate by error type

2. System Health:
   - Connection status (all integrations)
   - API quota usage
   - Recipe job queue depth
   - Atom/runtime resource usage (CPU, memory)

3. Business Metrics:
   - Data latency (source update → destination sync)
   - Data quality (validation failures)
   - SLA compliance (on-time sync rate)
```

**Alerting Configuration (Workato Example):**

```ruby
# Recipe: Monitor Integration Health

Trigger: Schedule (every 5 minutes)

Actions:
  1. HTTP GET: Workato API - Get Recipe Jobs
       URL: https://www.workato.com/api/recipes/{recipe_id}/jobs
       Params: { from: now - 5 minutes }

  2. Calculate metrics:
       total_jobs = jobs.count
       failed_jobs = jobs.filter { |j| j.status == 'failed' }.count
       error_rate = (failed_jobs / total_jobs) * 100
       avg_duration = jobs.map { |j| j.duration }.avg

  3. If error_rate > 5%:
       Send PagerDuty alert:
         Severity: error
         Summary: "Integration error rate: #{error_rate}%"
         Details: Failed recipe names and error messages

  4. If avg_duration > 60 seconds:
       Send Slack warning:
         Channel: #data-ops
         Message: "Integration running slow: avg #{avg_duration}s"

  5. Log metrics to Datadog:
       POST https://api.datadoghq.com/api/v1/series
       {
         "series": [
           {
             "metric": "workato.recipe.jobs.total",
             "points": [[now, total_jobs]],
             "tags": ["recipe:customer-sync", "env:prod"]
           },
           {
             "metric": "workato.recipe.error_rate",
             "points": [[now, error_rate]]
           }
         ]
       }
```

**Dashboard Example (Grafana/Datadog):**

```
Panel 1: Recipe Execution Success Rate (Last 24h)
  - Line graph showing success % by hour
  - Alert threshold at 95%

Panel 2: Top 10 Failing Recipes
  - Bar chart of error counts
  - Click to view error details

Panel 3: Data Sync Latency
  - Heatmap showing latency distribution
  - By integration and time of day

Panel 4: API Quota Usage
  - Gauge showing % of daily quota used
  - Per connected system (Salesforce, NetSuite, etc.)

Panel 5: Records Processed
  - Time series of records/hour
  - Segmented by integration
```

### Audit Logging and Compliance

**Audit Log Requirements:**

```sql
CREATE TABLE integration_audit_log (
  log_id BIGINT PRIMARY KEY,
  timestamp TIMESTAMP NOT NULL,
  recipe_name VARCHAR(255),
  recipe_id VARCHAR(100),
  job_id VARCHAR(100),

  -- What happened
  operation VARCHAR(50),  -- CREATE, UPDATE, DELETE, EXPORT
  entity_type VARCHAR(100),  -- Account, Order, Customer
  entity_id VARCHAR(255),

  -- Who/what triggered it
  trigger_type VARCHAR(50),  -- SCHEDULE, WEBHOOK, MANUAL
  triggered_by VARCHAR(255),  -- User email or system

  -- Source and destination
  source_system VARCHAR(100),
  destination_system VARCHAR(100),

  -- Data payload (encrypted)
  data_before TEXT,  -- JSON (for updates/deletes)
  data_after TEXT,   -- JSON (for creates/updates)

  -- Outcome
  status VARCHAR(20),  -- SUCCESS, FAILED, RETRYING
  error_message TEXT,
  records_processed INT,

  -- Compliance
  pii_accessed BOOLEAN,
  data_classification VARCHAR(50),  -- PUBLIC, INTERNAL, CONFIDENTIAL

  INDEX idx_timestamp (timestamp),
  INDEX idx_entity (entity_type, entity_id),
  INDEX idx_user (triggered_by)
);
```

**GDPR Compliance - Data Access Request:**

```sql
-- Find all integrations that touched a customer's data
SELECT
  recipe_name,
  operation,
  source_system,
  destination_system,
  timestamp,
  data_after
FROM integration_audit_log
WHERE
  entity_type = 'Customer'
  AND entity_id = 'customer-12345'
  AND timestamp >= '2024-01-01'
ORDER BY timestamp DESC;
```

**SOC2 Compliance - Access Controls:**

```
Requirements:
1. Role-based access control (RBAC)
2. Audit trail of configuration changes
3. Encryption at rest and in transit
4. Annual access reviews

Implementation in Workato:
- Roles: Admin, Developer, Operator, Viewer
- Audit: All recipe changes logged with user and timestamp
- Encryption: AES-256 for credentials, TLS 1.2+ for data transfer
- Access Review: Quarterly report of user permissions
```

### Cost Management

**Task/Recipe-Based Billing:**

```
Workato Pricing Example:
- Base: 25 recipes + 100k tasks/month = $60k/year
- Additional recipes: $2400/year per recipe
- Additional tasks: $0.40 per 1000 tasks

Optimization strategies:
1. Consolidate recipes using conditions (1 smart recipe vs 5 simple ones)
2. Increase polling interval for non-critical syncs (5 min → 15 min)
3. Use batch operations where possible
4. Implement filters early to skip unnecessary processing
```

**Cost Monitoring Dashboard:**

```sql
-- Monthly cost projection
SELECT
  DATE_TRUNC('month', execution_date) AS month,
  recipe_name,
  COUNT(*) AS tasks_used,
  COUNT(*) * 0.0004 AS estimated_cost_usd
FROM recipe_executions
WHERE execution_date >= CURRENT_DATE - INTERVAL '3 months'
GROUP BY 1, 2
ORDER BY 4 DESC;

-- Identify cost outliers
SELECT
  recipe_name,
  AVG(tasks_per_run) AS avg_tasks,
  STDDEV(tasks_per_run) AS stddev_tasks,
  MAX(tasks_per_run) AS max_tasks
FROM (
  SELECT
    recipe_name,
    DATE(execution_time) AS run_date,
    COUNT(*) AS tasks_per_run
  FROM recipe_executions
  GROUP BY 1, 2
) daily_stats
GROUP BY 1
HAVING MAX(tasks_per_run) > AVG(tasks_per_run) + (2 * STDDEV(tasks_per_run))
ORDER BY max_tasks DESC;
```

### Documentation Standards for Integration Catalog

**Integration Catalog Template:**

```markdown
# Integration: Salesforce → NetSuite Customer Sync

## Overview
- **Purpose:** Sync customer accounts from Salesforce to NetSuite in near real-time
- **Owner:** Data Engineering Team (data-eng@company.com)
- **Status:** Active
- **Criticality:** High (impacts order processing)

## Technical Details
- **Platform:** Workato
- **Recipe ID:** 12345
- **Recipe URL:** https://app.workato.com/recipes/12345
- **Trigger:** Salesforce Account created/updated (polling every 5 min)
- **Destinations:** NetSuite Customer record
- **Volume:** ~500 accounts/day, peak 2000/day
- **SLA:** 99.5% uptime, sync within 15 minutes

## Data Flow
```
Salesforce Account → [Workato] → NetSuite Customer
Fields mapped:
  - Id → External ID (SF_Account_ID)
  - Name → Company Name
  - BillingAddress → Address
  - Industry → Category
```

## Dependencies
- **Upstream:** Salesforce production org
- **Downstream:** NetSuite production account
- **Related Integrations:**
  - NetSuite → Snowflake (uses NetSuite customer data)
  - Salesforce → Marketo (shares account data)

## Monitoring
- **Dashboard:** [Grafana link]
- **Alerts:** PagerDuty escalation to #data-ops
- **Metrics:**
  - Success rate: Target 99.5%
  - Sync latency: Target < 10 minutes
  - Error budget: 50 failures/week

## Runbook
### Common Issues
1. **NetSuite API quota exceeded**
   - Symptom: 429 errors in recipe logs
   - Resolution: Wait for quota reset (hourly), or contact NetSuite to increase limit

2. **Salesforce connection failure**
   - Symptom: SALESFORCE:CONNECTIVITY errors
   - Resolution: Check API limits, refresh OAuth token, verify IP whitelist

### Emergency Contacts
- On-call: PagerDuty rotation
- Escalation: Jane Doe (jane@company.com)

## Change History
| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-02-01 | 2.1 | Added industry field mapping | John Smith |
| 2025-12-15 | 2.0 | Migrated to new NetSuite connector | Jane Doe |
| 2025-06-01 | 1.0 | Initial deployment | Team |
```

**Integration Catalog Index:**

```yaml
# integrations.yaml
integrations:
  - name: Salesforce → NetSuite Customer Sync
    id: sf-ns-customer-sync
    platform: Workato
    status: active
    criticality: high
    owner: data-engineering
    docs: docs/integrations/sf-ns-customer-sync.md

  - name: Marketo → Snowflake Lead Export
    id: marketo-snowflake-leads
    platform: Fivetran
    status: active
    criticality: medium
    owner: analytics
    docs: docs/integrations/marketo-snowflake.md

  - name: NetSuite → BigQuery Orders
    id: ns-bq-orders
    platform: MuleSoft
    status: deprecated
    deprecation_date: 2026-03-01
    replacement: netsuite-snowflake-orders
    docs: docs/integrations/ns-bq-orders.md
```

---

Back to [main skill](../SKILL.md)
