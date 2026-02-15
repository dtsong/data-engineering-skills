# iPaaS Platforms

## iPaaS vs Custom Code Decision

| Factor | iPaaS Wins | Custom Code Wins |
|--------|------------|------------------|
| Volume | < 100k records/day | > 1M records/day |
| Complexity | Standard transforms | Complex logic, ML |
| Speed to market | Days-weeks | Weeks-months |
| Maintainers | Low-code teams | Engineers |
| Connectors | Standard SaaS | Custom/legacy |
| Cost at scale | Lower initial, higher volume | Higher initial, lower volume |

**Hybrid patterns:** (1) iPaaS orchestrates, custom API handles heavy transforms. (2) Custom code extracts from legacy, iPaaS distributes via pre-built connectors.

## Workato

**Recipe structure:** Trigger -> Conditions -> Actions -> Error Handler. Supports callable sub-recipes for reusable logic.

**Custom Connector SDK:** Define connection (auth), object definitions (schema), actions/triggers in Ruby DSL.

**Formulas:** `email.split('@').last`, `amount > 10000 ? 'Enterprise' : 'Standard'`, `customer_name.presence || 'Unknown'`.

**Error handling:** Configure retry count + exponential backoff. Use Monitor blocks to catch errors, log to Snowflake, alert Slack, create Jira tickets.

**Naming:** `[Source] -> [Destination]: [Entity] [Action]` (e.g., "Salesforce -> NetSuite: Account Sync").

**Promotion:** Export recipe package from dev -> import to test (update connections) -> run test suite -> promote to staging -> production (with approval gate).

## MuleSoft (Anypoint Platform)

**Architecture:** Three-layer API-led connectivity: System APIs (direct system access) -> Process APIs (orchestrate business logic) -> Experience APIs (channel-specific).

**Core concepts:** Flows (event processor sequences), Connectors (pre-built integrations), DataWeave (transformation language), Error Handlers.

**DataWeave examples:**

```dataweave
%dw 2.0
output application/json
---
payload map {
  id: $.Id,
  tier: if ($.AnnualRevenue > 1000000) "Enterprise" else "Standard",
  domain: $.Website replace /^https?:\/\// with "",
  contacts: $.Contacts map {
    fullName: $.FirstName ++ " " ++ $.LastName,
    email: $.Email
  }
}
```

**Error handling:** `on-error-continue` (catch and continue, e.g., retry queue), `on-error-propagate` (catch and fail, e.g., return 503).

**Deployment:** CloudHub (managed AWS, quick), Runtime Fabric (customer VPC, private), On-Premise (air-gapped).

**CI/CD:** Maven plugin for CloudHub deployment, GitHub Actions pipeline with environment promotion.

## Boomi

**Atom types:** Atom (single-tenant), Molecule (clustered HA), Atom Cloud (multi-tenant).

**Process flow:** Start Shape -> Connector -> Map -> Decision -> Connector -> End Shape. Maps use profile-based transformations with functions: `concat()`, `if()`, `formatDate()`, `lookupCrossReference()`.

**Master Data Hub:** Match rules (exact email, fuzzy name > 85%, exact phone) + merge rules (survivorship per field) -> golden record.

**Flow Services:** Create REST APIs directly in Boomi with CRUD operations + error handling.

## Zapier & Lightweight iPaaS

**Use Zapier when:** Small team (< 50), simple workflows (< 10 steps), low volume (< 100k tasks/month), popular SaaS apps, budget < $1000/mo.

**Task consumption:** Trigger finds item = 1, each action = 1, filter = 0, loop over 3 items = 3. Optimize with batch operations and increased polling intervals.

**Tray.io for mid-market:** Unlimited workflows, advanced logic, better for > 500k ops/month, GraphQL support, embedded integration builder.

## iPaaS Governance

**Credential management:**
- Use dedicated service accounts (`integration-salesforce@company.com`)
- Rotate API keys every 90 days, DB passwords every 180 days
- Environment-specific credentials (dev/test/prod)
- Store in platform's encrypted vault, never in code

**Monitoring metrics:** Recipe success rate, execution duration (p50/p95/p99), API quota usage, data sync latency, error rate by type.

**Audit logging:** Track operation, entity, trigger type, source/destination systems, data payload (encrypted), PII access flag. Support GDPR data access requests and SOC2 compliance.

**Cost management:** Consolidate recipes with conditions, increase polling intervals for non-critical syncs, use batch operations, implement early filters.
