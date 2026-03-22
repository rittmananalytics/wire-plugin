---
name: dbt-development
description: Proactive skill for validating dbt models against coding conventions. Auto-activates when creating, reviewing, or refactoring dbt models in staging, integration, or warehouse layers. Validates naming, SQL structure, field conventions, testing coverage, and documentation. Supports project-specific convention overrides and sqlfluff integration.
---

# dbt Development Skill

## Purpose

This skill automatically activates when working with dbt models to ensure adherence to coding conventions and best practices. It provides validation and recommendations for model structure, naming, SQL style, testing, and documentation.

## When This Skill Activates

### User-Triggered Activation

This skill should activate when users:
- **Create new dbt models:** "Create a staging model for users from Salesforce"
- **Review existing models:** "Review this dbt model for issues"
- **Refactor models:** "Refactor this integration model to follow best practices"
- **Work with .sql files in models/:** Any read/write operations on dbt model files
- **Ask about dbt conventions:** "What are the naming conventions for warehouse models?"
- **Request schema/test files:** "Add tests to this model"

**Keywords to watch for:**
- "dbt model", "staging", "integration", "warehouse", "intermediate"
- "refactor", "review", "validate", "check conventions"
- "stg_", "int_", "_dim", "_fct"
- "schema.yml", "tests", "dbt test"
- "multi-source", "entity resolution", "deduplication", "merge sources"
- "enable source", "disable source", "add source", "remove source"
- "source array", "dbt_project.yml vars"

### Self-Triggered Activation (Proactive)

**Activate BEFORE creating or modifying dbt SQL when:**
- You're about to suggest creating a model from scratch
- You detect .sql files in a models/ directory structure
- User asks to "write SQL" in a dbt project context
- You're reviewing changes in a dbt project
- Working with files that match dbt patterns (stg_, int_, _dim, _fct)

**Example internal triggers:**
- "I'll create a staging model for..." → Activate skill first
- User shows dbt SQL file → Validate against conventions
- "Let me write this transformation..." in dbt context → Check conventions first

## Instructions

### 0. Load Convention Source

**Priority Order (2-tier system):**
1. **Project-specific conventions** (highest priority)
   - Check for `.dbt-conventions.md` in project root
   - Check for `dbt_coding_conventions.md` in project root
   - Check for `docs/dbt_conventions.md` in project

2. **PKM user conventions** (fallback)
   - Conventions: `/Users/olivierdupois/dev/PKM/4. 🛠️ Craft/Tools/dbt/dbt-conventions.md`
   - Testing: `/Users/olivierdupois/dev/PKM/4. 🛠️ Craft/Tools/dbt/dbt-testing.md`

**Note:** The skill's supporting files (`conventions-reference.md`, `testing-reference.md`, `examples/`) are embedded reference documentation that guide validation logic, not convention sources.

**Detection:**
- Use `Glob` to search for convention files in project root
- If found, use `Read` to load project conventions
- If not found, use PKM conventions as fallback
- Note which source is being used in validation output

---

### 1. Identify Model Type and Context

When working with a dbt model, determine:

**Model Type:**
- **Staging** (`stg_`): First transformation layer, selects from sources
- **Integration** (`int_`): Combines multiple sources, enriches entities
- **Intermediate** (`int__<object>__<action>`): Subcomponent of integration
- **Warehouse - Dimension** (`_dim`): Mutable, noun-based entities
- **Warehouse - Fact** (`_fct`): Immutable, verb-based events

**Context Information:**
- File location in directory structure
- Source system (for staging models)
- Entity/object name
- Related models (refs)
- Expected materialization

**How to identify:**
- Check filename prefix/suffix
- Review directory structure (staging/, integration/, warehouse/)
- Read model content for `ref()` and `source()` calls
- Look at model configuration blocks

---

### 2. Validate Naming Conventions

**Check the following:**

**File and Model Naming:**
- ✓ All objects are singular (e.g., `user` not `users`)
- ✓ Staging: `stg_<source>__<object>.sql` (e.g., `stg_salesforce__user.sql`)
- ✓ Integration: `int__<object>.sql` (e.g., `int__user.sql`)
- ✓ Intermediate: `int__<object>__<action>.sql` (e.g., `int__user__unioned.sql`)
  - Actions should be past tense verbs (unioned, grouped, filtered, etc.)
- ✓ Warehouse dimensions: `<object>_dim.sql` or `<warehouse>_<object>_dim.sql`
  - Core warehouse has no prefix (e.g., `user_dim.sql`)
  - Other warehouses prefixed (e.g., `finance_revenue_dim.sql`)
- ✓ Warehouse facts: `<object>_fct.sql` or `<warehouse>_<object>_fct.sql`
  - Same prefix rules as dimensions

**Directory Structure:**
```
models/
├── staging/
│   └── <source_name>/
│       ├── stg_<source>.yml
│       └── stg_<source>__<object>.sql
├── integration/
│   ├── intermediate/
│   │   ├── intermediate.yml
│   │   └── int__<object>__<action>.sql
│   ├── int__<object>.sql
│   └── integration.yml
└── warehouse/
    └── <warehouse_name>/
        ├── <warehouse>.yml
        ├── <object>_dim.sql
        └── <object>_fct.sql
```

**Violations to Flag:**
- Plural object names
- Missing or incorrect prefixes/suffixes
- Non-standard directory structure
- Mismatched filename and directory location

---

### 3. Validate SQL Structure

**Required Structure:**

1. **All refs at top in CTEs:**
```sql
with

s_source_table as (
    select * from {{ ref('source_model') }}
),

s_another_source as (
    select * from {{ ref('another_model') }}
),
```

2. **CTE Naming:**
   - ✓ Prefix with `s_` for CTEs that select from refs/sources
   - ✓ Descriptive names for transformation CTEs (e.g., `filtered_events`, `aggregated_metrics`)
   - ✓ One logical unit of work per CTE

3. **Final CTE Pattern:**
```sql
final as (
    select
        -- fields here
    from s_source_table
    -- joins and where clauses
)

select * from final
```

4. **Configuration Block (if needed):**
```sql
{{
  config(
    materialized = 'table',
    sort = 'id',
    dist = 'id'
  )
}}
```

**Style Requirements:**
- ✓ 4-space indentation (not tabs)
- ✓ Lines no longer than 80 characters
- ✓ Lowercase field and function names
- ✓ Use `as` keyword for aliases
- ✓ Fields before aggregates/window functions
- ✓ Group by column name, not number
- ✓ Prefer `union all` to `union distinct`
- ✓ Explicit joins (`inner join`, `left join`, never just `join`)
- ✓ If joining 2+ tables, always prefix column names with table alias
- ✓ No table alias initialisms (use `customer`, not `c`)
- ✓ Comments for confusing CTEs

**Violations to Flag:**
- `ref()` or `source()` calls outside of top CTEs
- Missing final CTE
- Improper indentation or line length
- Uppercase SQL keywords or functions
- Implicit joins or missing join qualifiers
- Hard-to-understand table aliases

---

### 4. Validate Field Naming and Ordering

**Field Naming Conventions:**

**Primary Keys:**
- ✓ Named `<object>_pk` (e.g., `user_pk`, `transaction_pk`)
- ✓ Generated using `dbt_utils.surrogate_key()`
- ✓ Never look up PKs in separate queries

**Foreign Keys:**
- ✓ Named `<referenced_object>_fk` (e.g., `user_fk`, `transaction_fk`)
- ✓ Generated using `dbt_utils.surrogate_key()`

**Natural Keys:**
- ✓ Source system identifiers: `<descriptive_name>_natural_key`
- ✓ Example: `salesforce_user_natural_key`, `stripe_customer_natural_key`

**Timestamps:**
- ✓ Named `<event>_ts` (e.g., `created_ts`, `updated_ts`, `order_placed_ts`)
- ✓ Always in UTC timezone
- ✓ If different timezone, add suffix: `created_ts_ct`, `created_ts_pt`

**Booleans:**
- ✓ Prefixed with `is_` or `has_` (e.g., `is_active`, `has_subscription`)

**Prices/Revenue:**
- ✓ In decimal currency (e.g., 19.99 for $19.99)
- ✓ If stored in cents, add suffix: `price_in_cents`

**Common Fields:**
- ✓ Prefix with entity name (e.g., `customer_name`, `carrier_name`, not just `name`)

**General Rules:**
- ✓ All names in `snake_case`
- ✓ Use business terminology, not source terminology
- ✓ Avoid SQL reserved words
- ✓ Consistency across models (same field names for same concepts)

**Field Ordering (Staging/Base Models):**
1. Keys (pk, fks, natural keys)
2. Dates and timestamps
3. Attributes (dimensions/slicing fields)
4. Metrics (measures/aggregatable values)
5. Metadata (insert_ts, updated_ts, etc.)

Within each category, sort alphabetically.

**Violations to Flag:**
- Inconsistent naming patterns
- Missing _pk or _fk suffixes
- Timestamps without _ts suffix
- Booleans without is_/has_ prefix
- Reserved words as column names
- Incorrect field ordering

---

### 5. Validate Model Configuration

**Configuration Rules:**

**Warehouse Models:**
- ✓ Always materialized as `table`
- ✓ Consider sort/dist keys for performance

**Other Layers:**
- ✓ Prefer `view` or ephemeral (CTE) materialization
- ✓ Use `table` only if performance requires it

**Configuration Placement:**
- ✓ Model-specific config in the model file (in config() block)
- ✓ Directory-wide config in `dbt_project.yml`

**Example:**
```sql
{{
  config(
    materialized = 'table',
    sort = 'user_pk',
    dist = 'user_pk'
  )
}}
```

**Violations to Flag:**
- Warehouse models not materialized as tables
- Unnecessary table materializations in staging/integration
- Config that should be in dbt_project.yml but is in model

---

### 6. Validate Testing Coverage

**Minimum Testing Requirements:**

**Every Model:**
- ✓ Has a corresponding entry in a `schema.yml` file
- ✓ Primary key has `unique` and `not_null` tests
- ✓ Integration models with multiple sources: use `dbt_utils.unique_combination_of_columns`

**Schema.yml Location:**
- ✓ Every subdirectory should contain a `.yml` file
- ✓ Filename typically matches directory (e.g., `stg_salesforce.yml`, `integration.yml`)

**Example:**
```yaml
version: 2

models:
  - name: stg_salesforce__user
    description: Salesforce user records
    columns:
      - name: user_pk
        description: Unique identifier for user
        tests:
          - unique
          - not_null

      - name: email
        description: User email address
        tests:
          - not_null
```

**Additional Tests:**
- ✓ `relationships` tests for foreign keys
- ✓ `accepted_values` for enums/status fields
- ✓ `not_null_where` for conditional requirements
- ✓ Custom data tests in `tests/` directory for KPI validation

**Violations to Flag:**
- Missing schema.yml file
- Models without test coverage
- Primary keys without unique/not_null tests
- Missing relationships tests on foreign keys

---

### 7. Validate Documentation Coverage

**Documentation Requirements:**

**Staging Models:**
- ✓ 100% documented (all models and columns)
- ✓ Clear descriptions for all fields
- ✓ Business terminology explained

**Warehouse Models:**
- ✓ 100% documented (all models and columns)
- ✓ End-user focused descriptions

**Integration/Intermediate:**
- ✓ Document as needed for clarity
- ✓ Explain any special cases or complex logic

**Doc Blocks:**
- ✓ Use `{% docs %}` blocks for shared documentation
- ✓ Reference doc blocks to maintain consistency
- ✓ Store in `models/docs/` directory

**Example:**
```yaml
version: 2

models:
  - name: user_dim
    description: |
      User dimension containing customer profile information.
      Updated nightly from Salesforce and Stripe sources.
    columns:
      - name: user_pk
        description: "{{ doc('user_pk') }}"
```

**Violations to Flag:**
- Staging/warehouse models without descriptions
- Missing column documentation
- Vague or unhelpful descriptions

---

### 8. Run sqlfluff Validation (if available)

**Check for sqlfluff:**
```bash
which sqlfluff
```

**If available:**
1. Check for `.sqlfluff` config in project root
2. Run: `sqlfluff lint <model_file> --dialect <dialect>`
3. Include sqlfluff violations in validation output
4. Note: sqlfluff enforces many style conventions automatically

**If not available:**
- Note in output: "sqlfluff not detected - recommend installing for automated linting"
- Provide manual validation of style conventions

---

### 9. Output Validation Report

Structure your validation feedback as:

```
## dbt Model Validation Report

**Model:** `<model_name>.sql`
**Type:** <staging/integration/warehouse-dim/warehouse-fct>
**Convention Source:** <project-specific / RA defaults>

### Summary
- ✓ X checks passed
- ⚠️ Y issues found (N critical, M important, P nice-to-have)

### Naming Conventions
[✓/⚠️] **File naming:** <details>
[✓/⚠️] **Field naming:** <details>

### SQL Structure
[✓/⚠️] **CTE structure:** <details>
[✓/⚠️] **Style compliance:** <details>
[✓/⚠️] **Field ordering:** <details>

### Configuration
[✓/⚠️] **Materialization:** <details>
[✓/⚠️] **Performance settings:** <details>

### Testing
[✓/⚠️] **Schema.yml exists:** <details>
[✓/⚠️] **Primary key tests:** <details>
[✓/⚠️] **Foreign key tests:** <details>

### Documentation
[✓/⚠️] **Model description:** <details>
[✓/⚠️] **Column descriptions:** <details>

### sqlfluff
[✓/⚠️/N/A] **Linter results:** <details>

---

## Recommendations

### Critical Issues (must fix)
1. <issue description>
   - **Location:** <file:line or section>
   - **Current:** `<current code>`
   - **Should be:** `<correct pattern>`
   - **Reason:** <why this matters>

### Important Issues (should fix)
<same format>

### Nice-to-have Improvements
<same format>

---

## Examples

See `skills/dbt-development/examples/` for reference implementations:
- `staging-model-example.sql` - Compliant staging model
- `integration-model-example.sql` - Compliant integration model
- `warehouse-model-example.sql` - Compliant warehouse model
- `schema-example.yml` - Proper testing setup
```

---

## 10. Multi-Source Data Warehouse Framework

This section describes the design pattern for building scalable, multi-source data warehouse frameworks. Use this pattern when integrating data from multiple source systems where the same entities (companies, contacts, products, locations) exist across sources with different IDs and attributes.

### Architecture Overview

The multi-source framework uses a three-layer architecture:

```
Sources Layer (stg_*) → Integration Layer (int_*) → Warehouse Layer (wh_*)
```

| Layer | Purpose | Naming | Materialization |
|-------|---------|--------|-----------------|
| **Sources** | Source-specific transformations, column standardization, ID prefixing | `stg_<source>__<object>.sql` | view |
| **Integration** | Cross-source entity resolution, deduplication, merging | `int__<object>.sql` | view or table |
| **Warehouse** | Final dimensional models with surrogate keys | `<object>_dim.sql`, `<object>_fct.sql` | table |

### Configuration-Driven Source Management

A key feature is the ability to **enable or disable data sources** through dbt variables. This allows selective deployment, gradual rollout, and environment-specific configurations.

#### Variable-Based Source Control (dbt_project.yml)

```yaml
# dbt_project.yml
vars:
  # Source enablement arrays - add/remove sources as needed
  crm_warehouse_company_sources: ['hubspot_crm', 'xero_accounting', 'harvest_projects', 'stripe_payments']
  crm_warehouse_contact_sources: ['hubspot_crm', 'mailchimp_email', 'harvest_projects', 'jira_projects']
  finance_warehouse_invoice_sources: ['xero_accounting', 'harvest_projects']
  projects_warehouse_delivery_sources: ['asana_projects', 'jira_projects']
  
  # Per-source configuration
  stg_hubspot_crm_id-prefix: 'hubspot-'
  stg_hubspot_crm_etl: 'fivetran'
  stg_hubspot_crm_schema: 'fivetran_hubspot'
  
  stg_xero_accounting_id-prefix: 'xero-'
  stg_xero_accounting_etl: 'fivetran'
  stg_xero_accounting_schema: 'fivetran_xero'
  
  stg_harvest_projects_id-prefix: 'harvest-'
  stg_harvest_projects_etl: 'stitch'
  stg_harvest_projects_schema: 'stitch_harvest'
  
  # Feature flags
  enable_companies_merge_file: true
  enable_ip_geo_enrichment: false
```

#### Conditional Model Compilation

Models check if their source is enabled before compiling:

```sql
-- models/sources/stg_hubspot_crm/stg_hubspot_crm__company.sql

-- Only compile if hubspot_crm is in the company sources list
{% if var("crm_warehouse_company_sources") %}
{% if 'hubspot_crm' in var("crm_warehouse_company_sources") %}

with source as (
    select * from {{ source('hubspot_crm', 'companies') }}
),

renamed as (
    select
        -- Prefix ID with source identifier to prevent collisions
        concat('{{ var("stg_hubspot_crm_id-prefix") }}', cast(companyid as string)) as company_id,
        
        -- Standardize names for matching
        trim(regexp_replace(
            regexp_replace(properties_name, r'(?i)\s*(Limited|Ltd\.?|Inc\.?|LLC|Corp\.?)$', ''),
            r'\s+', ' '
        )) as company_name,
        
        lower(properties_website) as company_website,
        properties_industry as company_industry,
        properties_phone as company_phone,
        properties_createdate as company_created_ts,
        properties_hs_lastmodifieddate as company_last_modified_ts
    from source
)

select * from renamed

{% endif %}
{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Multi-ETL Support

Support multiple ETL pipelines in the same model:

```sql
-- models/sources/stg_hubspot_crm/stg_hubspot_crm__company.sql

{% if var("crm_warehouse_company_sources") %}
{% if 'hubspot_crm' in var("crm_warehouse_company_sources") %}

{% if var("stg_hubspot_crm_etl") == 'stitch' %}

with source as (
    select * from {{ source('stitch_hubspot_crm', 'companies') }}
),
-- Stitch-specific transformations...

{% elif var("stg_hubspot_crm_etl") == 'fivetran' %}

with source as (
    select * from {{ source('fivetran_hubspot_crm', 'company') }}
),
-- Fivetran-specific transformations...

{% elif var("stg_hubspot_crm_etl") == 'airbyte' %}

with source as (
    select * from {{ source('airbyte_hubspot_crm', 'companies') }}
),
-- Airbyte-specific transformations...

{% endif %}

renamed as (
    -- Common transformation logic
)

select * from renamed

{% endif %}
{% else %} {{ config(enabled=false) }} {% endif %}
```

### Entity Deduplication and Merging

#### Step 1: Source Layer - ID Prefixing

Each source view must prefix all IDs to prevent collisions:

```sql
-- Each source uses its own prefix
concat('{{ var("stg_hubspot_crm_id-prefix") }}', cast(id as string)) as company_id    -- 'hubspot-12345'
concat('{{ var("stg_xero_accounting_id-prefix") }}', cast(id as string)) as company_id  -- 'xero-67890'
concat('{{ var("stg_harvest_projects_id-prefix") }}', cast(id as string)) as company_id -- 'harvest-abc123'
```

#### Step 2: Integration Layer - Pre-Merge Union

Use the `merge_sources` macro to dynamically union enabled sources:

```sql
-- macros/merge_sources.sql

{% macro merge_sources(sources, model_suffix) %}
(
    {% set relations_list = [] %}
    {% for source in sources %}
      {% do relations_list.append(ref("stg_" ~ source ~ model_suffix)) %}
    {% endfor %}

    {{ dbt_utils.union_relations(relations=relations_list) }}
)
{% endmacro %}
```

```sql
-- models/integration/int__company_pre_merged.sql

{% if var('crm_warehouse_company_sources') %}

with companies_pre_merged as (
    {{ merge_sources(sources=var('crm_warehouse_company_sources'), model_suffix='__company') }}
),

-- Collect all source IDs into arrays grouped by company name
all_company_ids as (
    select
        company_name,
        array_agg(distinct company_id ignore nulls) as all_company_ids
    from companies_pre_merged
    where company_name is not null and trim(company_name) != ''
    group by 1
),

-- Deduplicate attributes by taking best/max values
companies_grouped as (
    select
        company_name,
        max(company_website) as company_website,
        max(company_industry) as company_industry,
        max(company_phone) as company_phone,
        min(company_created_ts) as company_created_ts,
        max(company_last_modified_ts) as company_last_modified_ts,
        count(distinct _dbt_source_relation) as source_count
    from companies_pre_merged
    where company_name is not null and trim(company_name) != ''
    group by 1
),

final as (
    select
        g.*,
        a.all_company_ids
    from companies_grouped g
    join all_company_ids a on g.company_name = a.company_name
)

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 3: Manual Merge Resolution (Optional)

For complex merges where name matching isn't sufficient, use a seed file:

```csv
# data/companies_merge_list.csv
company_id,old_company_id
hubspot-12345,xero-67890
hubspot-12345,harvest-abc123
hubspot-99999,xero-88888
```

```sql
-- models/integration/int__company.sql

{% if var('crm_warehouse_company_sources') %}

with companies_pre_merged as (
    select * from {{ ref('int__company_pre_merged') }}
),

{% if var('enable_companies_merge_file', false) %}
-- Apply manual merge mappings
merge_list as (
    select * from {{ ref('companies_merge_list') }}
),

-- Identify companies to be merged
merged_ids as (
    select
        c2.company_name,
        array_concat_agg(
            case 
                when c1.company_name is not null then c1.all_company_ids
                else c2.all_company_ids
            end
        ) as all_company_ids
    from companies_pre_merged c2
    left join merge_list m on m.company_id in unnest(c2.all_company_ids)
    left join companies_pre_merged c1 on m.old_company_id in unnest(c1.all_company_ids)
    group by 1
),

-- Exclude companies that were merged INTO another company
excluded_companies as (
    select distinct c1.company_name
    from merge_list m
    join companies_pre_merged c1 on m.old_company_id in unnest(c1.all_company_ids)
),

final as (
    select
        c.company_name,
        c.company_website,
        c.company_industry,
        c.company_phone,
        c.company_created_ts,
        c.company_last_modified_ts,
        c.source_count,
        coalesce(m.all_company_ids, c.all_company_ids) as all_company_ids
    from companies_pre_merged c
    left join merged_ids m on c.company_name = m.company_name
    where c.company_name not in (select company_name from excluded_companies)
)

{% else %}
-- No merge file, use pre-merged directly
final as (
    select * from companies_pre_merged
)
{% endif %}

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 4: Warehouse Layer - Dimension with Surrogate Key

```sql
-- models/warehouse/core/company_dim.sql

{% if var("crm_warehouse_company_sources") %}

{{
    config(
        materialized='table',
        unique_key='company_pk'
    )
}}

with companies as (
    select * from {{ ref('int__company') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['company_name']) }} as company_pk,
        company_name,
        company_website,
        company_industry,
        company_phone,
        company_created_ts,
        company_last_modified_ts,
        source_count,
        all_company_ids
    from companies
)

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 5: Fact Table Joins Using Source ID Arrays

Join fact tables to dimensions using the array of source IDs:

```sql
-- models/warehouse/finance/invoice_fct.sql

{% if var("finance_warehouse_invoice_sources") %}

{{
    config(
        materialized='table',
        unique_key='invoice_pk'
    )
}}

with invoices as (
    select * from {{ ref('int__invoice') }}
),

companies_dim as (
    select * from {{ ref('company_dim') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['i.invoice_number']) }} as invoice_pk,
        c.company_pk as company_fk,
        
        -- Invoice attributes
        i.invoice_number,
        i.invoice_amount,
        i.invoice_currency,
        i.invoice_status,
        i.invoice_created_ts,
        i.invoice_due_ts,
        i.invoice_paid_ts,
        
        -- Calculated fields
        row_number() over (partition by c.company_pk order by i.invoice_created_ts) as invoice_seq,
        datediff('day', i.invoice_created_ts, i.invoice_paid_ts) as days_to_pay
        
    from invoices i
    -- JOIN using UNNEST to match any source system ID
    left join companies_dim c
        on i.company_id in unnest(c.all_company_ids)
)

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

### Multi-Source Framework Checklist

When implementing the multi-source pattern:

**Configuration**
- [ ] Source arrays defined in `dbt_project.yml` for each entity type
- [ ] ID prefix variables defined for each source
- [ ] ETL type variables defined if supporting multiple pipelines
- [ ] Feature flags for optional behaviors (merge files, enrichment)

**Source Layer**
- [ ] Each source model checks if enabled before compiling
- [ ] All IDs prefixed with unique source identifier
- [ ] Column names standardized across all sources
- [ ] Entity names normalized (trim, remove Ltd/Inc suffixes)
- [ ] Multi-ETL support if applicable

**Integration Layer**
- [ ] `merge_sources` macro used for dynamic unions
- [ ] Pre-merge model collects IDs into arrays
- [ ] Attributes deduplicated using MAX/MIN logic
- [ ] Manual merge file configured if needed
- [ ] Source count tracked for data quality

**Warehouse Layer**
- [ ] Surrogate keys generated from business keys (not source IDs)
- [ ] Source ID arrays preserved in dimension tables
- [ ] Fact tables join using `IN UNNEST()` pattern
- [ ] All conditional config blocks in place

### Directory Structure for Multi-Source Projects

```
models/
├── sources/
│   ├── stg_hubspot_crm/
│   │   ├── _hubspot_crm__sources.yml
│   │   ├── stg_hubspot_crm__company.sql
│   │   ├── stg_hubspot_crm__contact.sql
│   │   └── stg_hubspot_crm__deal.sql
│   ├── stg_xero_accounting/
│   │   ├── _xero_accounting__sources.yml
│   │   ├── stg_xero_accounting__company.sql
│   │   ├── stg_xero_accounting__contact.sql
│   │   └── stg_xero_accounting__invoice.sql
│   └── stg_harvest_projects/
│       ├── _harvest_projects__sources.yml
│       ├── stg_harvest_projects__company.sql
│       ├── stg_harvest_projects__contact.sql
│       └── stg_harvest_projects__invoice.sql
├── integration/
│   ├── _integration__schema.yml
│   ├── int__company_pre_merged.sql
│   ├── int__company.sql
│   ├── int__contact_pre_merged.sql
│   ├── int__contact.sql
│   └── int__invoice.sql
└── warehouse/
    ├── core/
    │   ├── _core__schema.yml
    │   ├── company_dim.sql
    │   └── contact_dim.sql
    └── finance/
        ├── _finance__schema.yml
        ├── invoice_fct.sql
        └── payment_fct.sql

macros/
└── merge_sources.sql

data/
├── companies_merge_list.csv
└── contacts_merge_list.csv
```

### Adding a New Source

To add a new data source:

1. **Add source configuration to `dbt_project.yml`:**
```yaml
vars:
  crm_warehouse_company_sources: ['hubspot_crm', 'xero_accounting', 'NEW_SOURCE']
  stg_new_source_id-prefix: 'newsource-'
  stg_new_source_etl: 'fivetran'
  stg_new_source_schema: 'fivetran_new_source'
```

2. **Create source definition (`_new_source__sources.yml`):**
```yaml
version: 2
sources:
  - name: new_source
    database: "{{ var('stg_new_source_database', target.database) }}"
    schema: "{{ var('stg_new_source_schema') }}"
    tables:
      - name: companies
      - name: contacts
```

3. **Create staging model with conditional compilation:**
```sql
{% if var("crm_warehouse_company_sources") %}
{% if 'new_source' in var("crm_warehouse_company_sources") %}
-- Model SQL here
{% endif %}
{% else %} {{ config(enabled=false) }} {% endif %}
```

4. **Test the source independently before enabling in integration**

### Removing a Source

1. **Remove from source array in `dbt_project.yml`:**
```yaml
vars:
  # 'harvest_projects' removed from list
  crm_warehouse_company_sources: ['hubspot_crm', 'xero_accounting']
```

2. **The source models will automatically disable due to conditional compilation**

3. **Historical source IDs remain in dimension arrays for audit purposes**

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Model not compiling | Source not in enablement array | Add source to `*_sources` variable |
| Duplicate dimension records | Inconsistent name normalization | Ensure identical cleaning logic in all sources |
| Missing fact-dimension joins | Source ID not in array | Verify ID prefix is consistent |
| Orphaned fact records | Company exists in fact but not dim source | Add source to dimension source list |
| Array contains duplicates | Missing DISTINCT in ARRAY_AGG | Add `distinct` keyword |
| Wrong ETL source used | ETL variable incorrect | Check `stg_*_etl` variable value |

---

## 11. Creating New Models

When creating a new dbt model from scratch:

**Step-by-step Process:**

1. **Determine Model Type**
   - Ask user if not clear: staging/integration/warehouse?
   - What source system (for staging)?
   - What entity/object?

2. **Generate File Structure**
   - Correct filename following conventions
   - Proper directory location
   - Configuration block if needed

3. **Build SQL Structure**
   - Refs/sources in CTEs at top
   - Transformation CTEs for logic
   - Final CTE
   - Select from final

4. **Apply Field Conventions**
   - Generate _pk using surrogate_key
   - Name foreign keys with _fk suffix
   - Timestamp fields with _ts suffix
   - Proper field ordering

5. **Create/Update schema.yml**
   - Model description
   - Column descriptions
   - Minimum tests (unique/not_null on pk)

6. **Validate Against Conventions**
   - Run through validation checklist
   - Provide preview before writing

---

## 12. Supporting References

**In This Skill Directory:**
- `conventions-reference.md` - Quick reference for naming, style, structure
- `testing-reference.md` - Test requirements and transformation layers
- `examples/staging-model-example.sql` - Staging model template
- `examples/integration-model-example.sql` - Integration model template
- `examples/warehouse-model-example.sql` - Warehouse model template
- `examples/schema-example.yml` - Testing and documentation example
- `examples/multi-source-staging-example.sql` - Multi-source staging model with conditional compilation
- `examples/multi-source-integration-example.sql` - Entity deduplication and merging
- `examples/multi-source-dimension-example.sql` - Dimension with source ID arrays
- `examples/multi-source-fact-example.sql` - Fact table with UNNEST joins
- `examples/merge-sources-macro.sql` - Dynamic source union macro
- `examples/multi-source-dbt-project-example.yml` - Configuration-driven source management

**Convention Sources (2-tier system):**
- Project-specific: `.dbt-conventions.md` (if exists in project)
- PKM user conventions: `/Users/olivierdupois/dev/PKM/4. 🛠️ Craft/Tools/dbt/dbt-conventions.md` and `dbt-testing.md`

---

## 13. Important Guidelines

**Always Validate When:**
- Creating new dbt models
- Reviewing changes to existing models
- User asks for dbt guidance
- Working with .sql files in models/ directory
- Refactoring or cleaning up code

**Validation Mode (Not Auto-fix):**
- Provide clear, actionable feedback
- Show correct patterns with examples
- Explain WHY conventions matter
- Offer to make specific changes if user approves
- Never silently modify without explaining

**Project Awareness:**
- Always check for project-specific conventions first
- Note which convention source is being used
- Respect project overrides while suggesting RA best practices

**Priority Levels:**
- **Critical:** Breaks functionality, violates core principles, missing required tests
- **Important:** Inconsistent with conventions, maintainability issues, missing documentation
- **Nice-to-have:** Style preferences, minor optimizations, enhanced documentation

---

## 14. Examples of Activation

**Example 1: Creating a Staging Model**
```
User: "Create a staging model for Hubspot contacts"

Actions:
1. Activate dbt Development skill
2. Load convention source (project or RA defaults)
3. Determine: staging model, Hubspot source, contact object
4. Generate: stg_hubspot__contact.sql with proper structure
5. Create schema.yml entry with tests
6. Validate against all conventions
7. Present model for review
```

**Example 2: Reviewing Existing Model**
```
User: "Review this dbt model" [provides file]

Actions:
1. Activate dbt Development skill
2. Load convention source
3. Identify model type from filename/content
4. Run through validation checklist (naming, structure, fields, tests, docs)
5. Check sqlfluff if available
6. Generate validation report with recommendations
```

**Example 3: Refactoring**
```
User: "This integration model needs refactoring to match conventions"

Actions:
1. Activate dbt Development skill
2. Load conventions
3. Analyze current model structure
4. Identify violations
5. Provide detailed refactoring plan with before/after examples
6. Offer to apply changes section by section with user approval
```

**Example 4: Multi-Source Entity Resolution**
```
User: "I need to create a company dimension that combines data from HubSpot, Xero, and Harvest"

Actions:
1. Activate dbt Development skill
2. Load conventions
3. Identify this as a multi-source entity resolution task
4. Review dbt_project.yml for existing source configuration
5. Create/update source arrays in vars section
6. Generate staging models for each source with:
   - Conditional compilation checks
   - ID prefixing using source-specific prefix
   - Standardized column names
7. Create integration models:
   - int__company_pre_merged.sql using merge_sources macro
   - int__company.sql with optional merge list support
8. Create warehouse model:
   - company_dim.sql with surrogate key
   - Preserved all_company_ids array
9. Create merge_sources macro if not exists
10. Create schema.yml with appropriate tests
11. Validate all models against conventions
```

**Example 5: Adding a New Source**
```
User: "We just connected Stripe and need to add it to our company dimension"

Actions:
1. Activate dbt Development skill
2. Load conventions
3. Review existing source configuration in dbt_project.yml
4. Add new source configuration:
   - Add 'stripe_payments' to crm_warehouse_company_sources array
   - Add stg_stripe_payments_id-prefix variable
   - Add stg_stripe_payments_schema variable
5. Create source definition file
6. Create staging model stg_stripe_payments__company.sql with:
   - Conditional compilation check
   - ID prefixing
   - Standardized columns matching other company sources
7. Integration models will automatically include via merge_sources macro
8. Validate new model against conventions
9. Recommend testing new source independently before production
```

---

### Command Execution Tips

When running dbt commands:
- **Use `--quiet` flag** for cleaner output — reduces noise from `dbt run` and `dbt build`
- **Preview selectors first** with `dbt list --select <selector>` before running `dbt build` or `dbt run` — avoids accidentally running more models than intended
- **Use `dbt show --limit N`** instead of writing `SELECT ... LIMIT N` queries — lets you preview model output without running the full model
- **Check `target/run_results.json`** after runs to get per-model timing, status, and row counts — useful for performance analysis and debugging
- **Prefer `dbt build` over separate `dbt run` + `dbt test`** — `build` runs models and their tests together in dependency order, catching failures earlier
- **Use `--warn-error-options`** to promote specific warnings to errors — prevents silent issues from accumulating

---

## 15. Skill Deactivation

Do NOT activate this skill when:
- Working with non-dbt SQL (raw queries, database migrations, etc.)
- User explicitly says "ignore conventions" or "quick prototype"
- Files outside models/ directory (analyses, macros have different conventions)
- User is asking about dbt Cloud, dbt Core installation, or infrastructure (not model development)
