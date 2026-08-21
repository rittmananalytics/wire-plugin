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

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Generate dbt models following layered architecture (staging → integration → warehouse)
argument-hint: <project-folder>
---

# dbt Generate Command

## Purpose

Generate dbt models based on the data model design, following best practices for layered architecture. Creates staging, integration, and warehouse models with appropriate tests, documentation, and naming conventions.

> **Per-layer alternative**: For very large dbt projects where you want to review/commit each layer independently rather than generating all three in one pass, use the per-layer commands instead: `/wire:dbt-staging-generate` → `/wire:dbt-staging-validate` → `/wire:dbt-integration-generate` → `/wire:dbt-integration-validate` → `/wire:dbt-warehouse-generate` → `/wire:dbt-warehouse-validate`, run in that order.

## Prerequisites

**Default** (all project types except `dashboard_first`):

**Required Artifacts (must be complete)**:
- `requirements`: Requirements specification
- `data_model`: dbt model design specification

**Optional**:
- `pipeline_design`: Understanding of data sources
- Existing dbt project structure

**Dashboard-first** (`dashboard_first` project type):

**Required Artifacts (must be complete)**:
- `requirements`: Requirements specification
- `data_model`: dbt model design specification
- `seed_data`: `review: approved` — provides CSV seed files for initial data

**Seed-based generation notes**:
When `project_type` is `dashboard_first`, the dbt project should:
1. Use `ref('seed_name')` in staging models instead of `source('source_name', 'table_name')`
2. Include seed configuration in `dbt_project.yml` (seed paths, schema overrides)
3. Read seed files from `.wire/<project_id>/dev/seed_data/` and include them in the dbt project's `seeds/` directory
4. Generate source definitions that map to seed tables rather than external databases
5. Keep the staging model SQL compatible with later refactoring to real sources (use the `data_refactor` command when real data becomes available)

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
1. Read `.wire/<project_id>/design/data_model_specification.md`
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
| Primary Key | `<entity>_pk`, generated via `dbt_utils.generate_surrogate_key(...)` | `user_pk`, `transaction_pk` |
| Foreign Key | `<referenced_entity>_fk`, generated via `dbt_utils.generate_surrogate_key(...)` | `user_fk`, `account_fk` |
| Natural Key | `<descriptive_name>_natural_key` | `salesforce_user_natural_key` |
| Date | `<event>_dt` | `user_created_dt` |
| Timestamp (UTC) | `<event>_ts` — always assumed UTC unless otherwise indicated | `created_ts`, `updated_ts`, `order_placed_ts` |
| Timestamp (non-UTC) | `<event>_<tz>_ts` — timezone tag inserted before `_ts` | `created_cet_ts`, `created_pt_ts` |
| Boolean | `is_<state>`, `has_<thing>`, or `was_<event>` | `is_active`, `has_subscription`, `was_refunded` |
| Revenue / Money | `<entity>_<measure>_amount` — decimal currency, converted from cents at the staging layer | `user_account_balance_amount` (not `price_in_cents`) |
| Common fields | `<entity>_<field>` | `customer_name`, `carrier_name` (not just `name`) |

**General Rules:**
- All names in `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models (same field names for same concepts)
- All objects are SINGULAR (e.g., `user` not `users`)

**Key Generation:**
- Primary keys: Generated using `{{ dbt_utils.generate_surrogate_key(['source_id', 'source_system']) }}`
- Foreign keys: Generated using `{{ dbt_utils.generate_surrogate_key(['referenced_id', 'source_system']) }}`
- Natural keys: Preserved from source as `<source>_<entity>_natural_key`

**Type Casting:**
- Always use dbt's type-cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`, `{{ type_date() }}` (community macro, no `dbt.` prefix)
- This keeps models portable across warehouses (BigQuery / Snowflake / Databricks / Postgres)

#### Field Ordering Rules

Fields in all models should follow this ordering:

1. **Keys** — pk, fks, natural keys
2. **Attributes** — dimensions, slicing fields, descriptive columns (alphabetical within)
3. **Indexes / ranks** — `row_number()`, rank columns, sequence positions
4. **Metrics** — measures, aggregatable values, `_amount` columns (alphabetical within)
5. **Booleans** — `is_*`, `has_*`, `was_*` flags
6. **Temporal data types** — `_dt`, `_ts` columns last

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

        -- Attributes (renamed for consistency)
        lower(trim(<source_column>)) as <standard_name>,

        -- Metrics
        cast(<numeric_column> as {{ dbt.type_numeric() }}) as <metric_name>,

        -- Booleans
        case
            when is_deleted = 'true' then true
            else false
        end as is_deleted,

        -- Temporal data types
        cast(<date_column> as {{ dbt.type_timestamp() }}) as <event>_ts,
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

#### Intermediate Models (`int_<group>__<entity>__<action>.sql`)

For complex multi-step transformations (action is a past-tense verb, e.g. `unioned`, `deduped`):

**File**: `dbt/models/integration/int_<group>/intermediate/int_<group>__<entity>__<action>.sql`

**Example**: `int_core__student__extended_data.sql`

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

#### Final Integration Models (`int_<group>__<entity>.sql`)

**File**: `dbt/models/integration/int_<group>/int_<group>__<entity>.sql`

```sql
{{
    config(
        materialized='view',
        tags=['integration']
    )
}}

with student_extended as (

    select * from {{ ref('int_core__student__extended_data') }}

),

demographics as (

    select * from {{ ref('int_core__student__demographics') }}

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

#### Dimension Tables (`wh_<group>__<entity>_dim.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_dim.sql`

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

    select * from {{ ref('int_<group>__<entity>') }}

),

final as (

    select
        -- Keys
        <entity>_pk,
        <entity>_natural_key,

        -- Attributes
        <attribute_1>,
        <attribute_2>,

        -- Temporal data types
        current_timestamp() as dbt_updated_ts

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

    select * from {{ ref('int_<group>__<entity>') }}

),

add_temporal_columns as (

    select
        *,
        current_timestamp() as valid_from,
        cast('9999-12-31' as {{ dbt.type_timestamp() }}) as valid_to,
        true as is_current

    from base

)

{% if is_incremental() %}

-- SCD Type 2 logic (detect changes and version records)
...

{% endif %}

select * from add_temporal_columns
```

#### Fact Tables (`wh_<group>__<entity>_fact.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_fact.sql`

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
    left join {{ ref('wh_<group>__dim1_dim') }} as dim1
        on base.dim1_id = dim1.dim1_id
    left join {{ ref('wh_<group>__dim2_dim') }} as dim2
        on base.dim2_id = dim2.dim2_id

),

final as (

    select
        -- Keys
        {{ dbt_utils.generate_surrogate_key(['<id_columns>']) }} as <fact>_pk,
        dim1_pk as dim1_fk,
        dim2_pk as dim2_fk,

        -- Metrics
        <measure_1_amount>,
        <measure_2_amount>,

        -- Booleans
        case when <condition> then true else false end as <flag>,

        -- Temporal data types
        current_timestamp() as dbt_updated_ts

    from dimension_joins

)

select * from final
```

#### Aggregate Tables (`wh_<group>__<entity>_agg.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_agg.sql`

```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'aggregate'],
        cluster_by=['<dimension_fk>']
    )
}}

with fact as (

    select * from {{ ref('wh_<group>__<entity>_fact') }}

),

aggregated as (

    select
        <dimension_fk>,
        <grouping_column>,

        -- Aggregated Measures
        count(*) as total_count,
        sum(<measure>) as total_<measure>_amount,
        avg(<measure>) as avg_<measure>_amount

    from fact
    group by 1, 2

)

select * from aggregated
```

#### Cross-Attribute / Bridge Tables (`wh_<group>__<entity>_xa.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_xa.sql`

For bridge / many-to-many / cross-entity attribute models (e.g. user-to-role, product-to-category), joining two or more dimension surrogate keys with no measures of their own.

### Step 5.5: Multi-Source Framework (If Applicable)

When integrating data from **multiple source systems** where the same entities (companies, contacts, products) exist across sources with different IDs and attributes, use this framework pattern.

**When to use:** The data model design identifies multiple sources for the same entity (e.g., companies from HubSpot + Xero + Harvest).

#### Architecture Overview

```
Sources Layer (stg_*) → Integration Layer (int_<group>__*) → Warehouse Layer (wh_<group>__*_dim/*_fact)
```

| Layer | Purpose | Naming | Materialization |
|-------|---------|--------|-----------------|
| **Sources** | Source-specific transformations, column standardization, ID prefixing | `stg_<source>__<object>.sql` | view |
| **Integration** | Cross-source entity resolution, deduplication, merging | `int_<group>__<object>.sql` | view or table |
| **Warehouse** | Final dimensional models with surrogate keys | `wh_<group>__<object>_dim.sql`, `wh_<group>__<object>_fact.sql` | table |

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
            cast(companyid as {{ dbt.type_string() }})
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
        cast(properties_createdate as {{ dbt.type_timestamp() }})
            as company_created_ts,
        cast(properties_hs_lastmodifieddate as {{ dbt.type_timestamp() }})
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
-- models/integration/int_crm/int_crm__company.sql

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
-- models/warehouse/wh_crm/wh_crm__company_dim.sql

{% if var("crm_warehouse_company_sources") %}

{{ config(materialized='table', unique_key='company_pk') }}

with companies as (
    select * from {{ ref('int_crm__company') }}
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
    select * from {{ ref('int_finance__invoice') }}
),

companies_dim as (
    select * from {{ ref('wh_crm__company_dim') }}
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
│   └── int_crm/
│       ├── _integration__schema.yml
│       ├── int_crm__company.sql
│       └── int_crm__contact.sql
└── warehouse/
    ├── wh_crm/
    │   ├── _wh_crm__schema.yml
    │   └── wh_crm__company_dim.sql
    └── wh_finance/
        ├── _wh_finance__schema.yml
        └── wh_finance__invoice_fact.sql

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
- Named after directory: `stg_<group>.yml`, `int_<group>/integration.yml`, `wh_<group>.yml`

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>.yml`

```yaml
version: 2

models:
  - name: wh_<group>__<entity>_dim
    description: "Dimension table for <entity>"
    columns:
      - name: <entity>_pk
        description: "Surrogate primary key"
        tests:
          - not_null
          - unique
      - name: <entity>_natural_key
        description: "Natural key"
        tests:
          - not_null

  - name: wh_<group>__<entity>_fact
    description: "Fact table for <entity> at <grain> grain"
    columns:
      - name: <entity>_pk
        description: "Surrogate primary key"
        tests:
          - not_null
          - unique
      - name: <dimension>_fk
        description: "Foreign key to wh_<group>__<dimension>_dim"
        tests:
          - not_null
          - relationships:
              to: ref('wh_<group>__<dimension>_dim')
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

**File**: `.wire/<project_id>/dev/dbt_models_summary.md`

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

1. Run dbt models: `/wire:utils-run-dbt <project_id>`
2. Validate models: `/wire:dbt-validate <project_id>`
3. Review with team: `/wire:dbt-review <project_id>`
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

### Step 10.5: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt`
- `artifact_name`: `dbt Models Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_models_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 11: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
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
│   └── <group>/
│       ├── stg_<group>__<entity>.sql (x[count])
│       └── stg_<group>.yml
├── integration/
│   └── int_<group>/
│       ├── intermediate/
│       │   └── int_<group>__<entity>__<action>.sql (x[count])
│       ├── int_<group>__<entity>.sql (x[count])
│       └── integration.yml
└── warehouse/
    └── wh_<group>/
        ├── wh_<group>__<entity>_dim.sql (x[count])
        ├── wh_<group>__<entity>_fact.sql (x[count])
        ├── wh_<group>__<entity>_xa.sql (x[count])
        ├── wh_<group>__<entity>_agg.sql (x[count])
        └── wh_<group>.yml
```

### Next Steps

1. **Run the dbt models**:
   /wire:utils-run-dbt <project_id>

   This will execute the models in your dbt Cloud or local environment.

2. **Validate the models**:
   /wire:dbt-validate <project_id>

   This will:
   - Run dbt tests
   - Check data quality
   - Verify row counts
   - Validate relationships

3. **Review with Analytics Engineering**:
   /wire:dbt-review <project_id>

### Quick Links

- View summary: `.wire/<project_id>/dev/dbt_models_summary.md`
- dbt models: `dbt/models/`
- View status: `/wire:status <project_id>`
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
        {{ dbt_utils.generate_surrogate_key(['id', "'salesforce'"]) }}
            as contact_pk,
        id as salesforce_contact_natural_key,
        account_id as salesforce_account_natural_key,

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
        cast(number_of_employees as {{ dbt.type_numeric() }}) as employee_count,

        -- Booleans
        case
            when is_deleted = 'true' then true
            else false
        end as is_deleted,

        -- Temporal data types
        cast(created_date as {{ dbt.type_timestamp() }}) as created_ts,
        cast(last_modified_date as {{ dbt.type_timestamp() }}) as updated_ts,
        cast(last_activity_date as {{ type_date() }}) as last_activity_dt,
        cast(system_modstamp as {{ dbt.type_timestamp() }}) as source_updated_ts

    from s_salesforce_contact
    where is_deleted = 'false'
)

select * from final
```

### Integration Model Example

```sql
-- int_core__contact.sql
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
-- wh_core__contact_dim.sql
{{
  config(
    materialized = 'table',
    sort = 'contact_pk',
    dist = 'contact_pk'
  )
}}

with

s_contact as (
    select * from {{ ref('int_core__contact') }}
),

s_account as (
    select * from {{ ref('int_core__account') }}
),

final as (
    select
        -- Keys
        s_contact.contact_pk,
        s_account.account_pk as account_fk,

        -- Attributes
        s_contact.email as contact_email,
        concat(s_contact.first_name, ' ', s_contact.last_name)
            as contact_full_name,
        s_account.account_name,
        s_account.account_industry,

        -- Booleans
        s_contact.has_email as is_emailable,
        case
            when s_contact.source_system = 'salesforce' then true
            else false
        end as is_salesforce_contact,

        -- Temporal data types
        s_contact.created_ts,
        s_contact.updated_ts

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
          Primary key for contact. Generated using generate_surrogate_key
          from Salesforce ID and source system name.
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

  - name: wh_core__contact_dim
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
              to: ref('wh_core__account_dim')
              field: account_pk
```

### Quick Conventions Checklist

Before committing a dbt model:

- [ ] Filename follows the `<layer>_<group>__<entity>(_dim|_fact|_agg|_xa).sql` naming pattern (`stg_`, `int_<group>__`, `wh_<group>__`)
- [ ] File in the correct entity-group subfolder (`stg_<group>/`, `int_<group>/`, `warehouse/wh_<group>/`)
- [ ] All refs/sources in CTEs at top (prefixed with `s_`)
- [ ] Final CTE exists and is selected from
- [ ] 4-space indentation, < 80 char lines
- [ ] All fields lowercase
- [ ] Primary key: `<entity>_pk` generated via `dbt_utils.generate_surrogate_key` (not `surrogate_key`)
- [ ] Foreign keys: `<entity>_fk` generated via `dbt_utils.generate_surrogate_key`
- [ ] Dates: `_dt`. Timestamps: `_ts` (UTC) or `_<tz>_ts` (non-UTC, timezone before `_ts`)
- [ ] Booleans: `is_`, `has_`, or `was_` prefix
- [ ] Revenue / money columns: `_amount` suffix
- [ ] Type casts use `{{ dbt.type_*() }}` / `{{ type_date() }}` macros, not raw SQL types
- [ ] Explicit joins (`inner join`, `left join`)
- [ ] Field ordering correct: keys → attributes → indexes/ranks → metrics → booleans → temporal data types
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
/wire:data_model-generate <project_id>

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
- `.wire/<project_id>/dev/dbt_models_summary.md`
- Updates `.wire/<project_id>/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
