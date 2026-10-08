# dbt Model Validation Report: FAIL

Example of a release branch with one new model that breaks several rules, and one changed model that keeps accepted old forms. It shows which findings are reported and which are not.

---

## Branch summary

| Model | Scope | Result |
|---|---|---|
| `models/staging/stg_hubspot/stg_hubspot__contacts.sql` | new | 6 errors, 1 warning |
| `models/staging/stg_salesforce/stg_salesforce__opportunity.sql` | changed | pass |
| 42 other models | unchanged | not checked for section A rules |

Checker: `python3 wire/scripts/lint_conventions.py --domain dbt --convention .wire/conventions/dbt.yml --path models --changed-from 4f2c1a9 --format json`
Form rulings: none.

---

## dbt Model Validation Report

**Model:** `stg_hubspot__contacts.sql`
**Kind:** staging
**Scope:** new
**Convention source:** project override `.wire/conventions/dbt.yml`

### Model as submitted

```sql
{{ config(description = 'HubSpot contacts') }}

with s_contacts as (

    select * from {{ source('hubspot', 'contact') }}

),

renamed as (

    select

        lower(id) as contact_natural_key,
        lower(email) as contact_email,
        lower(lifecycle_stage) as contact_lifecycle_stage,
        email_open_rate as contact_email_open_pct,
        is_unsubscribed,
        cast(created_at as timestamp) as contact_created_ts,
        {{ dbt_utils.generate_surrogate_key(['company_id']) }} as company_fk

    from s_contacts

    where lifecycle_stage = 'customer'

)

select * from renamed
```

### Summary
- 6 errors, 1 warning

## Recommendations

### Errors (must fix before merge)

1. **Missing `Grain:` line**
   - **Location:** line 1
   - **Current:** `description = 'HubSpot contacts'`
   - **Should be:** `description = """Grain: One row per HubSpot contact. ..."""`
   - **Reason:** grain is the first thing needed to join or aggregate the model correctly.

2. **Model does not end with `select * from final`**
   - **Location:** last line
   - **Should be:** a `final` CTE selecting from `renamed`, then `select * from final`
   - **Reason:** one line to change when debugging; every model ends the same way.

3. **Natural key lowercased**
   - **Location:** `lower(id) as contact_natural_key`
   - **Should be:** `cast(id as {{ dbt.type_string() }}) as contact_natural_key`
   - **Reason:** source identifiers can be case-sensitive; lowercasing can merge different records.

4. **Foreign key created in staging**
   - **Location:** `generate_surrogate_key(['company_id']) as company_fk`
   - **Should be:** `cast(company_id as {{ dbt.type_string() }}) as contact_company_natural_key` here; `company_fk` built in the warehouse fact or dimension
   - **Reason:** keys are created in one place, the warehouse, so they stay consistent.

5. **Business filter in staging**
   - **Location:** `where lifecycle_stage = 'customer'`
   - **Should be:** no filter here; filter to customers in the integration model that exposes them
   - **Reason:** staging keeps the source population; this filter hides non-customer contacts from every later model.

6. **Bare warehouse type and unprefixed boolean**
   - **Location:** `cast(created_at as timestamp)`, `is_unsubscribed`
   - **Should be:** `cast(created_at as {{ dbt.type_timestamp() }})`, `contact_is_unsubscribed`
   - **Reason:** macros keep the model portable; the entity prefix says which entity the flag belongs to.

### Warnings (should fix)

1. **`_pct` on a value that may be a ratio**
   - **Location:** `email_open_rate as contact_email_open_pct`
   - **Check:** the `_sources.yml` description of `email_open_rate` says "from 0 to 1". If so, the column is `contact_email_open_ratio`.
   - **Reason:** `_pct` is 0 to 100 and `_ratio` is 0 to 1. On the wrong scale, every chart is out by a factor of 100.

Also required for this new model: column groups with Jinja comments in the eight-group order, a `_schema.yml` entry with tests and doc blocks for every column, and a `_sources.yml` declaration for `contact` (table `name: contacts`, `identifier: contact`).

---

## Not reported

`stg_salesforce__opportunity.sql` changed on this branch but keeps its singular name, its unprefixed columns (`name`, `is_won`) and its schema file's `tests:` key. These are accepted old forms. Wire never renames them, and they are not findings.

The 42 unchanged models are not checked for section A rules. Some use `_agg`, singular names or `ephemeral` intermediate models; none of these is reported.
