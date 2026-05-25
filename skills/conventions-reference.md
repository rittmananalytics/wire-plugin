# dbt Conventions Quick Reference

This is embedded reference documentation used by the dbt development skill to guide validation logic. For the authoritative convention source, see the PKM or project-specific conventions as configured in the skill's 2-tier system.

---

## Model Naming

Models are organised into **entity groups** (`core`, `entity`, or domain-specific like `finance`, `risk`). The general pattern is `<layer>_<group>__<entity>.sql` with a double underscore separating group from entity.

| Layer | Pattern | Example |
|-------|---------|---------|
| Staging | `stg_<group>__<table>.sql` | `stg_core__users.sql`, `stg_entity__entity_a.sql` |
| Integration | `int_<group>__<entity>.sql` | `int_core__users.sql`, `int_core__geographies.sql` |
| Warehouse Dimension | `wh_<group>__<entity>_dim.sql` | `wh_core__user_dim.sql`, `wh_core__country_dim.sql` |
| Warehouse Fact | `wh_<group>__<entity>_fact.sql` | `wh_entity_group__entity_name_b_fact.sql` |
| Warehouse Cross-Attribute | `wh_<group>__<entity>_xa.sql` | `wh_entity_group__entity_name_d_xa.sql` |

**Rules:**
- All entity names are singular
- Only **staging** models select from sources (`{{ source(...) }}`)
- Integration and warehouse models select from lower layers via `{{ ref(...) }}`
- A warehouse model may select directly from staging if an integration model isn't required

---

## Directory Structure

```
models/
│
├── schema.yml                   # Schema YAML — auto-generated, do not hand-edit
├── field_descriptions.md         # Centralised dbt doc blocks
│
├── warehouse/
│   ├── wh_core/
│   │   ├── wh_core__user_dim.sql
│   │   └── wh_core__country_dim.sql
│   └── wh_entity_group/
│       ├── wh_entity_group__entity_name_a_dim.sql
│       ├── wh_entity_group__entity_name_b_fact.sql
│       └── wh_entity_group__entity_name_d_xa.sql
│
├── integration/
│   ├── int_core/
│   │   ├── int_core__users.sql
│   │   └── int_core__geographies.sql
│   └── int_entity_group/
│       └── int_entity_group__entity_name.sql
│
└── staging/
    ├── stg_core/
    │   ├── _sources.yml
    │   ├── stg_core__users.sql
    │   └── stg_core__geographies.sql
    └── stg_entity/
        ├── _sources.yml
        ├── stg_entity__entity_a.sql
        └── stg_entity__entity_b.sql
```

---

## SQL Structure Template — canonical staging model

```sql
{{
  config(
    description = 'A description of the model to help developers'
    )
}}

with s_users as (

    select * from {{ source('back_office', 'user_accounts') }}

),

rename_and_cast as (

    select

        {# keys #}
        lower(cast(id as {{ dbt.type_string() }} )) as user_natural_key,
        {# attributes #}
        lower(cast(name as {{ dbt.type_string() }} )) as user_name,
        {# metrics #}
        cast(account_balance as {{ dbt.type_numeric() }} ) as user_account_balance_amount,
        {# booleans #}
        cast(status as {{ dbt.type_boolean() }} ) as user_status,
        {# temporal data types #}
        cast(created_date as {{ type_date() }} ) as user_created_dt,
        cast(update_at as {{ dbt.type_timestamp() }} ) as user_update_ts,

    from s_users

),

final as (

    select * from rename_and_cast

)

select * from final
```

**Pattern notes:**
- First CTE selects from source / ref, prefixed `s_`
- Second CTE handles renaming and casting in one place (`rename_and_cast`)
- `{# keys #}`, `{# attributes #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal data types #}` comments mark the column-ordering groups
- Final CTE is always called `final` — `select * from final` at the bottom for debuggability
- Blank lines around CTE bodies improve readability — don't optimise for fewer lines

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
| Primary Key | `<entity>_pk` | `user_pk`, `subscription_pk` |
| Foreign Key | `<entity>_fk` | `user_fk`, `subscription_fk` |
| Natural Key | `<entity>_natural_key` | `user_natural_key`, `subscription_natural_key` |
| Date | `<event>_dt` | `user_created_dt` |
| Timestamp (UTC) | `<event>_ts` | `created_ts`, `updated_ts` |
| Timestamp (non-UTC) | `<event>_<tz>_ts` | `created_cet_ts`, `created_pt_ts` |
| Boolean | `is_<state>`, `has_<thing>`, `was_<event>` | `is_active`, `has_subscription`, `was_refunded` |
| Revenue / money | `<entity>_<measure>_amount` | `user_account_balance_amount`, `subscription_revenue_amount` |
| Common fields | `<entity>_<field>` | `customer_name`, `carrier_name` |

**PK / FK generation:**
- Use `{{ dbt_utils.generate_surrogate_key([...]) }}` for both PKs and FKs

**Type casting — always use dbt macros:**
- `{{ dbt.type_string() }}` / `{{ dbt.type_numeric() }}` / `{{ dbt.type_boolean() }}` / `{{ dbt.type_timestamp() }}`
- `{{ type_date() }}` (community macro, no `dbt.` prefix)

**General Rules:**
- All `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models

---

## Field Ordering (in `select` lists)

1. **Keys** — pk, fks, natural keys
2. **Attributes** — dimensions, slicing fields, descriptive columns
3. **Indexes / ranks** — `row_number()`, rank columns, sequence positions
4. **Metrics** — measures, aggregatable values, `_amount` columns
5. **Booleans** — `is_*` / `has_*` / `was_*` flags
6. **Temporal data types** — `_dt`, `_ts` columns last

Use `{# keys #}`, `{# attributes #}`, etc. Jinja comments to visually mark each group.

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
- An entry in the schema file
- Primary key with `unique` and `not_null` tests

**Schema YAML — auto-generated:**
- The `schema.yml` at the models root is **auto-generated** from compiled SQL — do not hand-create or hand-edit it.
- Configure the generator and re-run it instead of editing the produced file.
- Hand-authored `_sources.yml` files inside `stg_*/` folders are still valid — they define the upstream source mapping, not the model schema, and are not regenerated.

**Additional Tests:**
- `relationships` for foreign keys
- `accepted_values` for enums
- `not_null_where` for conditional requirements
- `dbt_utils.unique_combination_of_columns` for integration models with multiple sources

---

## Documentation Requirements

| Layer | Required | Notes |
|-------|----------|-------|
| Warehouse | All columns must be documented | This is the layer end-users and BI consumers touch |
| Staging | Model `description` in config; column descriptions encouraged | |
| Integration | Document complex / non-obvious logic | |

**Doc blocks — centralised in `field_descriptions.md`:**
- Field descriptions live in `models/field_descriptions.md` as `{% docs %}` blocks
- Schema YAML references them: `description: "{{ doc('user_pk') }}"`
- Avoids duplicate descriptions for the same logical column across models
- Coverage can be enforced via [dbt-meta-testing](https://github.com/tnightengale/dbt-meta-testing)

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
- Use plural entity names (`users` → use `user`)
- Put `ref()` / `source()` calls outside the top `s_*` CTEs
- Use implicit joins or just `join` (use `inner join`, `left join`)
- Use table alias initialisms (`c` → use `customer`)
- Mix tabs and spaces (use 4 spaces)
- Skip tests on primary keys
- Leave warehouse-layer columns undocumented
- Select from sources in non-staging models
- Use `union distinct` without good reason
- Look up PKs in separate queries — generate with `dbt_utils.generate_surrogate_key`
- Hand-create or hand-edit `schema.yml` files — they are auto-generated from compiled SQL
- Cast types with raw SQL — use `{{ dbt.type_*() }}` macros

✅ **Do:**
- Use singular entity names
- All refs / sources in `s_*` CTEs at the top
- A `final` CTE in every model; `select * from final` at the bottom
- Explicit join types
- Descriptive table aliases (no initialisms)
- Consistent indentation (4 spaces)
- Test all primary keys (unique + not_null)
- Document every warehouse-layer column (centralise via `field_descriptions.md` doc blocks)
- Respect layer boundaries (staging → integration → warehouse)
- Prefer `union all`
- Generate PKs/FKs with `dbt_utils.generate_surrogate_key`
- Use `dbt.type_*()` macros for type casting
- Group columns in select lists with `{# keys #}`, `{# attributes #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal data types #}` markers

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
{{ dbt_utils.generate_surrogate_key(['source_system_id', 'source_system']) }}
    as user_pk,

-- Generate foreign key (reference to another table's pk)
{{ dbt_utils.generate_surrogate_key(['account_id', 'source_system']) }}
    as account_fk,

-- Natural key — preserved from source
source_system_id as user_natural_key
```

Note: macro is `generate_surrogate_key` (the older name `surrogate_key` is deprecated in dbt_utils).

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

- [ ] Filename follows the `<layer>_<group>__<entity>(_dim|_fact|_xa).sql` naming pattern
- [ ] File in the correct entity-group subfolder (`stg_<group>/`, `int_<group>/`, `warehouse/wh_<group>/`)
- [ ] All `ref()` / `source()` calls live in `s_*`-prefixed CTEs at the top
- [ ] Model has a `final` CTE; bottom of file is `select * from final`
- [ ] 4-space indentation, < 80-char lines
- [ ] All fields lowercase, `snake_case`
- [ ] Primary key: `<entity>_pk` generated via `dbt_utils.generate_surrogate_key`
- [ ] Foreign keys: `<entity>_fk` generated via `dbt_utils.generate_surrogate_key`
- [ ] Natural keys: `<entity>_natural_key`
- [ ] Dates: `_dt`. Timestamps: `_ts` (UTC) or `_<tz>_ts` (non-UTC)
- [ ] Booleans: `is_*` / `has_*` / `was_*`
- [ ] Revenue / money columns: `_amount` suffix
- [ ] Type casts use `dbt.type_*()` macros, not raw SQL types
- [ ] Explicit join types (`inner join`, `left join`)
- [ ] Field ordering correct: keys → attributes → indexes/ranks → metrics → booleans → temporal data types
- [ ] Column groups marked with `{# keys #}`, `{# attributes #}` etc. Jinja comments (staging models)
- [ ] `description` set in the model's `{{ config() }}` block
- [ ] Materialisation: warehouse = `table`; staging / integration = `view` or ephemeral
- [ ] Primary key has `unique` + `not_null` tests in the schema YAML
- [ ] Warehouse-layer columns have descriptions (via `field_descriptions.md` doc blocks)
- [ ] No SQL reserved words as column names
- [ ] Singular entity names throughout
- [ ] If the project's schema YAML is auto-generated, it has been regenerated after the model change
