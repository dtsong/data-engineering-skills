# Data Mapping and Crosswalks

> **Part of:** [integration-patterns-skill](../SKILL.md)
> **Purpose:** Deep dive into canonical models, field mappings, crosswalk tables, and schema drift detection

## Table of Contents

- [Canonical Data Models](#canonical-data-models)
- [Field Mapping Tables](#field-mapping-tables)
- [Crosswalk Tables](#crosswalk-tables)
- [Schema Drift Detection](#schema-drift-detection)
- [Metadata Management](#metadata-management)

---

## Canonical Data Models

### What is a Canonical Model and Why Use One

A **canonical data model** is a unified, standard representation of business entities used across multiple systems. Instead of directly translating between N systems (requiring N² mappings), you translate each system to/from the canonical model (requiring only 2N mappings).

**Without Canonical Model:**

```
Salesforce ←→ NetSuite
    ↕           ↕
HubSpot   ←→ Zendesk
    ↕           ↕
Marketo   ←→ Snowflake

Total mappings needed: 6 systems × 5 connections each = 30 mappings
```

**With Canonical Model:**

```
Salesforce → Canonical Customer Model → NetSuite
HubSpot    →            ↓              → Zendesk
Marketo    →            ↓              → Snowflake

Total mappings needed: 6 systems × 2 directions = 12 mappings
```

**Benefits:**
- **Reduced complexity:** Linear growth (2N) vs quadratic (N²)
- **Single source of truth:** One definition of "Customer"
- **Easier maintenance:** Change canonical model, not every integration
- **Data quality:** Validation rules enforced at canonical layer
- **Onboarding new systems:** Only map to canonical model

**When NOT to Use:**
- Simple point-to-point integration (2 systems, no growth planned)
- Real-time, high-throughput scenarios (canonical adds latency)
- Systems have identical schemas (direct copy sufficient)

### Domain-Driven Design Approach

Organize canonical models around **bounded contexts** (business domains):

**Bounded Contexts:**

```
Customer Domain:
  - Customer
  - Contact
  - Address

Order Domain:
  - Order
  - OrderLine
  - Shipment

Product Domain:
  - Product
  - ProductCategory
  - PriceList

Finance Domain:
  - Invoice
  - Payment
  - Transaction
```

**Context Relationships:**

```
Customer ──has──> Order ──contains──> Product
   ↓                 ↓
Address          Shipment
```

### Example Canonical Models

**Customer Entity:**

```python
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CustomerTier(Enum):
    PROSPECT = "prospect"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class CustomerStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"

@dataclass
class Address:
    """Canonical address model"""
    address_type: str  # "billing", "shipping", "physical"
    street_line1: str
    street_line2: Optional[str] = None
    city: str
    state_province: str
    postal_code: str
    country_code: str  # ISO 3166-1 alpha-2
    is_primary: bool = False

@dataclass
class Customer:
    """Canonical customer model"""
    # Identity
    canonical_id: str  # UUID in canonical system
    external_ids: dict[str, str]  # {"salesforce": "001...", "netsuite": "12345"}

    # Core attributes
    customer_name: str
    customer_type: str  # "individual", "business"
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None

    # Business attributes
    tier: CustomerTier = CustomerTier.STANDARD
    status: CustomerStatus = CustomerStatus.ACTIVE
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    industry: Optional[str] = None  # Standard industry codes

    # Addresses
    addresses: List[Address] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str  # System or user ID
    updated_by: str

    # Data quality
    data_quality_score: Optional[float] = None  # 0.0 to 1.0
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.addresses is None:
            self.addresses = []
        if self.validation_errors is None:
            self.validation_errors = []

    def validate(self) -> bool:
        """Validate canonical model rules"""
        self.validation_errors = []

        if not self.customer_name or len(self.customer_name) < 2:
            self.validation_errors.append("customer_name must be at least 2 characters")

        if self.email and '@' not in self.email:
            self.validation_errors.append("email must be valid format")

        if self.annual_revenue and self.annual_revenue < 0:
            self.validation_errors.append("annual_revenue cannot be negative")

        if len(self.addresses) > 0:
            primary_count = sum(1 for addr in self.addresses if addr.is_primary)
            if primary_count == 0:
                self.validation_errors.append("at least one address must be primary")
            if primary_count > 1:
                self.validation_errors.append("only one address can be primary")

        return len(self.validation_errors) == 0
```

**Order Entity:**

```python
from decimal import Decimal
from typing import List

@dataclass
class OrderLine:
    """Canonical order line item"""
    line_number: int
    product_id: str  # Reference to canonical product
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal = Decimal('0.00')
    tax_amount: Decimal = Decimal('0.00')
    line_total: Decimal = Decimal('0.00')

    def __post_init__(self):
        # Calculate line total
        self.line_total = (
            (self.unit_price * self.quantity)
            - self.discount_amount
            + self.tax_amount
        )

@dataclass
class Order:
    """Canonical order model"""
    # Identity
    canonical_id: str
    external_ids: dict[str, str]  # {"shopify": "12345", "erp": "SO-00678"}

    # Relationships
    customer_id: str  # Reference to canonical customer
    customer_name: str

    # Core attributes
    order_number: str
    order_date: datetime
    order_status: str  # "pending", "confirmed", "shipped", "delivered", "cancelled"
    currency: str  # ISO 4217 code

    # Line items
    line_items: List[OrderLine]

    # Financials
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    shipping_cost: Decimal
    grand_total: Decimal

    # Fulfillment
    shipping_address: Address
    requested_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    def calculate_totals(self):
        """Calculate order totals from line items"""
        self.subtotal = sum(line.line_total for line in self.line_items)
        self.discount_total = sum(line.discount_amount for line in self.line_items)
        self.tax_total = sum(line.tax_amount for line in self.line_items)
        self.grand_total = self.subtotal + self.tax_total + self.shipping_cost
```

**Product Entity:**

```python
@dataclass
class Product:
    """Canonical product model"""
    # Identity
    canonical_id: str
    external_ids: dict[str, str]

    # Core attributes
    sku: str  # Stock Keeping Unit (unique)
    product_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None

    # Pricing
    list_price: Decimal
    cost: Decimal
    currency: str  # ISO 4217

    # Inventory
    in_stock: bool
    stock_quantity: int
    reorder_point: Optional[int] = None

    # Physical attributes
    weight: Optional[Decimal] = None  # kg
    weight_unit: str = "kg"
    dimensions: Optional[dict] = None  # {"length": 10, "width": 5, "height": 3, "unit": "cm"}

    # Status
    is_active: bool = True
    discontinued_date: Optional[datetime] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
```

### Versioning Canonical Models

**Strategy 1: Major Version in Model Name**

```python
@dataclass
class CustomerV1:
    canonical_id: str
    customer_name: str
    email: str
    # ... original fields

@dataclass
class CustomerV2:
    canonical_id: str
    customer_name: str
    email: str
    phone: str  # NEW required field
    tier: CustomerTier  # NEW field
    # ... other fields

# Transformation layer handles version migration
def upgrade_customer_v1_to_v2(v1: CustomerV1) -> CustomerV2:
    return CustomerV2(
        canonical_id=v1.canonical_id,
        customer_name=v1.customer_name,
        email=v1.email,
        phone=None,  # Default for missing field
        tier=CustomerTier.STANDARD,  # Default tier
        # ... map other fields
    )
```

**Strategy 2: Schema Version Field**

```python
@dataclass
class Customer:
    schema_version: int = 2  # Current version
    canonical_id: str
    customer_name: str
    # ... fields

    @classmethod
    def from_dict(cls, data: dict):
        """Load customer with version handling"""
        version = data.get('schema_version', 1)

        if version == 1:
            # Upgrade V1 to V2
            data['phone'] = data.get('phone', None)
            data['tier'] = data.get('tier', 'standard')
            data['schema_version'] = 2

        return cls(**data)
```

**Strategy 3: Event Sourcing with Upcasting**

```python
# Store events, not state
CustomerCreated(v1) → CustomerPhoneAdded(v2) → CustomerTierSet(v2)

# When reading, upcast old events to current schema
def upcast_event(event):
    if isinstance(event, CustomerCreatedV1):
        # Transform V1 event to V2 structure
        return CustomerCreatedV2(
            **event.__dict__,
            phone=None,
            tier='standard'
        )
    return event
```

### Pydantic for Validation

```python
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class Address(BaseModel):
    address_type: str
    street_line1: str
    street_line2: Optional[str] = None
    city: str
    state_province: str
    postal_code: str
    country_code: str
    is_primary: bool = False

    @validator('country_code')
    def validate_country_code(cls, v):
        if len(v) != 2:
            raise ValueError('country_code must be ISO 3166-1 alpha-2 (2 chars)')
        return v.upper()

class Customer(BaseModel):
    canonical_id: str
    external_ids: dict[str, str] = Field(default_factory=dict)

    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_type: str
    email: EmailStr
    phone: Optional[str] = None
    website: Optional[str] = None

    tier: str = "standard"
    status: str = "active"
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    employee_count: Optional[int] = Field(None, ge=1)
    industry: Optional[str] = None

    addresses: List[Address] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    @validator('tier')
    def validate_tier(cls, v):
        allowed = ['prospect', 'standard', 'premium', 'enterprise']
        if v not in allowed:
            raise ValueError(f'tier must be one of {allowed}')
        return v

    @validator('addresses')
    def validate_primary_address(cls, v):
        if not v:
            return v
        primary_count = sum(1 for addr in v if addr.is_primary)
        if primary_count > 1:
            raise ValueError('only one address can be primary')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# Usage
try:
    customer = Customer(
        canonical_id="c-12345",
        customer_name="Acme Corp",
        customer_type="business",
        email="contact@acme.com",
        annual_revenue=-1000,  # Invalid
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="system",
        updated_by="system"
    )
except ValueError as e:
    print(f"Validation error: {e}")
    # Validation error: annual_revenue must be >= 0
```

---

## Field Mapping Tables

### Structure

A **field mapping table** defines how source system fields map to canonical model fields, including transformation rules.

**Schema:**

```sql
CREATE TABLE field_mappings (
  mapping_id SERIAL PRIMARY KEY,
  source_system VARCHAR(100) NOT NULL,  -- "salesforce", "netsuite", "hubspot"
  source_table VARCHAR(100) NOT NULL,   -- "Account", "Customer", "Contact"
  source_field VARCHAR(100) NOT NULL,   -- "AnnualRevenue", "CompanyName"

  canonical_entity VARCHAR(100) NOT NULL,  -- "customer", "order", "product"
  canonical_field VARCHAR(100) NOT NULL,   -- "annual_revenue", "customer_name"

  transform_rule TEXT,  -- Transformation logic (SQL expression or function name)
  data_type VARCHAR(50),  -- "string", "integer", "decimal", "date", "boolean"

  is_required BOOLEAN DEFAULT FALSE,
  default_value TEXT,  -- Default if source is NULL

  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(source_system, source_table, source_field, canonical_field)
);

CREATE INDEX idx_mappings_source ON field_mappings(source_system, source_table);
CREATE INDEX idx_mappings_canonical ON field_mappings(canonical_entity);
```

### Example Mapping Data

```sql
-- Salesforce Account → Canonical Customer
INSERT INTO field_mappings (source_system, source_table, source_field, canonical_entity, canonical_field, transform_rule, data_type, is_required) VALUES
('salesforce', 'Account', 'Id', 'customer', 'external_ids.salesforce', 'direct', 'string', TRUE),
('salesforce', 'Account', 'Name', 'customer', 'customer_name', 'direct', 'string', TRUE),
('salesforce', 'Account', 'Type', 'customer', 'customer_type', 'CASE WHEN Type = ''Customer'' THEN ''business'' WHEN Type = ''Prospect'' THEN ''individual'' ELSE ''unknown'' END', 'string', FALSE),
('salesforce', 'Account', 'AnnualRevenue', 'customer', 'annual_revenue', 'CAST(AnnualRevenue AS DECIMAL)', 'decimal', FALSE),
('salesforce', 'Account', 'Industry', 'customer', 'industry', 'lookup_industry_code(Industry)', 'string', FALSE),
('salesforce', 'Account', 'Email__c', 'customer', 'email', 'LOWER(TRIM(Email__c))', 'string', TRUE),
('salesforce', 'Account', 'BillingStreet', 'customer', 'addresses[0].street_line1', 'direct', 'string', FALSE),
('salesforce', 'Account', 'BillingCity', 'customer', 'addresses[0].city', 'direct', 'string', FALSE),
('salesforce', 'Account', 'BillingState', 'customer', 'addresses[0].state_province', 'direct', 'string', FALSE),
('salesforce', 'Account', 'BillingPostalCode', 'customer', 'addresses[0].postal_code', 'direct', 'string', FALSE),
('salesforce', 'Account', 'BillingCountry', 'customer', 'addresses[0].country_code', 'lookup_country_code(BillingCountry)', 'string', FALSE);

-- NetSuite Customer → Canonical Customer
INSERT INTO field_mappings (source_system, source_table, source_field, canonical_entity, canonical_field, transform_rule, data_type, is_required) VALUES
('netsuite', 'Customer', 'internalId', 'customer', 'external_ids.netsuite', 'CAST(internalId AS TEXT)', 'string', TRUE),
('netsuite', 'Customer', 'companyName', 'customer', 'customer_name', 'direct', 'string', TRUE),
('netsuite', 'Customer', 'email', 'customer', 'email', 'LOWER(TRIM(email))', 'string', TRUE),
('netsuite', 'Customer', 'phone', 'customer', 'phone', 'format_phone(phone)', 'string', FALSE),
('netsuite', 'Customer', 'category', 'customer', 'tier', 'CASE WHEN category = ''Enterprise'' THEN ''enterprise'' WHEN category = ''Premium'' THEN ''premium'' ELSE ''standard'' END', 'string', FALSE);
```

### Dynamic Mapping Execution

**Python Implementation:**

```python
import sqlalchemy as sa
from sqlalchemy import create_engine
import pandas as pd
from typing import Any, Dict

class FieldMapper:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def get_mappings(self, source_system: str, source_table: str) -> pd.DataFrame:
        """Fetch mappings for a source system/table"""
        query = """
            SELECT *
            FROM field_mappings
            WHERE source_system = :source_system
              AND source_table = :source_table
            ORDER BY canonical_field
        """
        return pd.read_sql(
            query,
            self.engine,
            params={'source_system': source_system, 'source_table': source_table}
        )

    def apply_mapping(self, source_data: Dict[str, Any], mappings: pd.DataFrame) -> Dict[str, Any]:
        """Apply field mappings to source data"""
        canonical_data = {}

        for _, mapping in mappings.iterrows():
            source_field = mapping['source_field']
            canonical_field = mapping['canonical_field']
            transform_rule = mapping['transform_rule']
            default_value = mapping['default_value']

            # Get source value
            source_value = source_data.get(source_field)

            # Apply default if missing
            if source_value is None and default_value:
                source_value = default_value

            # Apply transformation
            if transform_rule == 'direct':
                canonical_value = source_value
            elif transform_rule.startswith('CASE'):
                # Execute SQL CASE statement (simplified)
                canonical_value = self._execute_case_statement(transform_rule, source_data)
            elif transform_rule.startswith('lookup_'):
                # Call lookup function
                function_name = transform_rule.split('(')[0]
                canonical_value = self._call_lookup_function(function_name, source_value)
            elif transform_rule.startswith('CAST'):
                # Type casting
                canonical_value = self._apply_cast(transform_rule, source_value)
            else:
                # Generic SQL expression
                canonical_value = self._evaluate_expression(transform_rule, source_data)

            # Set canonical field (handle nested fields like "addresses[0].city")
            self._set_nested_field(canonical_data, canonical_field, canonical_value)

        return canonical_data

    def _set_nested_field(self, data: dict, field_path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        if '.' in field_path:
            # Handle nested fields: "addresses[0].city"
            parts = field_path.replace('[', '.').replace(']', '').split('.')
            current = data
            for part in parts[:-1]:
                if part.isdigit():
                    # Array index
                    idx = int(part)
                    if not isinstance(current, list):
                        current = []
                    while len(current) <= idx:
                        current.append({})
                    current = current[idx]
                else:
                    # Object key
                    if part not in current:
                        current[part] = {}
                    current = current[part]
            current[parts[-1]] = value
        else:
            data[field_path] = value

    def _call_lookup_function(self, function_name: str, value: Any) -> Any:
        """Call registered lookup function"""
        lookup_functions = {
            'lookup_industry_code': self._lookup_industry_code,
            'lookup_country_code': self._lookup_country_code,
            'format_phone': self._format_phone,
        }
        func = lookup_functions.get(function_name)
        if func:
            return func(value)
        return value

    def _lookup_industry_code(self, industry_name: str) -> str:
        """Map industry name to standard code"""
        industry_map = {
            'Technology': 'TECH',
            'Healthcare': 'HLTH',
            'Financial Services': 'FINC',
            'Manufacturing': 'MANU',
            'Retail': 'RETL',
        }
        return industry_map.get(industry_name, 'OTHR')

    def _lookup_country_code(self, country_name: str) -> str:
        """Map country name to ISO 3166-1 alpha-2 code"""
        country_map = {
            'United States': 'US',
            'Canada': 'CA',
            'United Kingdom': 'GB',
            'Germany': 'DE',
            'France': 'FR',
        }
        return country_map.get(country_name, 'XX')

    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format"""
        if not phone:
            return None
        # Simple formatting (real implementation would use phonenumbers library)
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"+1{digits}"  # Assume US
        return f"+{digits}"

# Usage
mapper = FieldMapper('postgresql://user:pass@localhost/db')

# Fetch mappings for Salesforce Account
mappings = mapper.get_mappings('salesforce', 'Account')

# Sample Salesforce data
salesforce_account = {
    'Id': '001XXXXXXXX',
    'Name': 'Acme Corporation',
    'Type': 'Customer',
    'AnnualRevenue': 5000000,
    'Industry': 'Technology',
    'Email__c': 'contact@acme.com',
    'BillingStreet': '123 Main St',
    'BillingCity': 'San Francisco',
    'BillingState': 'CA',
    'BillingPostalCode': '94105',
    'BillingCountry': 'United States'
}

# Apply mapping
canonical_customer = mapper.apply_mapping(salesforce_account, mappings)

print(canonical_customer)
# {
#   'external_ids': {'salesforce': '001XXXXXXXX'},
#   'customer_name': 'Acme Corporation',
#   'customer_type': 'business',
#   'annual_revenue': 5000000.0,
#   'industry': 'TECH',
#   'email': 'contact@acme.com',
#   'addresses': [
#     {
#       'street_line1': '123 Main St',
#       'city': 'San Francisco',
#       'state_province': 'CA',
#       'postal_code': '94105',
#       'country_code': 'US'
#     }
#   ]
# }
```

### Maintaining Mappings: YAML Version Control

**mappings/salesforce_account.yaml:**

```yaml
source_system: salesforce
source_table: Account
canonical_entity: customer
version: 2.1
last_updated: 2026-02-13

field_mappings:
  - source_field: Id
    canonical_field: external_ids.salesforce
    transform: direct
    data_type: string
    required: true
    description: Salesforce unique identifier

  - source_field: Name
    canonical_field: customer_name
    transform: direct
    data_type: string
    required: true
    description: Account name

  - source_field: Type
    canonical_field: customer_type
    transform: |
      CASE
        WHEN Type = 'Customer' THEN 'business'
        WHEN Type = 'Prospect' THEN 'individual'
        ELSE 'unknown'
      END
    data_type: string
    required: false
    description: Map Salesforce Type to canonical customer_type

  - source_field: AnnualRevenue
    canonical_field: annual_revenue
    transform: CAST(AnnualRevenue AS DECIMAL)
    data_type: decimal
    required: false
    description: Annual revenue in USD

  - source_field: Industry
    canonical_field: industry
    transform: lookup_industry_code(Industry)
    data_type: string
    required: false
    description: Standardized industry code

  - source_field: Email__c
    canonical_field: email
    transform: LOWER(TRIM(Email__c))
    data_type: string
    required: true
    description: Primary email address
    validation:
      - type: email_format
      - type: not_null

  - source_field: BillingStreet
    canonical_field: addresses[0].street_line1
    transform: direct
    data_type: string
    required: false

  - source_field: BillingCity
    canonical_field: addresses[0].city
    transform: direct
    data_type: string
    required: false

  - source_field: BillingState
    canonical_field: addresses[0].state_province
    transform: direct
    data_type: string
    required: false

  - source_field: BillingPostalCode
    canonical_field: addresses[0].postal_code
    transform: direct
    data_type: string
    required: false

  - source_field: BillingCountry
    canonical_field: addresses[0].country_code
    transform: lookup_country_code(BillingCountry)
    data_type: string
    required: false

transformations:
  lookup_industry_code:
    type: function
    description: Map industry name to standard code
    implementation: integrations.lookups.industry_code

  lookup_country_code:
    type: function
    description: Map country name to ISO 3166-1 alpha-2
    implementation: integrations.lookups.country_code
```

**Load YAML to Database:**

```python
import yaml
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session

def load_mappings_from_yaml(yaml_path: str, engine):
    """Load field mappings from YAML to database"""
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    source_system = config['source_system']
    source_table = config['source_table']
    canonical_entity = config['canonical_entity']

    with Session(engine) as session:
        # Delete existing mappings
        session.execute(
            "DELETE FROM field_mappings WHERE source_system = :sys AND source_table = :tbl",
            {'sys': source_system, 'tbl': source_table}
        )

        # Insert new mappings
        for mapping in config['field_mappings']:
            session.execute(
                insert(field_mappings).values(
                    source_system=source_system,
                    source_table=source_table,
                    source_field=mapping['source_field'],
                    canonical_entity=canonical_entity,
                    canonical_field=mapping['canonical_field'],
                    transform_rule=mapping['transform'],
                    data_type=mapping['data_type'],
                    is_required=mapping.get('required', False),
                    notes=mapping.get('description', '')
                )
            )

        session.commit()
        print(f"Loaded {len(config['field_mappings'])} mappings from {yaml_path}")

# Usage
engine = create_engine('postgresql://user:pass@localhost/db')
load_mappings_from_yaml('mappings/salesforce_account.yaml', engine)
```

### Mapping Validation Rules

```python
class MappingValidator:
    def __init__(self, mappings: pd.DataFrame):
        self.mappings = mappings

    def validate_completeness(self, required_canonical_fields: set) -> List[str]:
        """Check if all required canonical fields are mapped"""
        mapped_fields = set(self.mappings['canonical_field'].unique())
        missing = required_canonical_fields - mapped_fields
        return [f"Missing required field: {field}" for field in missing]

    def validate_uniqueness(self) -> List[str]:
        """Check for duplicate mappings (same source field mapped multiple times)"""
        duplicates = self.mappings[
            self.mappings.duplicated(subset=['source_field'], keep=False)
        ]
        errors = []
        for _, row in duplicates.iterrows():
            errors.append(
                f"Duplicate mapping: {row['source_field']} → {row['canonical_field']}"
            )
        return errors

    def validate_types(self) -> List[str]:
        """Check data type compatibility"""
        errors = []
        type_map = {
            'string': ['string', 'text'],
            'integer': ['integer', 'int', 'bigint'],
            'decimal': ['decimal', 'numeric', 'float', 'double'],
            'date': ['date', 'timestamp', 'datetime'],
            'boolean': ['boolean', 'bool']
        }

        for _, row in self.mappings.iterrows():
            # Simplified type validation (real implementation would query source schema)
            pass

        return errors

    def validate_all(self, required_fields: set) -> Dict[str, List[str]]:
        """Run all validation checks"""
        return {
            'completeness': self.validate_completeness(required_fields),
            'uniqueness': self.validate_uniqueness(),
            'types': self.validate_types()
        }

# Usage
required_fields = {
    'external_ids.salesforce',
    'customer_name',
    'email',
    'created_at',
    'updated_at'
}

validator = MappingValidator(mappings)
validation_results = validator.validate_all(required_fields)

if any(validation_results.values()):
    print("Validation errors found:")
    for category, errors in validation_results.items():
        if errors:
            print(f"\n{category.upper()}:")
            for error in errors:
                print(f"  - {error}")
else:
    print("All validations passed ✓")
```

---

## Crosswalk Tables

### What Crosswalks Solve

**Problem:** Same entity exists in multiple systems with different IDs:

```
Customer "Acme Corp":
  - Salesforce ID: 001XXXXXXXX
  - NetSuite ID: 12345
  - HubSpot ID: 67890
  - Canonical ID: c-uuid-1234
```

**Crosswalk table** maintains entity identity mappings across systems.

### Structure

```sql
CREATE TABLE entity_crosswalk (
  crosswalk_id SERIAL PRIMARY KEY,

  entity_type VARCHAR(50) NOT NULL,  -- "customer", "order", "product"
  canonical_id VARCHAR(100) NOT NULL,  -- ID in canonical model

  source_system VARCHAR(100) NOT NULL,  -- "salesforce", "netsuite", "hubspot"
  source_id VARCHAR(255) NOT NULL,  -- ID in source system

  confidence DECIMAL(3,2) DEFAULT 1.00,  -- Match confidence (0.00 to 1.00)
  match_method VARCHAR(50),  -- "exact_id", "fuzzy_name", "email", "manual"

  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),

  UNIQUE(entity_type, source_system, source_id),
  INDEX idx_canonical(entity_type, canonical_id),
  INDEX idx_source(entity_type, source_system, source_id)
);
```

### Example Data

```sql
-- Acme Corp exists in 3 systems
INSERT INTO entity_crosswalk (entity_type, canonical_id, source_system, source_id, confidence, match_method) VALUES
('customer', 'c-uuid-1234', 'salesforce', '001XXXXXXXX', 1.00, 'exact_id'),
('customer', 'c-uuid-1234', 'netsuite', '12345', 1.00, 'exact_id'),
('customer', 'c-uuid-1234', 'hubspot', '67890', 0.95, 'fuzzy_name');

-- Order crosswalk
INSERT INTO entity_crosswalk (entity_type, canonical_id, source_system, source_id, confidence, match_method) VALUES
('order', 'o-uuid-5678', 'shopify', 'order-98765', 1.00, 'exact_id'),
('order', 'o-uuid-5678', 'netsuite', 'SO-12345', 1.00, 'exact_id');
```

### SQL Example: Creating and Querying Crosswalks

**Create Crosswalk Entry:**

```sql
-- Function to get or create canonical ID
CREATE OR REPLACE FUNCTION get_or_create_canonical_id(
  p_entity_type VARCHAR,
  p_source_system VARCHAR,
  p_source_id VARCHAR
) RETURNS VARCHAR AS $$
DECLARE
  v_canonical_id VARCHAR;
BEGIN
  -- Check if crosswalk exists
  SELECT canonical_id INTO v_canonical_id
  FROM entity_crosswalk
  WHERE entity_type = p_entity_type
    AND source_system = p_source_system
    AND source_id = p_source_id
    AND is_active = TRUE;

  -- If not found, create new canonical ID
  IF v_canonical_id IS NULL THEN
    v_canonical_id := p_entity_type || '-' || gen_random_uuid()::TEXT;

    INSERT INTO entity_crosswalk (
      entity_type, canonical_id, source_system, source_id, confidence, match_method
    ) VALUES (
      p_entity_type, v_canonical_id, p_source_system, p_source_id, 1.00, 'exact_id'
    );
  END IF;

  RETURN v_canonical_id;
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT get_or_create_canonical_id('customer', 'salesforce', '001ABC123');
-- Returns: c-uuid-1234 (existing) or creates new
```

**Query: Find All System IDs for Canonical ID:**

```sql
SELECT
  source_system,
  source_id,
  confidence,
  match_method
FROM entity_crosswalk
WHERE entity_type = 'customer'
  AND canonical_id = 'c-uuid-1234'
  AND is_active = TRUE
ORDER BY confidence DESC;

-- Result:
-- source_system | source_id    | confidence | match_method
-- salesforce    | 001XXXXXXXX  | 1.00       | exact_id
-- netsuite      | 12345        | 1.00       | exact_id
-- hubspot       | 67890        | 0.95       | fuzzy_name
```

**Query: Translate ID Between Systems:**

```sql
-- Given Salesforce ID, get NetSuite ID
SELECT ns.source_id AS netsuite_id
FROM entity_crosswalk sf
JOIN entity_crosswalk ns
  ON sf.canonical_id = ns.canonical_id
  AND sf.entity_type = ns.entity_type
WHERE sf.entity_type = 'customer'
  AND sf.source_system = 'salesforce'
  AND sf.source_id = '001XXXXXXXX'
  AND ns.source_system = 'netsuite'
  AND sf.is_active = TRUE
  AND ns.is_active = TRUE;

-- Result: 12345
```

**Query: Find Orphaned IDs (no canonical mapping):**

```sql
-- Customers in Salesforce without canonical ID
SELECT sf.Id AS salesforce_id, sf.Name AS customer_name
FROM salesforce.accounts sf
LEFT JOIN entity_crosswalk xw
  ON xw.entity_type = 'customer'
  AND xw.source_system = 'salesforce'
  AND xw.source_id = sf.Id
  AND xw.is_active = TRUE
WHERE xw.crosswalk_id IS NULL;
```

### Automated Crosswalk Population

```python
import hashlib
from fuzzywuzzy import fuzz
from typing import Optional, List, Tuple

class CrosswalkManager:
    def __init__(self, engine):
        self.engine = engine

    def find_or_create_canonical_id(
        self,
        entity_type: str,
        source_system: str,
        source_id: str,
        entity_data: dict
    ) -> str:
        """Find existing canonical ID or create new one"""

        # 1. Check exact match in crosswalk
        canonical_id = self._find_by_exact_id(entity_type, source_system, source_id)
        if canonical_id:
            return canonical_id

        # 2. Try matching by external ID fields (if entity has them)
        if 'external_ids' in entity_data:
            for system, ext_id in entity_data['external_ids'].items():
                canonical_id = self._find_by_exact_id(entity_type, system, ext_id)
                if canonical_id:
                    # Create new crosswalk entry for current source
                    self._create_crosswalk(
                        entity_type, canonical_id, source_system, source_id,
                        confidence=1.0, match_method='exact_id'
                    )
                    return canonical_id

        # 3. Try fuzzy matching (for customers: by email or name)
        if entity_type == 'customer':
            canonical_id = self._fuzzy_match_customer(entity_data)
            if canonical_id:
                self._create_crosswalk(
                    entity_type, canonical_id, source_system, source_id,
                    confidence=0.95, match_method='fuzzy_match'
                )
                return canonical_id

        # 4. No match found, create new canonical ID
        canonical_id = f"{entity_type}-{self._generate_id()}"
        self._create_crosswalk(
            entity_type, canonical_id, source_system, source_id,
            confidence=1.0, match_method='new_entity'
        )
        return canonical_id

    def _find_by_exact_id(
        self,
        entity_type: str,
        source_system: str,
        source_id: str
    ) -> Optional[str]:
        """Find canonical ID by exact source system ID"""
        query = """
            SELECT canonical_id
            FROM entity_crosswalk
            WHERE entity_type = :entity_type
              AND source_system = :source_system
              AND source_id = :source_id
              AND is_active = TRUE
            LIMIT 1
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {
                    'entity_type': entity_type,
                    'source_system': source_system,
                    'source_id': source_id
                }
            ).fetchone()
            return result[0] if result else None

    def _fuzzy_match_customer(self, customer_data: dict) -> Optional[str]:
        """Fuzzy match customer by email or name"""

        # Try exact email match first
        if 'email' in customer_data and customer_data['email']:
            canonical_id = self._find_by_email(customer_data['email'])
            if canonical_id:
                return canonical_id

        # Try fuzzy name match
        if 'customer_name' in customer_data:
            canonical_id = self._find_by_fuzzy_name(customer_data['customer_name'])
            if canonical_id:
                return canonical_id

        return None

    def _find_by_email(self, email: str) -> Optional[str]:
        """Find customer by exact email match"""
        query = """
            SELECT c.canonical_id
            FROM canonical.customers c
            WHERE LOWER(c.email) = LOWER(:email)
            LIMIT 1
        """
        with self.engine.connect() as conn:
            result = conn.execute(query, {'email': email}).fetchone()
            return result[0] if result else None

    def _find_by_fuzzy_name(self, name: str, threshold: int = 90) -> Optional[str]:
        """Find customer by fuzzy name matching"""
        query = """
            SELECT canonical_id, customer_name
            FROM canonical.customers
            WHERE is_active = TRUE
            LIMIT 1000
        """
        with self.engine.connect() as conn:
            results = conn.execute(query).fetchall()

        best_match = None
        best_score = 0

        for row in results:
            canonical_id, customer_name = row
            score = fuzz.ratio(name.lower(), customer_name.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = canonical_id

        return best_match

    def _create_crosswalk(
        self,
        entity_type: str,
        canonical_id: str,
        source_system: str,
        source_id: str,
        confidence: float,
        match_method: str
    ):
        """Create new crosswalk entry"""
        query = """
            INSERT INTO entity_crosswalk (
                entity_type, canonical_id, source_system, source_id,
                confidence, match_method, created_by
            ) VALUES (
                :entity_type, :canonical_id, :source_system, :source_id,
                :confidence, :match_method, 'auto_matcher'
            )
            ON CONFLICT (entity_type, source_system, source_id)
            DO UPDATE SET
                canonical_id = EXCLUDED.canonical_id,
                confidence = EXCLUDED.confidence,
                match_method = EXCLUDED.match_method,
                updated_at = CURRENT_TIMESTAMP
        """
        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    'entity_type': entity_type,
                    'canonical_id': canonical_id,
                    'source_system': source_system,
                    'source_id': source_id,
                    'confidence': confidence,
                    'match_method': match_method
                }
            )
            conn.commit()

    def _generate_id(self) -> str:
        """Generate UUID for new entity"""
        import uuid
        return str(uuid.uuid4())

# Usage
from sqlalchemy import create_engine

engine = create_engine('postgresql://user:pass@localhost/db')
xwalk = CrosswalkManager(engine)

# New customer from Salesforce
salesforce_customer = {
    'Id': '001NEW123',
    'Name': 'New Company Inc',
    'Email__c': 'contact@newco.com'
}

entity_data = {
    'customer_name': salesforce_customer['Name'],
    'email': salesforce_customer['Email__c']
}

canonical_id = xwalk.find_or_create_canonical_id(
    entity_type='customer',
    source_system='salesforce',
    source_id=salesforce_customer['Id'],
    entity_data=entity_data
)

print(f"Canonical ID: {canonical_id}")
# Canonical ID: customer-abc-123-def-456
```

### Master Data Management (MDM) Integration

**MDM Systems:**
- Informatica MDM
- Talend MDM
- SAP Master Data Governance
- Oracle MDM
- Open-source: Apache Atlas

**Integration Pattern:**

```
Source Systems → Crosswalk Table → MDM Hub → Golden Record
                                      ↓
                              Publish to Consumers
```

**MDM Hub as Source of Truth:**

```sql
-- MDM hub maintains golden record
CREATE TABLE mdm.golden_customers (
  mdm_id VARCHAR(100) PRIMARY KEY,  -- MDM system's ID
  canonical_id VARCHAR(100) UNIQUE,  -- Our canonical ID

  -- Golden record fields (survivorship rules applied)
  customer_name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(50),
  tier VARCHAR(50),
  annual_revenue DECIMAL(15,2),

  -- Data quality
  completeness_score DECIMAL(3,2),
  accuracy_score DECIMAL(3,2),

  -- Metadata
  source_systems TEXT[],  -- ['salesforce', 'netsuite', 'hubspot']
  last_updated TIMESTAMP
);

-- Sync crosswalk from MDM
INSERT INTO entity_crosswalk (entity_type, canonical_id, source_system, source_id, match_method)
SELECT
  'customer',
  g.canonical_id,
  UNNEST(g.source_systems) AS source_system,
  xref.source_id,
  'mdm_golden_record'
FROM mdm.golden_customers g
JOIN mdm.cross_references xref ON g.mdm_id = xref.mdm_id;
```

### Golden Record Resolution Strategies

**Survivorship Rules:** Determine which source value "wins" for each field.

**Common Strategies:**

```python
from typing import List, Dict, Any
from datetime import datetime

class GoldenRecordResolver:
    def __init__(self, source_priority: List[str]):
        """
        source_priority: Order of source system trust
        Example: ['mdm', 'salesforce', 'netsuite', 'hubspot']
        """
        self.source_priority = source_priority

    def resolve_golden_record(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply survivorship rules to create golden record"""
        golden = {}

        fields = set()
        for record in records:
            fields.update(record.keys())

        for field in fields:
            if field in ['source_system', 'source_id']:
                continue

            golden[field] = self._resolve_field(field, records)

        return golden

    def _resolve_field(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Apply field-specific survivorship rule"""

        # Rule 1: Most recent value (for timestamps)
        if field in ['updated_at', 'last_modified', 'last_activity_date']:
            return self._most_recent(field, records)

        # Rule 2: Highest value (for revenue, score)
        if field in ['annual_revenue', 'credit_limit', 'score']:
            return self._highest_value(field, records)

        # Rule 3: Most complete value (fewest nulls)
        if field in ['address', 'description']:
            return self._most_complete(field, records)

        # Rule 4: Longest value (for names)
        if field in ['customer_name', 'description']:
            return self._longest_value(field, records)

        # Rule 5: Source priority (default)
        return self._by_source_priority(field, records)

    def _most_recent(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Return most recent non-null value"""
        valid_records = [r for r in records if r.get(field)]
        if not valid_records:
            return None
        return max(valid_records, key=lambda r: r.get('updated_at', datetime.min))[field]

    def _highest_value(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Return highest non-null numeric value"""
        values = [r.get(field) for r in records if r.get(field) is not None]
        return max(values) if values else None

    def _most_complete(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Return value with most information (longest string, fewest nulls in dict)"""
        values = [r.get(field) for r in records if r.get(field)]
        if not values:
            return None
        if isinstance(values[0], str):
            return max(values, key=len)
        elif isinstance(values[0], dict):
            return max(values, key=lambda d: sum(1 for v in d.values() if v))
        return values[0]

    def _longest_value(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Return longest string value"""
        values = [r.get(field) for r in records if r.get(field) and isinstance(r.get(field), str)]
        return max(values, key=len) if values else None

    def _by_source_priority(self, field: str, records: List[Dict[str, Any]]) -> Any:
        """Return value from highest-priority source"""
        for source in self.source_priority:
            for record in records:
                if record.get('source_system') == source and record.get(field):
                    return record[field]
        return None

# Usage
resolver = GoldenRecordResolver(source_priority=['salesforce', 'netsuite', 'hubspot'])

# Input: Same customer from 3 systems
records = [
    {
        'source_system': 'salesforce',
        'customer_name': 'Acme Corporation',
        'email': 'contact@acme.com',
        'annual_revenue': 5000000,
        'tier': 'enterprise',
        'updated_at': datetime(2026, 2, 10)
    },
    {
        'source_system': 'netsuite',
        'customer_name': 'Acme Corp',
        'email': 'billing@acme.com',
        'annual_revenue': 5200000,  # Higher (more recent)
        'tier': 'premium',
        'updated_at': datetime(2026, 2, 13)
    },
    {
        'source_system': 'hubspot',
        'customer_name': 'Acme Corporation Inc',  # Longest
        'email': 'contact@acme.com',
        'annual_revenue': None,
        'tier': 'standard',
        'updated_at': datetime(2026, 1, 15)
    }
]

golden = resolver.resolve_golden_record(records)
print(golden)
# {
#   'customer_name': 'Acme Corporation Inc',  # Longest
#   'email': 'contact@acme.com',  # Salesforce (highest priority)
#   'annual_revenue': 5200000,  # Highest value
#   'tier': 'enterprise',  # Salesforce (highest priority)
#   'updated_at': datetime(2026, 2, 13)  # Most recent
# }
```

---

## Schema Drift Detection

### Types of Drift

| Drift Type | Description | Example | Impact |
|------------|-------------|---------|--------|
| **Added Column** | New column appears in source | `loyalty_points` added to `customers` | Low (if optional) |
| **Removed Column** | Column disappears from source | `fax_number` removed from `customers` | Medium (data loss) |
| **Type Changed** | Column data type changes | `zip_code` INT → VARCHAR | High (breaks transformations) |
| **Renamed Column** | Column name changes | `email` → `email_address` | High (mapping breaks) |
| **Constraint Changed** | Nullability or default changes | `phone` NOT NULL → NULL | Low to Medium |

### Detection Strategies

**Strategy 1: Schema Snapshots**

```python
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
import json
from datetime import datetime
from typing import Dict, Any

class SchemaSnapshotMonitor:
    def __init__(self, db_url: str, snapshot_table: str = 'schema_snapshots'):
        self.engine = create_engine(db_url)
        self.snapshot_table = snapshot_table
        self._ensure_snapshot_table()

    def _ensure_snapshot_table(self):
        """Create schema snapshots table if not exists"""
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.snapshot_table} (
                snapshot_id SERIAL PRIMARY KEY,
                database_name VARCHAR(100),
                schema_name VARCHAR(100),
                table_name VARCHAR(100),
                schema_hash VARCHAR(64),
                schema_json TEXT,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_table (database_name, schema_name, table_name)
            )
        """
        with self.engine.connect() as conn:
            conn.execute(create_sql)
            conn.commit()

    def capture_schema(self, schema: str, table: str) -> Dict[str, Any]:
        """Capture current schema for a table"""
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table, schema=schema)

        schema_dict = {
            'table': table,
            'schema': schema,
            'columns': [
                {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': str(col['default']) if col['default'] else None
                }
                for col in columns
            ]
        }

        return schema_dict

    def save_snapshot(self, database: str, schema: str, table: str):
        """Save schema snapshot to database"""
        schema_dict = self.capture_schema(schema, table)
        schema_json = json.dumps(schema_dict, sort_keys=True)
        schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()

        insert_sql = f"""
            INSERT INTO {self.snapshot_table}
            (database_name, schema_name, table_name, schema_hash, schema_json)
            VALUES (:database, :schema, :table, :hash, :json)
        """

        with self.engine.connect() as conn:
            conn.execute(
                insert_sql,
                {
                    'database': database,
                    'schema': schema,
                    'table': table,
                    'hash': schema_hash,
                    'json': schema_json
                }
            )
            conn.commit()

    def detect_drift(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Compare current schema with latest snapshot"""
        # Get latest snapshot
        query = f"""
            SELECT schema_json
            FROM {self.snapshot_table}
            WHERE database_name = :database
              AND schema_name = :schema
              AND table_name = :table
            ORDER BY captured_at DESC
            LIMIT 1
        """

        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {'database': database, 'schema': schema, 'table': table}
            ).fetchone()

        if not result:
            return [{'change_type': 'NEW_TABLE', 'message': 'No previous snapshot found'}]

        previous_schema = json.loads(result[0])
        current_schema = self.capture_schema(schema, table)

        return self._compare_schemas(previous_schema, current_schema)

    def _compare_schemas(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compare two schema snapshots and return differences"""
        changes = []

        prev_cols = {col['name']: col for col in previous['columns']}
        curr_cols = {col['name']: col for col in current['columns']}

        # Detect added columns
        for col_name in curr_cols.keys() - prev_cols.keys():
            changes.append({
                'change_type': 'COLUMN_ADDED',
                'column_name': col_name,
                'column_type': curr_cols[col_name]['type'],
                'nullable': curr_cols[col_name]['nullable']
            })

        # Detect removed columns
        for col_name in prev_cols.keys() - curr_cols.keys():
            changes.append({
                'change_type': 'COLUMN_REMOVED',
                'column_name': col_name,
                'previous_type': prev_cols[col_name]['type']
            })

        # Detect type changes
        for col_name in prev_cols.keys() & curr_cols.keys():
            prev_col = prev_cols[col_name]
            curr_col = curr_cols[col_name]

            if prev_col['type'] != curr_col['type']:
                changes.append({
                    'change_type': 'TYPE_CHANGED',
                    'column_name': col_name,
                    'previous_type': prev_col['type'],
                    'current_type': curr_col['type']
                })

            if prev_col['nullable'] != curr_col['nullable']:
                changes.append({
                    'change_type': 'NULLABILITY_CHANGED',
                    'column_name': col_name,
                    'previous_nullable': prev_col['nullable'],
                    'current_nullable': curr_col['nullable']
                })

        return changes

# Usage
import hashlib

monitor = SchemaSnapshotMonitor('postgresql://user:pass@localhost/db')

# Capture initial snapshot
monitor.save_snapshot('production', 'public', 'customers')

# Later, detect drift
changes = monitor.detect_drift('production', 'public', 'customers')

if changes:
    print("Schema drift detected:")
    for change in changes:
        print(f"  - {change['change_type']}: {change}")
else:
    print("No schema drift detected")
```

**Strategy 2: Avro Schema Registry**

```python
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer
import avro.schema

class AvroSchemaMonitor:
    def __init__(self, schema_registry_url: str):
        self.sr_client = SchemaRegistryClient({'url': schema_registry_url})

    def register_schema(self, subject: str, schema_str: str) -> int:
        """Register new schema version"""
        schema = Schema(schema_str, schema_type="AVRO")
        schema_id = self.sr_client.register_schema(subject, schema)
        return schema_id

    def get_latest_schema(self, subject: str) -> Dict:
        """Get latest schema version"""
        schema = self.sr_client.get_latest_version(subject)
        return {
            'schema_id': schema.schema_id,
            'version': schema.version,
            'schema': schema.schema.schema_str
        }

    def check_compatibility(self, subject: str, new_schema_str: str) -> bool:
        """Check if new schema is compatible with registered versions"""
        new_schema = Schema(new_schema_str, schema_type="AVRO")
        is_compatible = self.sr_client.test_compatibility(subject, new_schema)
        return is_compatible

# Usage
monitor = AvroSchemaMonitor('http://schema-registry:8081')

# Define schema
customer_schema = """
{
  "type": "record",
  "name": "Customer",
  "fields": [
    {"name": "customer_id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "created_at", "type": "long", "logicalType": "timestamp-millis"}
  ]
}
"""

# Register schema
schema_id = monitor.register_schema('customers-value', customer_schema)
print(f"Registered schema ID: {schema_id}")

# Later, try registering evolved schema
evolved_schema = """
{
  "type": "record",
  "name": "Customer",
  "fields": [
    {"name": "customer_id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "phone", "type": ["null", "string"], "default": null},
    {"name": "created_at", "type": "long", "logicalType": "timestamp-millis"}
  ]
}
"""

# Check compatibility (should pass: added optional field)
if monitor.check_compatibility('customers-value', evolved_schema):
    print("Schema evolution is compatible")
    new_schema_id = monitor.register_schema('customers-value', evolved_schema)
else:
    print("Schema evolution is NOT compatible")
```

**Strategy 3: dbt Source Freshness**

```yaml
# models/sources.yml
version: 2

sources:
  - name: raw_salesforce
    database: raw
    schema: salesforce
    tables:
      - name: accounts
        description: Salesforce accounts
        columns:
          - name: id
            tests:
              - not_null
              - unique
          - name: name
            tests:
              - not_null
          - name: email__c
            tests:
              - not_null
        loaded_at_field: _fivetran_synced
        freshness:
          warn_after: {count: 12, period: hour}
          error_after: {count: 24, period: hour}

      - name: opportunities
        columns:
          - name: id
          - name: account_id
          - name: amount
        loaded_at_field: _fivetran_synced
```

```bash
# Check source freshness
dbt source freshness

# Output:
# 14:30:00 | Concurrency: 4 threads
# 14:30:01 | 1 of 2 START freshness of raw_salesforce.accounts ..................
# 14:30:01 | 1 of 2 PASS freshness of raw_salesforce.accounts .................... [PASS in 0.23s]
# 14:30:01 | 2 of 2 START freshness of raw_salesforce.opportunities ..............
# 14:30:01 | 2 of 2 WARN freshness of raw_salesforce.opportunities ................ [WARN in 0.19s]
```

### Automated Alerting on Drift

```python
import requests
from typing import List, Dict, Any

class DriftAlerter:
    def __init__(self, slack_webhook_url: str, pagerduty_key: str = None):
        self.slack_webhook = slack_webhook_url
        self.pagerduty_key = pagerduty_key

    def alert_on_drift(self, database: str, schema: str, table: str, changes: List[Dict[str, Any]]):
        """Send alerts for schema drift"""
        if not changes:
            return

        severity = self._assess_severity(changes)
        message = self._format_message(database, schema, table, changes, severity)

        # Always send to Slack
        self._send_slack_alert(message, severity)

        # Send to PagerDuty if critical
        if severity == 'critical' and self.pagerduty_key:
            self._send_pagerduty_alert(message)

    def _assess_severity(self, changes: List[Dict[str, Any]]) -> str:
        """Determine severity based on change types"""
        critical_types = {'COLUMN_REMOVED', 'TYPE_CHANGED'}
        high_types = {'NULLABILITY_CHANGED'}
        low_types = {'COLUMN_ADDED'}

        change_types = {change['change_type'] for change in changes}

        if change_types & critical_types:
            return 'critical'
        elif change_types & high_types:
            return 'high'
        else:
            return 'low'

    def _format_message(
        self,
        database: str,
        schema: str,
        table: str,
        changes: List[Dict[str, Any]],
        severity: str
    ) -> str:
        """Format alert message"""
        emoji_map = {'critical': '🔴', 'high': '🟠', 'low': '🟡'}
        emoji = emoji_map.get(severity, '⚪')

        lines = [
            f"{emoji} **Schema Drift Detected** ({severity.upper()})",
            f"Table: `{database}.{schema}.{table}`",
            f"Changes detected: {len(changes)}",
            ""
        ]

        for change in changes:
            if change['change_type'] == 'COLUMN_ADDED':
                lines.append(
                    f"• ✅ Column added: `{change['column_name']}` ({change['column_type']})"
                )
            elif change['change_type'] == 'COLUMN_REMOVED':
                lines.append(
                    f"• ❌ Column removed: `{change['column_name']}` (was {change['previous_type']})"
                )
            elif change['change_type'] == 'TYPE_CHANGED':
                lines.append(
                    f"• ⚠️  Type changed: `{change['column_name']}` "
                    f"{change['previous_type']} → {change['current_type']}"
                )
            elif change['change_type'] == 'NULLABILITY_CHANGED':
                nullable_str = 'NULL' if change['current_nullable'] else 'NOT NULL'
                lines.append(
                    f"• ℹ️  Nullability changed: `{change['column_name']}` now {nullable_str}"
                )

        return '\n'.join(lines)

    def _send_slack_alert(self, message: str, severity: str):
        """Send alert to Slack"""
        color_map = {'critical': 'danger', 'high': 'warning', 'low': 'good'}
        color = color_map.get(severity, '#808080')

        payload = {
            'attachments': [
                {
                    'color': color,
                    'text': message,
                    'mrkdwn_in': ['text']
                }
            ]
        }

        response = requests.post(self.slack_webhook, json=payload)
        if response.status_code != 200:
            print(f"Failed to send Slack alert: {response.text}")

    def _send_pagerduty_alert(self, message: str):
        """Send alert to PagerDuty"""
        payload = {
            'routing_key': self.pagerduty_key,
            'event_action': 'trigger',
            'payload': {
                'summary': 'Critical schema drift detected',
                'severity': 'critical',
                'source': 'schema_drift_monitor',
                'custom_details': {
                    'message': message
                }
            }
        }

        response = requests.post(
            'https://events.pagerduty.com/v2/enqueue',
            json=payload
        )
        if response.status_code != 202:
            print(f"Failed to send PagerDuty alert: {response.text}")

# Usage
alerter = DriftAlerter(
    slack_webhook_url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
    pagerduty_key='YOUR_PAGERDUTY_INTEGRATION_KEY'
)

# When drift detected
changes = [
    {'change_type': 'COLUMN_REMOVED', 'column_name': 'fax_number', 'previous_type': 'VARCHAR'},
    {'change_type': 'COLUMN_ADDED', 'column_name': 'loyalty_points', 'column_type': 'INTEGER', 'nullable': True}
]

alerter.alert_on_drift('production', 'public', 'customers', changes)
```

### Handling Drift

**Policy 1: Break Pipeline (Fail Fast)**

```python
def handle_drift_fail_fast(changes: List[Dict[str, Any]]) -> bool:
    """Fail pipeline if any drift detected"""
    if changes:
        raise SchemaValidationError(
            f"Schema drift detected: {len(changes)} changes. "
            "Pipeline stopped to prevent data corruption."
        )
    return True
```

**Policy 2: Accommodate Drift (Add Columns)**

```python
def handle_drift_auto_add_columns(
    engine,
    target_table: str,
    changes: List[Dict[str, Any]]
):
    """Automatically add new columns to target table"""
    for change in changes:
        if change['change_type'] == 'COLUMN_ADDED':
            col_name = change['column_name']
            col_type = change['column_type']
            nullable = 'NULL' if change.get('nullable', True) else 'NOT NULL'

            ddl = f"ALTER TABLE {target_table} ADD COLUMN {col_name} {col_type} {nullable};"

            with engine.connect() as conn:
                conn.execute(ddl)
                conn.commit()

            print(f"Added column {col_name} to {target_table}")
```

**Policy 3: Alert and Log (Manual Review)**

```python
def handle_drift_alert_only(changes: List[Dict[str, Any]]):
    """Log drift and alert, but continue processing"""
    if not changes:
        return

    # Log to database
    log_schema_drift(changes)

    # Send alert
    alerter.alert_on_drift('production', 'public', 'customers', changes)

    # Continue pipeline (use previous schema mapping)
    print(f"Schema drift logged. Pipeline continuing with previous schema.")
```

---

## Metadata Management

### Data Catalogs

**Popular Tools:**
- **Atlan:** Modern data catalog with collaboration features
- **DataHub (LinkedIn):** Open-source, metadata-as-code
- **OpenMetadata:** Open-source, end-to-end metadata management
- **Alation:** Enterprise data catalog
- **Collibra:** Data governance platform
- **AWS Glue Data Catalog:** Cloud-native for AWS

**DataHub Example:**

```python
from datahub.emitter.mce_builder import make_dataset_urn, make_tag_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass, TagAssociationClass

# Initialize emitter
emitter = DatahubRestEmitter('http://datahub:8080')

# Define dataset
dataset_urn = make_dataset_urn('snowflake', 'analytics.customers', 'PROD')

# Add metadata
properties = DatasetPropertiesClass(
    description='Canonical customer master data',
    customProperties={
        'owner': 'data-engineering',
        'sla': '99.9%',
        'update_frequency': 'realtime'
    }
)

# Add tags
tags = [
    TagAssociationClass(tag=make_tag_urn('PII')),
    TagAssociationClass(tag=make_tag_urn('CustomerData'))
]

# Emit metadata
emitter.emit_mcp(dataset_urn, aspect=properties)
for tag in tags:
    emitter.emit_mcp(dataset_urn, aspect=tag)
```

### Lineage Tracking

**Track Data Flow Across Integrations:**

```python
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import UpstreamLineageClass, UpstreamClass, DatasetLineageTypeClass

# Define lineage: Salesforce → Canonical → Snowflake
upstream_lineage = UpstreamLineageClass(
    upstreams=[
        UpstreamClass(
            dataset=make_dataset_urn('salesforce', 'Account', 'PROD'),
            type=DatasetLineageTypeClass.TRANSFORMED
        ),
        UpstreamClass(
            dataset=make_dataset_urn('netsuite', 'Customer', 'PROD'),
            type=DatasetLineageTypeClass.TRANSFORMED
        )
    ]
)

# Emit lineage for canonical customer dataset
canonical_urn = make_dataset_urn('canonical', 'customers', 'PROD')
emitter.emit_mcp(canonical_urn, aspect=upstream_lineage)
```

**Query Lineage (via SQL):**

```sql
-- Simple lineage tracking table
CREATE TABLE data_lineage (
  lineage_id SERIAL PRIMARY KEY,
  source_dataset VARCHAR(255),
  source_system VARCHAR(100),
  destination_dataset VARCHAR(255),
  destination_system VARCHAR(100),
  transformation_type VARCHAR(50),  -- 'direct_copy', 'aggregation', 'join', 'canonical_mapping'
  pipeline_name VARCHAR(255),
  last_run TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert lineage metadata
INSERT INTO data_lineage (source_dataset, source_system, destination_dataset, destination_system, transformation_type, pipeline_name) VALUES
('salesforce.Account', 'salesforce', 'canonical.customers', 'canonical_db', 'canonical_mapping', 'salesforce_to_canonical'),
('canonical.customers', 'canonical_db', 'snowflake.analytics.customers', 'snowflake', 'direct_copy', 'canonical_to_snowflake');

-- Query: Find all downstream datasets from Salesforce
WITH RECURSIVE lineage_tree AS (
  -- Base case: Start from Salesforce
  SELECT source_dataset, destination_dataset, transformation_type, 1 AS depth
  FROM data_lineage
  WHERE source_system = 'salesforce'

  UNION ALL

  -- Recursive case: Follow lineage downstream
  SELECT dl.source_dataset, dl.destination_dataset, dl.transformation_type, lt.depth + 1
  FROM data_lineage dl
  JOIN lineage_tree lt ON dl.source_dataset = lt.destination_dataset
  WHERE lt.depth < 10  -- Prevent infinite loops
)
SELECT DISTINCT destination_dataset, MAX(depth) AS hops_from_source
FROM lineage_tree
GROUP BY destination_dataset
ORDER BY hops_from_source;

-- Result:
-- destination_dataset                  | hops_from_source
-- canonical.customers                  | 1
-- snowflake.analytics.customers        | 2
-- snowflake.analytics.customer_metrics | 3
```

### Business Glossary Alignment

**Glossary Structure:**

```sql
CREATE TABLE business_glossary (
  term_id SERIAL PRIMARY KEY,
  term_name VARCHAR(100) UNIQUE NOT NULL,
  definition TEXT NOT NULL,
  domain VARCHAR(50),  -- 'customer', 'product', 'finance'
  synonyms TEXT[],
  related_terms TEXT[],
  owner VARCHAR(100),
  approved_by VARCHAR(100),
  approval_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Map canonical fields to business terms
CREATE TABLE field_to_glossary (
  mapping_id SERIAL PRIMARY KEY,
  canonical_entity VARCHAR(100),
  canonical_field VARCHAR(100),
  term_id INT REFERENCES business_glossary(term_id),
  UNIQUE(canonical_entity, canonical_field, term_id)
);

-- Example entries
INSERT INTO business_glossary (term_name, definition, domain, synonyms) VALUES
('Customer', 'An individual or organization that purchases goods or services', 'customer', ARRAY['Client', 'Account', 'Buyer']),
('Annual Recurring Revenue', 'Yearly value of recurring subscription revenue', 'finance', ARRAY['ARR', 'Annual Revenue']),
('Customer Lifetime Value', 'Predicted net profit from entire future relationship with customer', 'customer', ARRAY['CLV', 'LTV', 'Lifetime Value']);

INSERT INTO field_to_glossary (canonical_entity, canonical_field, term_id) VALUES
('customer', 'canonical_id', 1),
('customer', 'customer_name', 1),
('customer', 'annual_revenue', 2);
```

### Impact Analysis

**Question: "If this source field changes, what breaks?"**

```sql
-- Query: Find all downstream dependencies of a field
WITH impacted_mappings AS (
  SELECT
    fm.canonical_entity,
    fm.canonical_field,
    fm.source_system AS impacted_source,
    fm.source_field AS impacted_field
  FROM field_mappings fm
  WHERE fm.source_system = 'salesforce'
    AND fm.source_table = 'Account'
    AND fm.source_field = 'AnnualRevenue'
),
impacted_datasets AS (
  SELECT DISTINCT
    dl.destination_dataset,
    dl.destination_system,
    dl.pipeline_name
  FROM impacted_mappings im
  JOIN data_lineage dl
    ON dl.source_dataset LIKE '%' || im.canonical_entity || '%'
)
SELECT
  id.destination_dataset AS impacted_dataset,
  id.destination_system AS impacted_system,
  id.pipeline_name AS impacted_pipeline,
  'Salesforce.Account.AnnualRevenue' AS source_field
FROM impacted_datasets id;

-- Result: All downstream datasets that depend on this field
-- impacted_dataset              | impacted_system | impacted_pipeline
-- canonical.customers            | canonical_db    | salesforce_to_canonical
-- snowflake.analytics.customers  | snowflake       | canonical_to_snowflake
-- looker.customer_metrics        | looker          | snowflake_to_looker
```

**Impact Analysis Tool:**

```python
class ImpactAnalyzer:
    def __init__(self, engine):
        self.engine = engine

    def analyze_field_impact(
        self,
        source_system: str,
        source_table: str,
        source_field: str
    ) -> Dict[str, List[str]]:
        """Find all downstream impacts of changing a source field"""

        # 1. Find canonical field mapping
        canonical_mapping = self._find_canonical_mapping(
            source_system, source_table, source_field
        )

        if not canonical_mapping:
            return {'error': 'No canonical mapping found'}

        # 2. Find all consumers of canonical field
        consumers = self._find_canonical_consumers(
            canonical_mapping['canonical_entity'],
            canonical_mapping['canonical_field']
        )

        # 3. Find downstream datasets via lineage
        downstream = self._find_downstream_datasets(
            canonical_mapping['canonical_entity']
        )

        return {
            'source': f"{source_system}.{source_table}.{source_field}",
            'canonical_field': f"{canonical_mapping['canonical_entity']}.{canonical_mapping['canonical_field']}",
            'direct_consumers': consumers,
            'downstream_datasets': downstream,
            'total_impact': len(consumers) + len(downstream)
        }

    def _find_canonical_mapping(self, source_system, source_table, source_field):
        query = """
            SELECT canonical_entity, canonical_field
            FROM field_mappings
            WHERE source_system = :sys
              AND source_table = :tbl
              AND source_field = :fld
            LIMIT 1
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {'sys': source_system, 'tbl': source_table, 'fld': source_field}
            ).fetchone()
            if result:
                return {'canonical_entity': result[0], 'canonical_field': result[1]}
        return None

    def _find_canonical_consumers(self, canonical_entity, canonical_field):
        # Simplified: In practice, query data lineage and metadata catalog
        return [
            'snowflake.analytics.customers',
            'bigquery.reporting.customer_summary',
            'looker.customer_dashboard'
        ]

    def _find_downstream_datasets(self, canonical_entity):
        # Simplified: In practice, recursively query lineage graph
        return [
            'snowflake.analytics.order_facts',
            'bigquery.ml.customer_churn_model',
            'tableau.customer_360_view'
        ]

# Usage
analyzer = ImpactAnalyzer(engine)
impact = analyzer.analyze_field_impact('salesforce', 'Account', 'AnnualRevenue')

print(f"Impact Analysis: {impact['source']}")
print(f"Canonical Field: {impact['canonical_field']}")
print(f"Total Impacted Assets: {impact['total_impact']}")
print("\nDirect Consumers:")
for consumer in impact['direct_consumers']:
    print(f"  - {consumer}")
print("\nDownstream Datasets:")
for dataset in impact['downstream_datasets']:
    print(f"  - {dataset}")
```

### Tagging and Classification for Compliance

**PII/PHI Tagging:**

```sql
CREATE TABLE data_classification (
  classification_id SERIAL PRIMARY KEY,
  dataset_name VARCHAR(255),
  column_name VARCHAR(100),
  classification_level VARCHAR(50),  -- 'public', 'internal', 'confidential', 'restricted'
  sensitivity_tags TEXT[],  -- ['PII', 'PHI', 'PCI', 'Financial']
  retention_policy VARCHAR(100),  -- 'keep_7_years', 'delete_after_30_days'
  encryption_required BOOLEAN DEFAULT FALSE,
  masking_required BOOLEAN DEFAULT FALSE,
  last_reviewed DATE,
  reviewed_by VARCHAR(100),
  UNIQUE(dataset_name, column_name)
);

-- Tag PII fields
INSERT INTO data_classification (dataset_name, column_name, classification_level, sensitivity_tags, encryption_required, masking_required) VALUES
('canonical.customers', 'email', 'confidential', ARRAY['PII'], TRUE, TRUE),
('canonical.customers', 'phone', 'confidential', ARRAY['PII'], TRUE, TRUE),
('canonical.customers', 'ssn', 'restricted', ARRAY['PII', 'PHI'], TRUE, TRUE),
('canonical.customers', 'customer_name', 'internal', ARRAY['PII'], FALSE, FALSE),
('canonical.orders', 'credit_card_number', 'restricted', ARRAY['PCI'], TRUE, TRUE);

-- Query: Find all PII fields in a dataset
SELECT column_name, classification_level, sensitivity_tags
FROM data_classification
WHERE dataset_name = 'canonical.customers'
  AND 'PII' = ANY(sensitivity_tags);
```

**Automated PII Detection:**

```python
import re
from typing import List, Dict

class PIIDetector:
    def __init__(self):
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
        }

        self.column_name_hints = {
            'email': ['email', 'email_address', 'e_mail'],
            'phone': ['phone', 'phone_number', 'mobile', 'telephone'],
            'ssn': ['ssn', 'social_security', 'national_id'],
            'credit_card': ['credit_card', 'cc_number', 'card_number'],
            'name': ['first_name', 'last_name', 'full_name', 'name'],
            'address': ['address', 'street', 'city', 'zip', 'postal_code']
        }

    def detect_pii_columns(
        self,
        table_name: str,
        columns: List[str],
        sample_data: Dict[str, List[str]] = None
    ) -> List[Dict[str, str]]:
        """Detect PII columns by name and data patterns"""
        pii_columns = []

        for column in columns:
            pii_type = self._check_column_name(column)

            if pii_type:
                pii_columns.append({
                    'table': table_name,
                    'column': column,
                    'pii_type': pii_type,
                    'detection_method': 'column_name'
                })
            elif sample_data and column in sample_data:
                # Check data patterns
                pii_type = self._check_data_pattern(sample_data[column])
                if pii_type:
                    pii_columns.append({
                        'table': table_name,
                        'column': column,
                        'pii_type': pii_type,
                        'detection_method': 'data_pattern'
                    })

        return pii_columns

    def _check_column_name(self, column_name: str) -> str:
        """Check if column name suggests PII"""
        column_lower = column_name.lower()
        for pii_type, hints in self.column_name_hints.items():
            if any(hint in column_lower for hint in hints):
                return pii_type
        return None

    def _check_data_pattern(self, values: List[str]) -> str:
        """Check if data matches PII patterns"""
        for pii_type, pattern in self.patterns.items():
            matches = sum(1 for val in values if val and pattern.search(str(val)))
            if matches / len(values) > 0.5:  # 50%+ match rate
                return pii_type
        return None

# Usage
detector = PIIDetector()

columns = ['customer_id', 'email', 'phone', 'annual_revenue', 'created_at']
sample_data = {
    'email': ['alice@example.com', 'bob@test.com', 'charlie@demo.com'],
    'phone': ['555-123-4567', '555-987-6543', '555-111-2222']
}

pii_columns = detector.detect_pii_columns('customers', columns, sample_data)

for col in pii_columns:
    print(f"PII detected: {col['column']} ({col['pii_type']}) via {col['detection_method']}")
```

---

Back to [main skill](../SKILL.md)
