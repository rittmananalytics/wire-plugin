# Changing an Existing Model: Before and After

Example of a ticket-sized change to a model in an existing client project. It shows what Wire changes and what it leaves alone.

---

## The request

"Add the opportunity's discount, its forecast category and the owner's region to the Salesforce opportunities staging model."

## The project

- Existing project, dbt 1.7. Schema files use `tests:`.
- Staging models are singular and unprefixed (`stg_salesforce__opportunity`, columns `name`, `is_won`).
- `.wire/conventions/dbt.yml` has no `form_choices:` ruling.
- The model is read by `int_sales__opportunity`, a LookML view and a Hightouch sync.

---

## Before

`models/staging/stg_salesforce/stg_salesforce__opportunity.sql`

```sql
{{ config(description = 'Salesforce opportunities') }}

with s_opportunities as (

    select * from {{ source('salesforce', 'opportunity') }}

),

renamed as (

    select

        id as opportunity_natural_key,
        account_id as account_natural_key,
        lower(name) as name,
        lower(stage_name) as stage_name,
        amount,
        is_won,
        cast(created_date as {{ dbt.type_timestamp() }}) as created_ts

    from s_opportunities

    where not is_deleted

)

select * from renamed
```

## After

```sql
{{
    config(
        description = """
            Grain: One row per Salesforce opportunity that is not deleted.
            Salesforce opportunities, renamed and cast.
        """
    )
}}

with s_opportunities as (

    select * from {{ source('salesforce', 'opportunity') }}

),

-- Deleted opportunities are kept in the Salesforce table with is_deleted set. They are not
-- opportunities the business recognises, so they are removed here.
current_opportunities as (

    select * from s_opportunities

    where not is_deleted

),

renamed as (

    select

        {# natural keys #}
        id as opportunity_natural_key,
        account_id as account_natural_key,
        {# attributes #}
        lower(name) as name,
        lower(stage_name) as stage_name,
        lower(forecast_category_name) as opportunity_forecast_category_name,
        {# metrics #}
        amount,
        cast(discount_percent__c as {{ dbt.type_numeric() }}) as opportunity_discount_pct,
        {# booleans #}
        is_won,
        {# temporal #}
        cast(created_date as {{ dbt.type_timestamp() }}) as created_ts

    from current_opportunities

),

final as (

    select * from renamed

)

select * from final
```

---

## What changed, and why

| Change | Rule | Reason |
|---|---|---|
| `Grain:` line added to the config description | Section A, changed model | Grain is the first thing a reader needs |
| `where not is_deleted` moved into its own CTE with a comment | Staging filters only for correctness, with a comment | A reader sees why rows are removed |
| New columns `opportunity_forecast_category_name`, `opportunity_discount_pct` | New columns take the new form (no ruling) | Prefix says which entity; `_pct` says the 0 to 100 scale |
| Column groups marked with Jinja comments | Section A, changed model | Eight groups, in order |
| `final` CTE and `select * from final` | Section A, changed model | One line to change when debugging |
| `opportunity_natural_key` not lowercased | Natural keys keep their case | Salesforce IDs are case-sensitive |

## What did not change, and why

| Kept | Reason |
|---|---|
| File name `stg_salesforce__opportunity.sql` (singular) | Never rename existing objects; three consumers read it |
| Owner region not added here | It comes from another concept (the Salesforce user). A join that derives a value from another concept, even in the same source, belongs in a later model: it is added to `int_sales__opportunity` |
| Columns `name`, `stage_name`, `amount`, `is_won`, `created_ts` (unprefixed) | Never rename existing columns; the LookML view and the sync use them |
| `renamed` CTE name | Renaming a CTE adds diff and no value |
| `tests:` in `stg_salesforce.yml` | dbt 1.7, and the file already uses `tests:` |
| Source file `_salesforce__sources.yml` | Old source file name still accepted |

Because the model already uses unprefixed columns, ask the consultant before writing whether the project wants a `column_prefix: none` ruling. If they do, record it in `decisions.md` and `.wire/conventions/dbt.yml`, and name the new columns `forecast_category_name` and `discount_pct` instead.

---

## Schema entry added

In `models/staging/stg_salesforce/stg_salesforce.yml` (existing file, existing key):

```yaml
      - name: opportunity_forecast_category_name
        description: '{{ doc("opportunity_forecast_category_name") }}'
        tests:
          - not_null
          - dbt_utils.at_least_one
          - accepted_values:
              values: ['pipeline', 'best case', 'commit', 'closed', 'omitted']

      - name: opportunity_discount_pct
        description: '{{ doc("opportunity_discount_pct") }}'
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100
```

Doc blocks for both columns added to `models/field_descriptions.md`. Because the model changed, every column in it is documented: doc blocks were added for the seven existing columns that had none.

## Source declaration checked

`discount_percent__c` and `forecast_category_name` are already declared under the `opportunity` table in `_salesforce__sources.yml`. Had they been missing, they would be added with descriptions in Salesforce terms: what the column holds, its unit or allowed values, and what a null means.

## Checker run

```
python3 wire/scripts/lint_conventions.py --domain dbt \
  --convention wire/conventions/dbt.yml --path models \
  --changed-from "$(git merge-base HEAD main)" --format json
```

Findings: none on the changed model. No findings on unchanged models, which keep their old forms.

---

## When a rename is wanted

If the client wants `stg_salesforce__opportunity` renamed to `stg_salesforce__opportunities`, or its columns prefixed, that is a refactor: a separate decision, planned with its consumers, in a `/wire:data_refactor-generate` run. It is never done as part of a feature change.
