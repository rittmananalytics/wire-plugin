---
description: Generate dbt models
argument-hint: <project-folder>
---

# Generate dbt models

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.agent_v2` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.agent_v2/` in specs refers to the `.agent_v2/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Generate dbt models following layered architecture (staging → integration → warehouse)
argument-hint: <project-folder>
---

# dbt Generate Command

## Purpose

Generate dbt models based on the data model design, following best practices for layered architecture. Creates staging, integration, and warehouse models with appropriate tests, documentation, and naming conventions.

## Prerequisites

**Required Artifacts (must be complete)**:
- `requirements`: Requirements specification
- `data_model`: dbt model design specification

**Optional**:
- `pipeline_design`: Understanding of data sources
- Existing dbt project structure

## Inputs

**From data_model artifact**:
- Source system schemas
- Target dimensional model design
- Transformation logic specifications
- Naming conventions
- Data quality requirements

## Workflow

### Step 1: Read Data Model Design

**Process**:
1. Read `.agent_v2/<project_id>/design/data_model_specification.md`
2. Extract:
   - Source systems and tables
   - Staging layer specifications
   - Integration layer transformations
   - Warehouse layer dimensions and facts
   - Naming conventions
   - Required tests

### Step 1.5: Load Convention Source

**Priority Order (2-tier system):**

1. **Project-specific conventions** (highest priority)
   - Check for `.dbt-conventions.md` in project root
   - Check for `dbt_coding_conventions.md` in project root
   - Check for `docs/dbt_conventions.md` in project

2. **Embedded conventions** (fallback — use the conventions defined in this spec)

**Detection:**
- Use Glob to search for convention files in project root
- If found, read and use project conventions
- If not found, use the embedded conventions below
- Note which source is being used in generated output

### Step 2: Determine dbt Project Location

**Process**:
1. Check if dbt project exists in repository
2. Common locations:
   - `dbt/` or `dbt_project/` at root
   - `transform/` at root
   - Within client folder

**Ask user if location is ambiguous:**
```
Where should I create the dbt models?

Options:
1. Existing dbt project at: [detected path]
2. Create new dbt project
3. Specify custom path
```

For this guide, assume dbt project root is at: `dbt/`

### Step 3: Generate Staging Models

**Purpose**: Clean and standardize raw source data

#### Field Naming Conventions

All generated models MUST follow these naming conventions:

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `<object>_pk` | `user_pk`, `transaction_pk` |
| Foreign Key | `<referenced_object>_fk` | `user_fk`, `account_fk` |
| Natural Key | `<descriptive_name>_natural_key` | `salesforce_user_natural_key` |
| Timestamp | `<event>_ts` | `created_ts`, `updated_ts`, `order_placed_ts` |
| Timestamp (TZ) | `<event>_ts_<tz>` | `created_ts_ct`, `created_ts_pt` |
| Boolean | `is_<state>` or `has_<thing>` | `is_active`, `has_subscription` |
| Price/Revenue | Decimal format | `price` (19.99), `price_in_cents` if integer |
| Common fields | `<entity>_<field>` | `customer_name`, `carrier_name` (not just `name`) |

**General Rules:**
- All names in `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models (same field names for same concepts)
- All objects are SINGULAR (e.g., `user` not `users`)

**Key Generation:**
- Primary keys: Generated using `{{ dbt_utils.surrogate_key(['source_id', 'source_system']) }}`
- Foreign keys: Generated using `{{ dbt_utils.surrogate_key(['referenced_id', 'source_system']) }}`
- Natural keys: Preserved from source as `<source>_<entity>_natural_key`

#### Field Ordering Rules

Fields in all models should follow this ordering:

1. **Keys**: pk, fks, natural keys
2. **Dates and timestamps**: All `_ts` fields
3. **Attributes**: Dimensions/slicing fields (alphabetical within)
4. **Metrics**: Measures/aggregatable values (alphabetical within)
5. **Metadata**: `insert_ts`, `updated_ts`, `source_updated_ts`, etc.

#### SQL Style Rules

All generated SQL MUST follow these style conventions:

| Rule | Requirement |
|------|-------------|
| Indentation | 4 spaces (not tabs) |
| Line length | Max 80 characters |
| Case | Lowercase field names and SQL functions |
| Aliases | Always use `as` keyword |
| Joins | Explicit: `inner join`, `left join` (never just `join`) |
| Table aliases in joins | Use full descriptive names, not initialisms (`customer`, not `c`) |
| Column prefixes | Required when joining 2+ tables |
| CTEs from refs/sources | Prefix with `s_` (e.g., `s_salesforce_contact`) |
| Transformation CTEs | Descriptive names (e.g., `filtered_events`, `aggregated_metrics`) |
| Final CTE | Always name `final` and `select * from final` at end |
| Union | Prefer `union all` to `union distinct` |
| Group by | Use column names, not numbers |
| Comments | Add for confusing CTEs; explain WHY, not WHAT |

**Required SQL Structure:**
```sql
with

s_source_table as (
    select * from {{ ref('source_model') }}
),

s_another_source as (
    select * from {{ ref('another_model') }}
),

-- Comment explaining transformation logic
transformation_cte as (
    select
        field_one,
        field_two
    from s_source_table
),

final as (
    select
        transformation_cte.field_one,
        s_another_source.field_two
    from transformation_cte
    left join s_another_source
        on transformation_cte.id = s_another_source.id
)

select * from final
```

#### Key Principles

1. **Only staging models select from sources** (via `{{ source() }}`)
2. **All other models select from other models** (via `{{ ref() }}`)
3. **All refs go in CTEs at the top** — never inline
4. **Always have a `final` CTE** to select from
5. **One CTE = one logical unit of work**
6. **Prefer creating integration layer** even if just `select *`
7. **Aggregations should happen early**, before joins
8. **Newlines are cheap, brain time is expensive** — optimize for readability

---

**For each source table, create:**

**File**: `dbt/models/staging/<source_system>/stg_<source>__<table>.sql`

**Template**:
```sql
{{
    config(
        materialized='view',
        tags=['staging', '<source_system>']
    )
}}

with

s_<source_system>_<table> as (
    select * from {{ source('<source_system>', '<table_name>') }}
),

final as (
    select
        -- Keys
        {{ dbt_utils.generate_surrogate_key(['<id_column>']) }}
            as <table>_pk,
        <id_column> as <source>_<table>_natural_key,
        <foreign_key_column> as <referenced_table>_fk,

        -- Dates and timestamps
        cast(<date_column> as timestamp) as <event>_ts,

        -- Attributes (renamed for consistency)
        lower(trim(<source_column>)) as <standard_name>,

        -- Metrics
        cast(<numeric_column> as integer) as <metric_name>,

        -- Metadata
        case
            when is_deleted = 'true' then true
            else false
        end as is_deleted,
        _fivetran_synced as source_updated_ts,
        current_timestamp() as dbt_loaded_ts

    from s_<source_system>_<table>
    where is_deleted = 'false'  -- Filter out deleted records
)

select * from final
```

**Also create**: `dbt/models/staging/<source_system>/stg_<source_system>.yml`

```yaml
version: 2

sources:
  - name: <source_system>
    database: "{{ var('source_database') }}"
    schema: "{{ var('source_schema') }}"
    tables:
      - name: <table_name>
        description: "[Description from data model design]"
        columns:
          - name: <column>
            description: "[Description]"
            tests:
              - not_null
              - unique

models:
  - name: stg_<source>__<table>
    description: "Staging model for <table>"
    columns:
      - name: <table>_pk
        description: "Surrogate key"
        tests:
          - not_null
          - unique
```

### Step 4: Generate Integration Models

**Purpose**: Business logic and complex transformations

**Types of integration models:**

#### Intermediate Models (`int__<entity>__<description>.sql`)

For complex multi-step transformations:

**File**: `dbt/models/integration/intermediate/int__<entity>__<description>.sql`

**Example**: `int__student__extended_data.sql`

```sql
{{
    config(
        materialized='ephemeral',
        tags=['integration', 'intermediate']
    )
}}

with student_base as (

    select * from {{ ref('stg_<source_name>__<entity>') }}

),

extended_data_flags as (

    select * from {{ ref('stg_<source_name>__<entity>_detail') }}

),

joined as (

    select
        student_base.*,
        extended_data_flags.is_sen,
        extended_data_flags.is_free_meals,
        extended_data_flags.is_bursary

    from student_base
    left join extended_data_flags
        on student_base.student_pk = extended_data_flags.student_fk

)

select * from joined
```

#### Final Integration Models (`int__<entity>.sql`)

**File**: `dbt/models/integration/int__<entity>.sql`

```sql
{{
    config(
        materialized='view',
        tags=['integration']
    )
}}

with student_extended as (

    select * from {{ ref('int__student__extended_data') }}

),

demographics as (

    select * from {{ ref('int__student__demographics') }}

),

final as (

    select
        student_extended.student_pk,
        student_extended.student_id,
        student_extended.forename,
        student_extended.surname,
        demographics.ethnic_group,
        demographics.is_ethnically_diverse,
        student_extended.is_sen,
        student_extended.is_free_meals,
        -- Derived fields
        case
            when student_extended.is_sen = true
                or student_extended.is_free_meals = true
            then true
            else false
        end as is_access_plus

    from student_extended
    left join demographics
        on student_extended.student_pk = demographics.student_fk

)

select * from final
```

### Step 5: Generate Warehouse Models

**Purpose**: Dimensional model ready for BI consumption

#### Dimension Tables (`<entity>_dim.sql`)

**File**: `dbt/models/warehouse/core/<entity>_dim.sql`

**For SCD Type 1 (current state only)**:
```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'dimension'],
        cluster_by=['<primary_key>']
    )
}}

with base as (

    select * from {{ ref('int__<entity>') }}

),

final as (

    select
        -- Surrogate Key
        <entity>_pk,

        -- Natural Key
        <entity>_id,

        -- Attributes
        <attribute_1>,
        <attribute_2>,

        -- Metadata
        current_timestamp() as dbt_updated_at

    from base

)

select * from final
```

**For SCD Type 2 (historical tracking)**:
```sql
{{
    config(
        materialized='incremental',
        unique_key='<entity>_pk',
        tags=['warehouse', 'dimension', 'scd2'],
        cluster_by=['<entity>_id']
    )
}}

with base as (

    select * from {{ ref('int__<entity>') }}

),

add_temporal_columns as (

    select
        *,
        current_timestamp() as valid_from,
        cast('9999-12-31' as timestamp) as valid_to,
        true as is_current

    from base

)

{% if is_incremental() %}

-- SCD Type 2 logic (detect changes and version records)
...

{% endif %}

select * from add_temporal_columns
```

#### Fact Tables (`<entity>_fct.sql`)

**File**: `dbt/models/warehouse/core/<entity>_fct.sql`

```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'fact'],
        cluster_by=['<date_key>', '<dimension_fk>']
    )
}}

with base as (

    select * from {{ ref('stg_<source>__<table>') }}

),

dimension_joins as (

    select
        base.*,
        dim1.dim1_pk,
        dim2.dim2_pk

    from base
    left join {{ ref('dim1') }} as dim1
        on base.dim1_id = dim1.dim1_id
    left join {{ ref('dim2') }} as dim2
        on base.dim2_id = dim2.dim2_id

),

final as (

    select
        -- Surrogate Key
        {{ dbt_utils.generate_surrogate_key(['<id_columns>']) }} as <fact>_pk,

        -- Foreign Keys
        dim1_pk as dim1_fk,
        dim2_pk as dim2_fk,

        -- Measures
        <measure_1>,
        <measure_2>,

        -- Derived Measures
        case when <condition> then 1 else 0 end as <flag>,

        -- Metadata
        current_timestamp() as dbt_updated_at

    from dimension_joins

)

select * from final
```

#### Aggregate Tables (`<entity>_agg.sql`)

**File**: `dbt/models/warehouse/analytics/<entity>_agg.sql`

```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'aggregate'],
        cluster_by=['<dimension_fk>']
    )
}}

with fact as (

    select * from {{ ref('<entity>_fct') }}

),

aggregated as (

    select
        <dimension_fk>,
        <grouping_column>,

        -- Aggregated Measures
        count(*) as total_count,
        sum(<measure>) as total_<measure>,
        avg(<measure>) as avg_<measure>

    from fact
    group by 1, 2

)

select * from aggregated
```

### Step 5.5: Multi-Source Framework (If Applicable)

When integrating data from **multiple source systems** where the same entities (companies, contacts, products) exist across sources with different IDs and attributes, use this framework pattern.

**When to use:** The data model design identifies multiple sources for the same entity (e.g., companies from HubSpot + Xero + Harvest).

#### Architecture Overview

```
Sources Layer (stg_*) → Integration Layer (int_*) → Warehouse Layer (*_dim/*_fct)
```

| Layer | Purpose | Naming | Materialization |
|-------|---------|--------|-----------------|
| **Sources** | Source-specific transformations, column standardization, ID prefixing | `stg_<source>__<object>.sql` | view |
| **Integration** | Cross-source entity resolution, deduplication, merging | `int__<object>.sql` | view or table |
| **Warehouse** | Final dimensional models with surrogate keys | `<object>_dim.sql`, `<object>_fct.sql` | table |

#### Configuration-Driven Source Management

Add source enablement variables to `dbt_project.yml`:

```yaml
# dbt_project.yml
vars:
  # Source enablement arrays - add/remove sources as needed
  crm_warehouse_company_sources: ['hubspot_crm', 'xero_accounting', 'harvest_projects']
  crm_warehouse_contact_sources: ['hubspot_crm', 'mailchimp_email', 'harvest_projects']
  finance_warehouse_invoice_sources: ['xero_accounting', 'harvest_projects']

  # Per-source configuration
  stg_hubspot_crm_id-prefix: 'hubspot-'
  stg_hubspot_crm_etl: 'fivetran'
  stg_hubspot_crm_schema: 'fivetran_hubspot'

  stg_xero_accounting_id-prefix: 'xero-'
  stg_xero_accounting_etl: 'fivetran'
  stg_xero_accounting_schema: 'fivetran_xero'

  # Feature flags
  enable_companies_merge_file: true
```

#### Step 1: Source Layer — Conditional Compilation with ID Prefixing

Each source model checks if enabled before compiling and prefixes all IDs:

```sql
-- models/sources/stg_hubspot_crm/stg_hubspot_crm__company.sql

{% if var("crm_warehouse_company_sources") %}
{% if 'hubspot_crm' in var("crm_warehouse_company_sources") %}

{% if var("stg_hubspot_crm_etl") == 'fivetran' %}
with source as (
    select * from {{ source('fivetran_hubspot_crm', 'company') }}
    where not _fivetran_deleted
)
{% elif var("stg_hubspot_crm_etl") == 'stitch' %}
with source as (
    select * from {{ source('stitch_hubspot_crm', 'companies') }}
    qualify row_number() over (
        partition by companyid order by _sdc_batched_at desc
    ) = 1
)
{% endif %}

renamed as (
    select
        -- PRIMARY KEY: Prefixed with source identifier
        concat(
            '{{ var("stg_hubspot_crm_id-prefix") }}',
            cast(companyid as string)
        ) as company_id,

        -- BUSINESS KEY: Standardized for matching across sources
        trim(regexp_replace(
            regexp_replace(
                properties_name,
                r'(?i)\s*(Limited|Ltd\.?|Inc\.?|LLC|Corp\.?)$', ''
            ),
            r'\s+', ' '
        )) as company_name,

        -- STANDARDIZED ATTRIBUTES
        lower(trim(properties_website)) as company_website,
        properties_industry as company_industry,
        properties_phone as company_phone,

        -- TIMESTAMPS
        cast(properties_createdate as timestamp) as company_created_ts,
        cast(properties_hs_lastmodifieddate as timestamp)
            as company_last_modified_ts,

        -- SOURCE METADATA
        'hubspot_crm' as source_system,
        current_timestamp() as _loaded_ts

    from source
    where properties_name is not null
)

select * from renamed

{% endif %}
{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 2: Create merge_sources Macro

**File**: `dbt/macros/merge_sources.sql`

```sql
{% macro merge_sources(sources, model_suffix) %}
(
    {% set relations_list = [] %}

    {% for source in sources %}
        {% do relations_list.append(ref("stg_" ~ source ~ model_suffix)) %}
    {% endfor %}

    {{ dbt_utils.union_relations(
        relations=relations_list,
        source_column_name='_dbt_source_relation'
    ) }}
)
{% endmacro %}
```

#### Step 3: Integration Layer — Entity Deduplication and Merging

```sql
-- models/integration/int__company.sql

{% if var('crm_warehouse_company_sources') %}

with companies_unioned as (
    {{ merge_sources(
        sources=var('crm_warehouse_company_sources'),
        model_suffix='__company'
    ) }}
),

-- Collect all source IDs into arrays
all_company_ids as (
    select
        company_name,
        array_agg(distinct company_id ignore nulls) as all_company_ids
    from companies_unioned
    where company_name is not null
      and trim(company_name) != ''
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
        count(distinct source_system) as source_count,
        array_agg(distinct source_system ignore nulls) as source_systems
    from companies_unioned
    where company_name is not null
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

#### Step 4: Warehouse Layer — Dimension with Surrogate Key

```sql
-- models/warehouse/core/company_dim.sql

{% if var("crm_warehouse_company_sources") %}

{{ config(materialized='table', unique_key='company_pk') }}

with companies as (
    select * from {{ ref('int__company') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['company_name']) }}
            as company_pk,
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

```sql
-- Join fact tables to dimensions using the array of source IDs:

with invoices as (
    select * from {{ ref('int__invoice') }}
),

companies_dim as (
    select * from {{ ref('company_dim') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['i.invoice_number']) }}
            as invoice_pk,
        c.company_pk as company_fk,
        i.invoice_number,
        i.invoice_amount,
        i.invoice_status,
        i.invoice_created_ts
    from invoices i
    -- JOIN using UNNEST to match any source system ID
    left join companies_dim c
        on i.company_id in unnest(c.all_company_ids)
)

select * from final
```

#### Multi-Source Directory Structure

```
models/
├── sources/
│   ├── stg_hubspot_crm/
│   │   ├── _hubspot_crm__sources.yml
│   │   ├── stg_hubspot_crm__company.sql
│   │   └── stg_hubspot_crm__contact.sql
│   ├── stg_xero_accounting/
│   │   ├── _xero_accounting__sources.yml
│   │   └── stg_xero_accounting__company.sql
│   └── stg_harvest_projects/
│       ├── _harvest_projects__sources.yml
│       └── stg_harvest_projects__company.sql
├── integration/
│   ├── _integration__schema.yml
│   ├── int__company.sql
│   └── int__contact.sql
└── warehouse/
    ├── core/
    │   ├── _core__schema.yml
    │   └── company_dim.sql
    └── finance/
        ├── _finance__schema.yml
        └── invoice_fct.sql

macros/
└── merge_sources.sql

data/
└── companies_merge_list.csv  (optional manual merge)
```

#### Adding a New Source

1. Add source to enablement array in `dbt_project.yml`
2. Add ID prefix and ETL variables
3. Create source definition `.yml` file
4. Create staging model with conditional compilation
5. Test independently before enabling in integration

#### Removing a Source

1. Remove from source array in `dbt_project.yml`
2. Source models automatically disable via conditional compilation
3. Historical source IDs remain in dimension arrays for audit

#### Multi-Source Framework Checklist

**Configuration:**
- [ ] Source arrays defined in `dbt_project.yml` for each entity type
- [ ] ID prefix variables defined for each source
- [ ] ETL type variables defined if supporting multiple pipelines

**Source Layer:**
- [ ] Each source model checks if enabled before compiling
- [ ] All IDs prefixed with unique source identifier
- [ ] Column names standardized across all sources
- [ ] Entity names normalized (trim, remove Ltd/Inc suffixes)

**Integration Layer:**
- [ ] `merge_sources` macro used for dynamic unions
- [ ] Pre-merge model collects IDs into arrays
- [ ] Attributes deduplicated using MAX/MIN logic
- [ ] Source count tracked for data quality

**Warehouse Layer:**
- [ ] Surrogate keys generated from business keys (not source IDs)
- [ ] Source ID arrays preserved in dimension tables
- [ ] Fact tables join using `IN UNNEST()` pattern
- [ ] All conditional config blocks in place

---

### Step 6: Generate Model Documentation

#### Documentation Coverage Requirements

| Layer | Coverage | Details |
|-------|----------|---------|
| Staging | 100% | All models and columns must be documented |
| Warehouse | 100% | All models and columns must be documented |
| Integration | As needed | Document complex logic and special cases |

**Best Practices:**
- Use `{% docs %}` blocks for shared documentation (store in `models/docs/`)
- Focus on business terminology — explain WHY, not just WHAT
- Include business context for calculated fields
- Reference doc blocks for consistency: `description: "{{ doc('user_pk') }}"`

**Schema.yml Location:**
- Every subdirectory should contain a `.yml` file
- Named after directory: `stg_<source>.yml`, `integration.yml`, `core.yml`

**File**: `dbt/models/warehouse/core/core.yml`

```yaml
version: 2

models:
  - name: <entity>_dim
    description: "Dimension table for <entity>"
    columns:
      - name: <entity>_pk
        description: "Surrogate primary key"
        tests:
          - not_null
          - unique
      - name: <entity>_id
        description: "Natural key"
        tests:
          - not_null

  - name: <entity>_fct
    description: "Fact table for <entity> at <grain> grain"
    columns:
      - name: <entity>_pk
        description: "Surrogate primary key"
        tests:
          - not_null
          - unique
      - name: <dimension>_fk
        description: "Foreign key to <dimension>_dim"
        tests:
          - not_null
          - relationships:
              to: ref('<dimension>_dim')
              field: <dimension>_pk
```

### Step 7: Generate Macros (if needed)

**File**: `dbt/macros/<macro_name>.sql`

**Example**: Calculate derived fields

```sql
{% macro calculate_access_plus(is_sen, is_free_meals) %}
    case
        when {{ is_sen }} = true or {{ is_free_meals }} = true
        then true
        else false
    end
{% endmacro %}
```

### Step 8: Generate dbt_project.yml Config (if new project)

**File**: `dbt/dbt_project.yml`

```yaml
name: '<client>_analytics'
version: '1.0.0'
config-version: 2

profile: '<client>_analytics'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  <client>_analytics:
    staging:
      +materialized: view
      +tags: ['staging']
    integration:
      +materialized: view
      +tags: ['integration']
    warehouse:
      +materialized: table
      +tags: ['warehouse']

vars:
  current_academic_year: '24/25'
  # Add project-specific variables
```

### Step 8.5: sqlfluff Configuration (If Applicable)

**Process:**
1. Check for existing `.sqlfluff` config file in the dbt project root
2. If not present, recommend creating one:

```ini
# .sqlfluff
[sqlfluff]
templater = dbt
dialect = bigquery
max_line_length = 80

[sqlfluff:indentation]
indent_unit = space
tab_space_size = 4

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = lower

[sqlfluff:rules:capitalisation.functions]
capitalisation_policy = lower
```

3. Note that sqlfluff enforces many style conventions automatically (line length, indentation, capitalization, trailing commas, whitespace)
4. If sqlfluff is available, recommend running: `sqlfluff lint models/ --dialect bigquery`

### Step 9: Create Summary Document

**File**: `.agent_v2/<project_id>/dev/dbt_models_summary.md`

```markdown
# dbt Models Summary

**Generated**: [Date]
**Project**: [Client Name]

## Models Created

### Staging Layer
[Table of staging models with descriptions]

### Integration Layer
[Table of integration models with descriptions]

### Warehouse Layer

#### Dimensions
[List of dimension tables]

#### Facts
[List of fact tables]

#### Aggregates
[List of aggregate tables]

## Testing Strategy

- [Count] uniqueness tests
- [Count] not null tests
- [Count] relationship tests
- [Count] custom tests

## Next Steps

1. Run dbt models: `/dp:utils:run-dbt <project_id>`
2. Validate models: `/dp:dbt:validate <project_id>`
3. Review with team: `/dp:dbt:review <project_id>`
```

### Step 10: Update Status

**Process**:
1. Read current status file
2. Update artifacts.dbt section:
   ```yaml
   dbt:
     generate: complete
     validate: not_started
     review: not_started
     models_count: [count]
     tests_count: [count]
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 11: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `dbt`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 12: Confirm and Suggest Next Steps

**Output**:

```
## dbt Models Generated Successfully

**Models Created**: [count]
- Staging: [count]
- Integration: [count]
- Warehouse: [count]

**Tests Configured**: [count]

### Files Created

```
dbt/models/
├── staging/
│   └── <source>/
│       ├── stg_<source>__<table>.sql (x[count])
│       └── stg_<source>.yml
├── integration/
│   ├── intermediate/
│   │   └── int__<entity>__<desc>.sql (x[count])
│   ├── int__<entity>.sql (x[count])
│   └── integration.yml
└── warehouse/
    ├── core/
    │   ├── <entity>_dim.sql (x[count])
    │   ├── <entity>_fct.sql (x[count])
    │   └── core.yml
    └── analytics/
        ├── <entity>_agg.sql (x[count])
        └── analytics.yml
```

### Next Steps

1. **Run the dbt models**:
   /dp:utils:run-dbt <project_id>

   This will execute the models in your dbt Cloud or local environment.

2. **Validate the models**:
   /dp:dbt:validate <project_id>

   This will:
   - Run dbt tests
   - Check data quality
   - Verify row counts
   - Validate relationships

3. **Review with Analytics Engineering**:
   /dp:dbt:review <project_id>

### Quick Links

- View summary: `.agent_v2/<project_id>/dev/dbt_models_summary.md`
- dbt models: `dbt/models/`
- View status: `/dp:status <project_id>`
```

## Reference Examples

### Staging Model Example

```sql
-- stg_salesforce__contact.sql
with

s_salesforce_contact as (
    select * from {{ source('salesforce', 'contact') }}
),

final as (
    select
        -- Keys
        {{ dbt_utils.surrogate_key(['id', "'salesforce'"]) }}
            as contact_pk,
        id as salesforce_contact_natural_key,
        account_id as salesforce_account_natural_key,

        -- Dates and timestamps
        cast(created_date as timestamp) as created_ts,
        cast(last_modified_date as timestamp) as updated_ts,
        cast(last_activity_date as date) as last_activity_date,

        -- Attributes
        lower(trim(email)) as email,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        trim(phone) as phone,
        trim(title) as job_title,
        lower(trim(lead_source)) as lead_source,
        trim(mailing_city) as city,
        trim(mailing_country) as country,

        -- Metrics
        cast(number_of_employees as integer) as employee_count,

        -- Metadata
        case
            when is_deleted = 'true' then true
            else false
        end as is_deleted,
        cast(system_modstamp as timestamp) as source_updated_ts

    from s_salesforce_contact
    where is_deleted = 'false'
)

select * from final
```

### Integration Model Example

```sql
-- int__contact.sql
with

s_salesforce_contact as (
    select * from {{ ref('stg_salesforce__contact') }}
),

s_hubspot_contact as (
    select * from {{ ref('stg_hubspot__contact') }}
),

-- Union contacts from both sources
unioned_contacts as (
    select
        contact_pk,
        'salesforce' as source_system,
        salesforce_contact_natural_key as source_natural_key,
        email, first_name, last_name, phone,
        created_ts, updated_ts, last_activity_date
    from s_salesforce_contact

    union all

    select
        contact_pk,
        'hubspot' as source_system,
        hubspot_contact_natural_key as source_natural_key,
        email, first_name, last_name, phone,
        created_ts, updated_ts, last_activity_date
    from s_hubspot_contact
),

-- Deduplicate by email
deduplicated_contacts as (
    select
        *,
        row_number() over (
            partition by lower(email)
            order by updated_ts desc
        ) as email_rank
    from unioned_contacts
    where email is not null
),

final as (
    select
        contact_pk,
        source_system,
        source_natural_key,
        created_ts,
        updated_ts,
        email,
        first_name,
        last_name,
        phone,
        case
            when email is not null then true
            else false
        end as has_email
    from deduplicated_contacts
    where email_rank = 1
)

select * from final
```

### Warehouse Dimension Example

```sql
-- contact_dim.sql
{{
  config(
    materialized = 'table',
    sort = 'contact_pk',
    dist = 'contact_pk'
  )
}}

with

s_contact as (
    select * from {{ ref('int__contact') }}
),

s_account as (
    select * from {{ ref('int__account') }}
),

final as (
    select
        -- Keys
        s_contact.contact_pk,
        s_account.account_pk as account_fk,

        -- Timestamps
        s_contact.created_ts,
        s_contact.updated_ts,

        -- Contact attributes
        s_contact.email as contact_email,
        concat(s_contact.first_name, ' ', s_contact.last_name)
            as contact_full_name,

        -- Account attributes (denormalized)
        s_account.account_name,
        s_account.account_industry,

        -- Flags
        s_contact.has_email as is_emailable,
        case
            when s_contact.source_system = 'salesforce' then true
            else false
        end as is_salesforce_contact

    from s_contact
    left join s_account
        on s_contact.contact_pk = s_account.contact_pk
)

select * from final
```

### Schema.yml Example

```yaml
version: 2

models:
  - name: stg_salesforce__contact
    description: |
      Salesforce contact records with basic cleaning and standardization.
      Filters out deleted records and normalizes field formats.
    columns:
      - name: contact_pk
        description: |
          Primary key for contact. Generated using surrogate_key from
          Salesforce ID and source system name.
        tests:
          - unique
          - not_null

      - name: salesforce_contact_natural_key
        description: Original Salesforce contact ID
        tests:
          - not_null
          - unique

      - name: email
        description: Contact email address (normalized to lowercase)
        tests:
          - not_null

      - name: lead_source
        description: Original source/channel where contact was acquired
        tests:
          - accepted_values:
              values: ['web', 'referral', 'partner', 'event', 'other']

  - name: contact_dim
    description: |
      Contact dimension for BI consumption. Contains unified contact
      information from all sources.
    columns:
      - name: contact_pk
        description: "{{ doc('contact_pk') }}"
        tests:
          - unique
          - not_null

      - name: account_fk
        description: Foreign key to account dimension
        tests:
          - relationships:
              to: ref('account_dim')
              field: account_pk
```

### Quick Conventions Checklist

Before committing a dbt model:

- [ ] Filename follows naming convention (`stg_`, `int__`, `_dim`, `_fct`)
- [ ] File in correct directory (`staging/`, `integration/`, `warehouse/`)
- [ ] All refs/sources in CTEs at top (prefixed with `s_`)
- [ ] Final CTE exists and is selected from
- [ ] 4-space indentation, < 80 char lines
- [ ] All fields lowercase
- [ ] Primary key: `<object>_pk` with `surrogate_key`
- [ ] Foreign keys: `<object>_fk` with `surrogate_key`
- [ ] Timestamps: `<event>_ts`
- [ ] Booleans: `is_` or `has_` prefix
- [ ] Explicit joins (`inner join`, `left join`)
- [ ] Field ordering correct (keys, dates, attributes, metrics, metadata)
- [ ] Configuration appropriate for layer
- [ ] Schema.yml entry exists
- [ ] Primary key has `unique` + `not_null` tests
- [ ] Model and columns documented (if staging/warehouse)
- [ ] Singular object names throughout

---

## Edge Cases

### No Data Model Design Found

If `data_model` artifact not complete:

```
Error: Data model design not found or incomplete.

Please complete the data model design first:
/dp:data_model:generate <project_id>

The data model design is required to generate dbt models.
```

### Existing dbt Models

If dbt models already exist for some tables:

1. Detect existing models
2. Ask user:
   ```
   Found existing dbt models for:
   - <model_1>
   - <model_2>

   How should I proceed?
   1. Skip existing models (only create new ones)
   2. Overwrite all models
   3. Create with different names (append _v2)
   ```

### dbt Project Not Found

If no dbt project exists:

```
No dbt project found. Would you like me to:

1. Create a new dbt project
2. Specify the dbt project location
3. Cancel (set up dbt project manually first)
```

## Validation Checks (for next step)

The validate command will:
- [ ] Run `dbt compile` (syntax check)
- [ ] Run `dbt test` (all tests pass)
- [ ] Check model dependencies (correct ref() usage)
- [ ] Validate naming conventions
- [ ] Check for circular dependencies

## Output Files

This command creates:
- Multiple `.sql` model files in `dbt/models/`
- Multiple `.yml` documentation files
- `.agent_v2/<project_id>/dev/dbt_models_summary.md`
- Updates `.agent_v2/<project_id>/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
