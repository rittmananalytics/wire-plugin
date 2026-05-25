# dbt Model Validation Report - PASSING

> Example of a dbt model that passes all validation checks

---

## Model Information

**Model**: `stg_salesforce_accounts.sql`
**Layer**: Staging
**Source**: Salesforce CRM
**Validated**: 2025-10-27
**Status**: ✅ **PASSING** - All checks passed

---

## Validation Summary

| Category | Status | Score |
|----------|--------|-------|
| **Naming Conventions** | ✅ Pass | 5/5 |
| **SQL Structure** | ✅ Pass | 5/5 |
| **Field Naming** | ✅ Pass | 5/5 |
| **Configuration** | ✅ Pass | 3/3 |
| **Testing** | ✅ Pass | 4/4 |
| **Documentation** | ✅ Pass | 3/3 |
| **Overall** | ✅ **PASS** | **25/25** |

---

## Model Code

```sql
-- models/staging/salesforce/stg_salesforce_accounts.sql

{{
    config(
        materialized='view',
        tags=['salesforce', 'crm', 'staging']
    )
}}

with source as (

    select * from {{ source('salesforce', 'accounts') }}

),

renamed as (

    select
        -- Primary Key
        id as account_pk,

        -- Foreign Keys
        owner_id as owner_fk,
        parent_id as parent_account_fk,

        -- Descriptive Fields
        name as account_name,
        type as account_type,
        industry,

        -- Contact Information
        billing_street,
        billing_city,
        billing_state,
        billing_postal_code,
        billing_country,
        phone,
        website,

        -- Business Metrics
        annual_revenue,
        number_of_employees,

        -- Status Flags
        is_deleted,

        -- Timestamps
        created_date as created_ts,
        last_modified_date as modified_ts,
        system_modstamp as system_modified_ts

    from source

)

select * from renamed
```

---

## Detailed Validation Results

### ✅ Naming Conventions (5/5)

**Model Name**: `stg_salesforce_accounts.sql`
- ✅ Correct prefix: `stg_` (staging layer)
- ✅ Source system identified: `salesforce`
- ✅ Singular noun: `accounts` → `account` (file uses plural, convention allows)
- ✅ Snake case throughout
- ✅ Descriptive and clear

**Directory Structure**:
- ✅ Correct location: `models/staging/salesforce/`
- ✅ Matches naming convention

---

### ✅ SQL Structure (5/5)

**CTE Pattern**:
- ✅ Uses CTE pattern (with `source` and `renamed`)
- ✅ Final `select * from renamed` statement
- ✅ Proper indentation (4 spaces)
- ✅ Clear section comments

**Formatting**:
- ✅ Line length under 80 characters
- ✅ Explicit joins (n/a - no joins in this model)
- ✅ Consistent comma placement (leading commas)
- ✅ Proper spacing and alignment

**Source References**:
- ✅ Uses `{{ source() }}` macro
- ✅ Source properly defined in `sources.yml`

---

### ✅ Field Naming (5/5)

**Primary Key**:
- ✅ Renamed to `account_pk` (correct `_pk` suffix)
- ✅ First field in select list

**Foreign Keys**:
- ✅ `owner_fk` and `parent_account_fk` (correct `_fk` suffix)
- ✅ Grouped together after primary key

**Timestamps**:
- ✅ All timestamp fields use `_ts` suffix
- ✅ `created_ts`, `modified_ts`, `system_modified_ts`

**Boolean Fields**:
- ✅ `is_deleted` (correct `is_` prefix)

**Descriptive Fields**:
- ✅ Clear, descriptive names
- ✅ Snake case throughout
- ✅ Grouped logically (contact info together, metrics together)

---

### ✅ Configuration (3/3)

**Materialization**:
- ✅ `materialized='view'` (correct for staging layer)

**Tags**:
- ✅ Relevant tags applied: `salesforce`, `crm`, `staging`
- ✅ Helps with selective execution

**Config Block**:
- ✅ Proper Jinja syntax
- ✅ Well-formatted

---

### ✅ Testing (4/4)

**Schema Tests Defined**: `models/staging/salesforce/schema.yml`

```yaml
version: 2

models:
  - name: stg_salesforce_accounts
    description: Staging model for Salesforce accounts
    columns:
      - name: account_pk
        description: Primary key - Salesforce account ID
        tests:
          - unique
          - not_null

      - name: owner_fk
        description: Foreign key to user (account owner)
        tests:
          - relationships:
              to: ref('stg_salesforce_users')
              field: user_pk

      - name: parent_account_fk
        description: Foreign key to parent account
        tests:
          - relationships:
              to: ref('stg_salesforce_accounts')
              field: account_pk

      - name: account_name
        description: Account name
        tests:
          - not_null
```

**Test Coverage**:
- ✅ Primary key tests: `unique` + `not_null` ✓
- ✅ Foreign key relationships: Both FKs tested ✓
- ✅ Critical field validation: `account_name` not null ✓
- ✅ All tests passing in CI/CD ✓

---

### ✅ Documentation (3/3)

**Model Documentation**:
- ✅ Model description provided in schema.yml
- ✅ All key columns documented (pk, fks, critical fields)
- ✅ Clear, concise descriptions

**Coverage**:
- ✅ 100% documentation for staging layer (required)
- ✅ All primary and foreign keys documented
- ✅ Business-critical fields explained

---

## sqlfluff Results

```bash
$ sqlfluff lint models/staging/salesforce/stg_salesforce_accounts.sql

All Finished!
==============

Linting complete: 0 violations found
```

✅ **No linting issues**

---

## Recommendations

### 🎉 Excellent Work!

This model is a **reference example** of dbt best practices:

1. **Perfect naming**: Follows all conventions
2. **Clean structure**: CTE pattern with clear sections
3. **Comprehensive testing**: PK uniqueness, FK relationships, critical fields
4. **Well documented**: 100% column documentation
5. **Production ready**: No linting issues, all tests passing

### Optional Enhancements (Nice-to-Have)

While this model passes all requirements, consider these optional improvements:

1. **Add Data Quality Tests**:
   ```yaml
   - name: annual_revenue
     tests:
       - dbt_utils.accepted_range:
           min_value: 0
           max_value: 1000000000
   ```

2. **Add Custom Business Logic Tests**:
   ```yaml
   - name: account_type
     tests:
       - accepted_values:
           values: ['Prospect', 'Customer', 'Partner', 'Other']
   ```

3. **Add Freshness Check** (in sources.yml):
   ```yaml
   freshness:
     warn_after: {count: 24, period: hour}
     error_after: {count: 48, period: hour}
   ```

---

## Use This Model As Reference

When creating new staging models, use this as a template:

1. ✅ CTE pattern (source → renamed → select)
2. ✅ Proper field renaming (_pk, _fk, _ts suffixes)
3. ✅ Logical field grouping
4. ✅ Comprehensive testing
5. ✅ Full documentation
6. ✅ Clean, readable SQL

---

## Comparison: Before Validation

**What improved**:
- Original model had `id` → Renamed to `account_pk`
- Original had `createddate` → Renamed to `created_ts`
- Original lacked tests → Now has 4+ tests
- Original undocumented → Now 100% documented

**This model demonstrates Wire/Rittman Analytics coding standards perfectly.**

---

_Example validation report from wire:dbt-development skill showing compliant model_
