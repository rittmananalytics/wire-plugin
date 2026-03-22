# dbt Testing Reference

This is embedded reference documentation used by the dbt development skill to guide testing validation. For the authoritative testing conventions, see the PKM or project-specific conventions as configured in the skill's 2-tier system.

---

## Transformation Layers

The dbt transformation process has 4 main layers:

### 1. Sources
- Pointers to raw data
- No transformations
- Defined in `sources.yml` files

### 2. Staging Models (`stg_`)
- First transformation layer
- Basic cleaning: renaming, casting, deduplication, filtering
- Core assumptions about data shape
- **Only layer that selects from sources**
- Always 100% documented

### 3. Integration Models (`int_`)
- Integrates multiple sources into single entities
- Enriches entities with calculated fields
- Examples:
  - Union user data from website + CRM
  - Calculate `last_month_total_visits`
  - Merge conceptual rows into single row

### 4. Warehouse Models (`_dim`, `_fct`)
- Public entities for consumption in BI tools
- Dimensions: Mutable, noun-based (users, products, accounts)
- Facts: Immutable, verb-based (transactions, sessions, events)
- Always 100% documented
- Always materialized as tables

---

## Test Types

### Schema Tests

Defined in `.yml` files alongside models. Validate data conforms to assumptions.

#### Built-in Tests

**`unique`**
- Validates field has unique values across table
- Required for all primary keys

**`not_null`**
- Validates field never contains null
- Required for all primary keys

**`relationships`**
- Validates field values exist in another table
- Use for foreign keys

```yaml
tests:
  - relationships:
      to: ref('users')
      field: user_pk
```

**`accepted_values`**
- Validates field only contains specific values
- Use for enums/status fields

```yaml
tests:
  - accepted_values:
      values: ['visitor', 'trial', 'paying', 'churned']
```

#### dbt-utils Tests

**`not_null_where`**
- Conditional not_null check

```yaml
tests:
  - dbt_utils.not_null_where:
      where: "is_paying = true"
```

**`not_constant`**
- Validates field has more than one distinct value

**`unique_combination_of_columns`**
- Validates uniqueness across multiple columns
- Required for integration models with multiple sources

```yaml
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - user_pk
        - source_system
```

**`expression_is_true`**
- Validates relationship between fields

```yaml
tests:
  - dbt_utils.expression_is_true:
      expression: "end_date >= start_date"
```

---

## Minimum Testing Requirements

### Every Model Must Have:

1. **Entry in schema.yml**
   - Located in same directory as model
   - Typically one yml per source/warehouse

2. **Primary Key Tests**
   ```yaml
   - name: user_pk
     tests:
       - unique
       - not_null
   ```

3. **For Integration Models with Multiple Sources:**
   ```yaml
   tests:
     - dbt_utils.unique_combination_of_columns:
         combination_of_columns:
           - source_a_id
           - source_b_id
           - source_system
   ```

### Recommended Additional Tests:

**Foreign Keys:**
```yaml
- name: account_fk
  tests:
    - relationships:
        to: ref('account_dim')
        field: account_pk
```

**Status/Enum Fields:**
```yaml
- name: subscription_status
  tests:
    - accepted_values:
        values: ['active', 'cancelled', 'past_due', 'trialing']
```

**Timestamps:**
```yaml
- name: created_ts
  tests:
    - not_null
    - dbt_utils.expression_is_true:
        expression: "created_ts <= current_timestamp()"
```

**Conditional Requirements:**
```yaml
- name: payment_method
  tests:
    - dbt_utils.not_null_where:
        where: "subscription_status = 'active'"
```

---

## Test Coverage by Layer

| Layer | Documentation | Primary Key Tests | Other Tests |
|-------|--------------|-------------------|-------------|
| Staging | 100% required | unique + not_null | Basic validation (accepted_values, not_null on critical fields) |
| Integration | As needed | unique + not_null (or unique_combination) | Relationships tests for fks |
| Warehouse | 100% required | unique + not_null | Comprehensive: relationships, business logic validation |

---

## Data Tests

Beyond schema tests, create custom data tests in `tests/` directory:

**Purpose:**
- Validate KPIs continuously
- Check metric performance
- Regression testing for development

**Example: Metric Performance Test**
```sql
-- tests/metric_performance_sessions.sql
{{
    metric_performance(
        source_table = 'website_landing_pages',
        metric = 'sessions',
        base_month_offset = 0,
        comparison_months_window = 2,
        performance_variation = 0.5
    )
}}
```

**Regression Tests:**
- Located in `analysis/regression_tests/`
- Validate that development doesn't break existing results
- Run with `dbt compile`

---

## Test Execution Flow

Standard dbt run sequence:

```bash
# 1. Run staging models
dbt run -m staging.*

# 2. Test staging models
dbt test --schema -m staging.*

# 3. Run integration models
dbt run -m integration.*

# 4. Test integration models
dbt test --schema -m integration.*

# 5. Run warehouse models
dbt run -m warehouse.*

# 6. Test warehouse models
dbt test --schema -m warehouse.*

# 7. Run data tests
dbt test --data
```

**Behavior:**
- If tests fail at any stage, transformation stops
- Prevents errors from propagating to public warehouse layer
- Data in warehouse stays clean but may not be refreshed

---

## Test Severity Levels

Configure test severity in schema.yml:

**Warning:**
```yaml
tests:
  - unique:
      severity: warn
```
- Logs warning but doesn't fail build
- Use for non-critical issues

**Error (default):**
```yaml
tests:
  - unique:
      severity: error
```
- Fails build if test fails
- Use for critical data quality issues

**Best Practice:**
- Primary key tests: Always `error`
- Foreign key tests: Usually `error`
- Optional fields: Can use `warn`
- Nice-to-have validations: Use `warn`

---

## Documentation Coverage

Enforced via [dbt-meta-testing](https://github.com/tnightengale/dbt-meta-testing)

**Requirements:**
- Staging models: 100% (all models and columns)
- Warehouse models: 100% (all models and columns)
- Integration models: As needed for clarity

**Using Doc Blocks:**

Create shared documentation:
```sql
-- models/docs/common_fields.md
{% docs user_pk %}
Unique identifier for user records. Generated using
`dbt_utils.surrogate_key()` from source system ID and source name.
{% enddocs %}
```

Reference in schema.yml:
```yaml
- name: user_pk
  description: "{{ doc('user_pk') }}"
```

---

## Testing Checklist

Before merging dbt code:

### Schema Tests
- [ ] schema.yml exists in model directory
- [ ] All models listed in schema.yml
- [ ] Primary key has `unique` test
- [ ] Primary key has `not_null` test
- [ ] Foreign keys have `relationships` tests
- [ ] Enum/status fields have `accepted_values` tests
- [ ] Conditional requirements use `not_null_where`
- [ ] Integration models use `unique_combination_of_columns` if needed

### Documentation
- [ ] Staging models: 100% documented (model + columns)
- [ ] Warehouse models: 100% documented (model + columns)
- [ ] Integration models: Complex logic documented
- [ ] Doc blocks used for shared field definitions

### Data Tests
- [ ] Critical KPIs have data tests in `tests/`
- [ ] Regression tests updated if logic changed
- [ ] Tests run successfully: `dbt test`

### Test Configuration
- [ ] Appropriate severity levels set (error vs warn)
- [ ] Critical tests set to `error`
- [ ] Nice-to-have validations set to `warn`

---

## Common Testing Patterns

### Pattern 1: Dimension Table
```yaml
models:
  - name: user_dim
    description: User dimension table
    columns:
      - name: user_pk
        description: Primary key
        tests:
          - unique
          - not_null

      - name: email
        description: User email address
        tests:
          - not_null
          - unique  # If email should be unique

      - name: account_fk
        description: Foreign key to account dimension
        tests:
          - relationships:
              to: ref('account_dim')
              field: account_pk

      - name: user_status
        description: Current user status
        tests:
          - accepted_values:
              values: ['active', 'inactive', 'suspended']

      - name: created_ts
        description: User creation timestamp (UTC)
        tests:
          - not_null
```

### Pattern 2: Fact Table
```yaml
models:
  - name: transaction_fct
    description: Transaction fact table
    columns:
      - name: transaction_pk
        description: Primary key
        tests:
          - unique
          - not_null

      - name: user_fk
        description: Foreign key to user dimension
        tests:
          - not_null
          - relationships:
              to: ref('user_dim')
              field: user_pk

      - name: product_fk
        description: Foreign key to product dimension
        tests:
          - relationships:
              to: ref('product_dim')
              field: product_pk

      - name: transaction_ts
        description: Transaction timestamp (UTC)
        tests:
          - not_null

      - name: amount
        description: Transaction amount in USD
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "amount >= 0"
```

### Pattern 3: Integration Model (Multiple Sources)
```yaml
models:
  - name: int__user
    description: Integrated user data from Salesforce and Stripe
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - user_pk
            - source_system
    columns:
      - name: user_pk
        description: User primary key
        tests:
          - not_null

      - name: source_system
        description: Source system for this record
        tests:
          - not_null
          - accepted_values:
              values: ['salesforce', 'stripe']
```

---

## Troubleshooting Failed Tests

### Test Fails: unique
**Cause:** Duplicate values in field
**Investigation:**
```sql
select
    field_name,
    count(*) as count
from {{ ref('model_name') }}
group by field_name
having count(*) > 1
```

### Test Fails: not_null
**Cause:** Null values in field
**Investigation:**
```sql
select *
from {{ ref('model_name') }}
where field_name is null
limit 100
```

### Test Fails: relationships
**Cause:** Foreign key values don't exist in referenced table
**Investigation:**
```sql
select distinct source_table.fk_field
from {{ ref('source_model') }} as source_table
left join {{ ref('target_model') }} as target_table
    on source_table.fk_field = target_table.pk_field
where target_table.pk_field is null
```

### Test Fails: accepted_values
**Cause:** Field contains values not in accepted list
**Investigation:**
```sql
select distinct field_name
from {{ ref('model_name') }}
where field_name not in ('value1', 'value2', 'value3')
```

---

### Unit Testing

For detailed guidance on dbt unit tests (Model-Inputs-Outputs pattern, format selection, BigQuery caveats, and production deployment), see the **dbt-unit-testing** skill:

- `wire/skills/dbt-unit-testing/SKILL.md`

Unit tests are distinct from schema tests and data tests — they validate transformation logic by mocking model inputs and asserting expected outputs, without hitting the database.

**RA Convention**: Unit tests are required for all warehouse-layer models with business logic (case statements, window functions, complex joins). They are recommended but optional for staging models with non-trivial transformations.
