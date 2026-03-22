# dbt Conventions Quick Reference

This is embedded reference documentation used by the dbt development skill to guide validation logic. For the authoritative convention source, see the PKM or project-specific conventions as configured in the skill's 2-tier system.

---

## Model Naming

| Layer | Pattern | Example |
|-------|---------|---------|
| Staging | `stg_<source>__<object>.sql` | `stg_salesforce__user.sql` |
| Integration | `int__<object>.sql` | `int__user.sql` |
| Intermediate | `int__<object>__<action>.sql` | `int__user__unioned.sql` |
| Warehouse Dim | `<object>_dim.sql` | `user_dim.sql` |
| Warehouse Fact | `<object>_fct.sql` | `transaction_fct.sql` |

**Rules:**
- All objects are SINGULAR
- Actions are PAST TENSE verbs (unioned, grouped, filtered)
- Non-core warehouses get prefix: `finance_revenue_fct.sql`

---

## Directory Structure

```
models/
├── staging/
│   └── <source>/
│       ├── stg_<source>.yml
│       └── stg_<source>__<object>.sql
├── integration/
│   ├── intermediate/
│   │   ├── intermediate.yml
│   │   └── int__<object>__<action>.sql
│   ├── int__<object>.sql
│   └── integration.yml
└── warehouse/
    └── <warehouse>/
        ├── <warehouse>.yml
        ├── <object>_dim.sql
        └── <object>_fct.sql
```

---

## SQL Structure Template

```sql
{{
  config(
    materialized = 'table',  -- warehouse models only
    sort = 'id',
    dist = 'id'
  )
}}

with

s_source_one as (
    select * from {{ ref('model_one') }}
),

s_source_two as (
    select * from {{ ref('model_two') }}
),

-- Comments for complex CTEs
transformation_logic as (
    select
        field_one,
        field_two,
        case
            when condition then value
            else other_value
        end as calculated_field
    from s_source_one
),

final as (
    select
        transformation_logic.field_one,
        transformation_logic.field_two,
        s_source_two.field_three
    from transformation_logic
    left join s_source_two
        on transformation_logic.id = s_source_two.id
    where transformation_logic.field_one = 'value'
)

select * from final
```

---

## SQL Style Rules

| Rule | Example |
|------|---------|
| Indentation | 4 spaces (not tabs) |
| Line length | Max 80 characters |
| Case | Lowercase fields and functions |
| Aliases | Always use `as` keyword |
| Joins | Explicit: `inner join`, `left join` (never just `join`) |
| Table names in joins | Use full names, not initialisms (`customer`, not `c`) |
| Column prefixes | Required when joining 2+ tables |
| CTEs from refs | Prefix with `s_` |
| Union | Prefer `union all` to `union distinct` |
| Group by | Use column names, not numbers |

---

## Field Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `<object>_pk` | `user_pk`, `transaction_pk` |
| Foreign Key | `<object>_fk` | `user_fk`, `account_fk` |
| Natural Key | `<description>_natural_key` | `salesforce_user_natural_key` |
| Timestamp | `<event>_ts` | `created_ts`, `updated_ts` |
| Timestamp (TZ) | `<event>_ts_<tz>` | `created_ts_ct` |
| Boolean | `is_<state>` or `has_<thing>` | `is_active`, `has_subscription` |
| Price/Revenue | Decimal format | `price` (19.99), `price_in_cents` if integer |
| Common fields | `<entity>_<field>` | `customer_name`, `carrier_name` |

**General Rules:**
- All `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models

---

## Field Ordering (Staging/Base Models)

1. **Keys:** pk, fks, natural keys
2. **Dates and timestamps:** All _ts fields
3. **Attributes:** Dimensions/slicing fields (alphabetical)
4. **Metrics:** Measures/aggregatable values (alphabetical)
5. **Metadata:** insert_ts, updated_ts, etc.

---

## Model Configuration

| Layer | Materialization | Notes |
|-------|----------------|-------|
| Warehouse | `table` (always) | Consider sort/dist keys |
| Integration | `view` or ephemeral | Use `table` only if performance requires |
| Staging | `view` or ephemeral | Keep lightweight |

**Configuration Placement:**
- Model-specific: In model file `{{ config() }}`
- Directory-wide: In `dbt_project.yml`

---

## Testing Requirements

**Every Model Must Have:**
- Entry in `schema.yml` file
- Primary key with `unique` and `not_null` tests

**Additional Tests:**
- `relationships` for foreign keys
- `accepted_values` for enums
- `not_null_where` for conditional requirements
- `dbt_utils.unique_combination_of_columns` for integration models with multiple sources

**Schema.yml Location:**
- Every subdirectory should have a `.yml` file
- Named after directory: `stg_<source>.yml`, `integration.yml`, etc.

---

## Documentation Requirements

| Layer | Coverage | Details |
|-------|----------|---------|
| Staging | 100% | All models and columns |
| Warehouse | 100% | All models and columns |
| Integration | As needed | Document complex logic and special cases |

**Best Practices:**
- Use `{% docs %}` blocks for shared documentation
- Store doc blocks in `models/docs/`
- Focus on business terminology
- Explain WHY, not just WHAT

---

## Key Principles

1. **Only staging models select from sources**
2. **All other models select from other models (via `ref()`)**
3. **All refs go in CTEs at the top**
4. **Always have a `final` CTE to select from**
5. **One CTE = one logical unit of work**
6. **Prefer creating integration layer even if just `select *`**
7. **Aggregations should happen early, before joins**
8. **Newlines are cheap, brain time is expensive** (optimize for readability)

---

## Common Violations

❌ **Don't:**
- Use plural object names (`users` → use `user`)
- Put `ref()` calls outside top CTEs
- Use implicit joins or just `join` (use `inner join`, `left join`)
- Use table alias initialisms (`c` → use `customer`)
- Mix tabs and spaces (use 4 spaces)
- Skip tests on primary keys
- Leave staging/warehouse models undocumented
- Select from sources in non-staging models
- Use `union distinct` without good reason
- Look up PKs in separate queries (generate with `surrogate_key`)

✅ **Do:**
- Use singular names
- All refs in top CTEs
- Explicit join types
- Descriptive table aliases
- Consistent indentation (4 spaces)
- Test all primary keys (unique + not_null)
- Document staging and warehouse 100%
- Respect layer boundaries
- Prefer `union all`
- Generate PKs with `dbt_utils.surrogate_key()`

---

## CTE Patterns

```sql
-- Simple select from ref
s_users as (
    select * from {{ ref('stg_salesforce__user') }}
),

-- Transformation CTE
filtered_active_users as (
    select
        user_pk,
        email,
        created_ts
    from s_users
    where is_active = true
),

-- Aggregation CTE
user_transaction_summary as (
    select
        user_pk,
        count(*) as transaction_count,
        sum(amount) as total_amount
    from s_transactions
    group by user_pk
),

-- Final CTE
final as (
    select
        filtered_active_users.user_pk,
        filtered_active_users.email,
        filtered_active_users.created_ts,
        user_transaction_summary.transaction_count,
        user_transaction_summary.total_amount
    from filtered_active_users
    left join user_transaction_summary
        on filtered_active_users.user_pk =
            user_transaction_summary.user_pk
)

select * from final
```

---

## Generate Primary/Foreign Keys

```sql
-- Generate primary key
{{ dbt_utils.surrogate_key(['source_system_id', 'source_system']) }}
    as user_pk,

-- Generate foreign key (reference to another table's pk)
{{ dbt_utils.surrogate_key(['account_id', 'source_system']) }}
    as account_fk,

-- Natural key from source
source_system_id as salesforce_user_natural_key
```

---

## sqlfluff Integration

If `sqlfluff` is available, it will enforce many of these conventions automatically:
- Line length limits
- Indentation consistency
- Capitalization rules
- Trailing commas
- Whitespace rules

Check for config file: `.sqlfluff` in project root

Run: `sqlfluff lint models/ --dialect <bigquery|snowflake|postgres>`

---

## Quick Checklist

Before committing a dbt model:

- [ ] Filename follows naming convention
- [ ] File in correct directory
- [ ] All refs/sources in CTEs at top
- [ ] Final CTE exists and is selected from
- [ ] 4-space indentation, < 80 char lines
- [ ] All fields lowercase
- [ ] Primary key: `<object>_pk` with surrogate_key
- [ ] Foreign keys: `<object>_fk` with surrogate_key
- [ ] Timestamps: `<event>_ts`
- [ ] Booleans: `is_` or `has_` prefix
- [ ] Explicit joins (inner/left)
- [ ] Field ordering correct (keys, dates, attributes, metrics, metadata)
- [ ] Configuration appropriate for layer
- [ ] Schema.yml entry exists
- [ ] Primary key has unique + not_null tests
- [ ] Model and columns documented (if staging/warehouse)
- [ ] No SQL reserved words as column names
- [ ] Singular object names throughout
