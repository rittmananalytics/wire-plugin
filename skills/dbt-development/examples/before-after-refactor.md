# dbt Model Refactoring: Before & After

> Side-by-side comparison showing transformation from non-compliant to compliant dbt model

---

## Overview

**Model**: Salesforce Opportunities staging model
**Original State**: Non-compliant (multiple convention violations)
**Refactored State**: Fully compliant with Wire/Rittman Analytics standards
**Effort**: 2 points (~1 hour)
**Files Changed**: 2 (model SQL + schema.yml)

---

## Before: Non-Compliant Model

### File: `models/staging/opportunities.sql`

**Issues**:
- ❌ Missing `stg_` prefix
- ❌ Not in source subdirectory
- ❌ No CTE pattern
- ❌ Poor field naming
- ❌ No config block
- ❌ No tests
- ❌ No documentation

```sql
-- models/staging/opportunities.sql

select
    id,
    accountid,
    name,
    stagename,
    amount,
    closedate,
    probability,
    isclosed,
    iswon,
    createddate,
    lastmodifieddate,
    ownerid,
    type
from raw.salesforce.opportunities
where isdeleted = 0
```

**Validation Score**: 6/25 (24%)

---

## After: Compliant Model

### File: `models/staging/salesforce/stg_salesforce_opportunities.sql`

**Improvements**:
- ✅ Correct naming: `stg_salesforce_opportunities.sql`
- ✅ Proper directory: `models/staging/salesforce/`
- ✅ CTE pattern (source → renamed)
- ✅ Correct field naming (_pk, _fk, _ts suffixes)
- ✅ Config block with materialization + tags
- ✅ Logical field grouping
- ✅ Source reference via `{{ source() }}`
- ✅ Comments explaining sections

```sql
-- models/staging/salesforce/stg_salesforce_opportunities.sql

{{
    config(
        materialized='view',
        tags=['salesforce', 'crm', 'staging', 'opportunities']
    )
}}

with source as (

    select * from {{ source('salesforce', 'opportunities') }}

),

renamed as (

    select
        -- Primary Key
        id as opportunity_pk,

        -- Foreign Keys
        accountid as account_fk,
        ownerid as owner_fk,

        -- Descriptive Fields
        name as opportunity_name,
        type as opportunity_type,
        stagename as stage_name,

        -- Financial Fields
        amount,
        probability,

        -- Status Flags
        isclosed as is_closed,
        iswon as is_won,

        -- Timestamps
        closedate as close_date,
        createddate as created_ts,
        lastmodifieddate as modified_ts

    from source

    -- Filter out deleted opportunities (soft deletes in Salesforce)
    where isdeleted = 0

)

select * from renamed
```

**Validation Score**: 22/25 (88%) - Tests and documentation needed

---

## Tests Added

### File: `models/staging/salesforce/schema.yml`

**Before**: No schema.yml file existed

**After**:

```yaml
version: 2

models:
  - name: stg_salesforce_opportunities
    description: >
      Staging model for Salesforce opportunities. Contains all active
      (non-deleted) opportunities with sales pipeline information including
      stage, amount, and close date.

    columns:
      - name: opportunity_pk
        description: Primary key - Salesforce opportunity ID
        tests:
          - unique
          - not_null

      - name: account_fk
        description: Foreign key to associated account
        tests:
          - not_null
          - relationships:
              to: ref('stg_salesforce_accounts')
              field: account_pk

      - name: owner_fk
        description: Foreign key to opportunity owner (user)
        tests:
          - relationships:
              to: ref('stg_salesforce_users')
              field: user_pk

      - name: opportunity_name
        description: Name/title of the opportunity
        tests:
          - not_null

      - name: stage_name
        description: Current sales stage (e.g., 'Prospecting', 'Closed Won')
        tests:
          - not_null

      - name: amount
        description: Opportunity value in account currency
        tests:
          - not_null

      - name: close_date
        description: Expected or actual close date
        tests:
          - not_null

      - name: probability
        description: Win probability percentage (0-100)

      - name: is_closed
        description: Boolean flag indicating if opportunity is closed

      - name: is_won
        description: Boolean flag indicating if opportunity was won

      - name: created_ts
        description: Timestamp when opportunity was created in Salesforce

      - name: modified_ts
        description: Timestamp when opportunity was last modified
```

**Validation Score**: Now 25/25 (100%) ✅

---

## Detailed Changes Breakdown

### 1. File Naming & Structure

**Before**:
```
models/staging/opportunities.sql
```

**After**:
```
models/staging/salesforce/stg_salesforce_opportunities.sql
```

**Changes**:
- ✅ Added `stg_` prefix (identifies layer)
- ✅ Added source system `salesforce_` (identifies source)
- ✅ Created source subdirectory `/salesforce/`
- ✅ Matches naming convention exactly

---

### 2. Configuration

**Before**: No config block (uses defaults)

**After**:
```sql
{{
    config(
        materialized='view',
        tags=['salesforce', 'crm', 'staging', 'opportunities']
    )
}}
```

**Changes**:
- ✅ Explicit materialization (view - correct for staging)
- ✅ Tags for selective execution
- ✅ Clear, declarative configuration

---

### 3. SQL Structure

**Before**: Direct select from raw table

**After**: CTE pattern with clear sections

```sql
with source as (
    select * from {{ source('salesforce', 'opportunities') }}
),

renamed as (
    select
        -- Transformation logic
    from source
    where isdeleted = 0
)

select * from renamed
```

**Changes**:
- ✅ Separated source reference from transformation
- ✅ Makes model extensible (easy to add more CTEs)
- ✅ Follows established pattern
- ✅ Used `{{ source() }}` macro instead of raw table reference

---

### 4. Field Naming

**Before → After**:

| Before (Non-Compliant) | After (Compliant) | Convention |
|------------------------|-------------------|------------|
| `id` | `opportunity_pk` | Primary key: `_pk` suffix |
| `accountid` | `account_fk` | Foreign key: `_fk` suffix |
| `ownerid` | `owner_fk` | Foreign key: `_fk` suffix |
| `name` | `opportunity_name` | Descriptive: full context |
| `type` | `opportunity_type` | Descriptive: full context |
| `stagename` | `stage_name` | Snake case |
| `isclosed` | `is_closed` | Boolean: `is_` prefix |
| `iswon` | `is_won` | Boolean: `is_` prefix |
| `closedate` | `close_date` | Date: snake case |
| `createddate` | `created_ts` | Timestamp: `_ts` suffix |
| `lastmodifieddate` | `modified_ts` | Timestamp: `_ts` suffix |

**Key Improvements**:
- ✅ All conventions followed
- ✅ Field purpose clear from name
- ✅ Consistent style (snake_case)
- ✅ No ambiguity

---

### 5. Field Grouping

**Before**: Random order (as they appear in source)

**After**: Logical grouping with comments

```sql
-- Primary Key
opportunity_pk,

-- Foreign Keys
account_fk,
owner_fk,

-- Descriptive Fields
opportunity_name,
opportunity_type,
stage_name,

-- Financial Fields
amount,
probability,

-- Status Flags
is_closed,
is_won,

-- Timestamps
close_date,
created_ts,
modified_ts
```

**Benefits**:
- ✅ Easier to scan
- ✅ Clear sections
- ✅ Maintainable
- ✅ Self-documenting

---

### 6. Testing

**Before**: No tests ❌

**After**: Comprehensive test coverage ✅

**Primary Key Tests**:
```yaml
- name: opportunity_pk
  tests:
    - unique
    - not_null
```

**Foreign Key Tests**:
```yaml
- name: account_fk
  tests:
    - relationships:
        to: ref('stg_salesforce_accounts')
        field: account_pk
```

**Critical Field Tests**:
```yaml
- name: opportunity_name
  tests:
    - not_null
- name: amount
  tests:
    - not_null
```

**Test Count**:
- Primary key: 2 tests (unique + not_null)
- Foreign keys: 2 relationship tests
- Critical fields: 3 not_null tests
- **Total**: 7 tests

---

### 7. Documentation

**Before**: 0% documented ❌

**After**: 100% documented ✅

**Model-Level**:
```yaml
description: >
  Staging model for Salesforce opportunities. Contains all active
  (non-deleted) opportunities with sales pipeline information...
```

**Column-Level**: All 13 columns documented

**Documentation Coverage**:
- Model description: ✅
- Primary key: ✅
- Foreign keys: ✅
- Business fields: ✅
- Technical fields: ✅
- **Coverage**: 100%

---

## Impact Comparison

### Code Quality Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Validation Score** | 6/25 (24%) | 25/25 (100%) | +76% |
| **Lines of Code** | 19 | 58 | +205% (more complete) |
| **Tests** | 0 | 7 | +7 tests |
| **Documentation** | 0% | 100% | +100% |
| **Maintainability** | Low | High | Qualitative |
| **Convention Adherence** | 1/8 patterns | 8/8 patterns | +700% |

### Specific Improvements

**Naming**: 2/5 → 5/5 (perfect)
**Structure**: 1/5 → 5/5 (perfect)
**Field Naming**: 1/5 → 5/5 (perfect)
**Configuration**: 0/3 → 3/3 (perfect)
**Testing**: 0/4 → 4/4 (perfect)
**Documentation**: 0/3 → 3/3 (perfect)

---

## Common Refactoring Patterns

### Pattern 1: Add Staging Prefix

```bash
# Before
models/staging/opportunities.sql

# After
models/staging/salesforce/stg_salesforce_opportunities.sql
```

**Steps**:
1. Create source subdirectory: `mkdir models/staging/salesforce`
2. Rename file with `stg_` prefix
3. Move to subdirectory
4. Update any references in downstream models

---

### Pattern 2: Wrap in CTE Pattern

**Before**:
```sql
select
    field1,
    field2
from raw.table
where condition
```

**After**:
```sql
with source as (
    select * from {{ source('system', 'table') }}
),

renamed as (
    select
        field1,
        field2
    from source
    where condition
)

select * from renamed
```

---

### Pattern 3: Fix Field Naming

**Before**: `createddate`, `id`, `accountid`, `isclosed`

**After**: `created_ts`, `object_pk`, `account_fk`, `is_closed`

**Rule Application**:
- Primary keys: add `_pk`
- Foreign keys: add `_fk`
- Timestamps: add `_ts`
- Booleans: add `is_` or `has_` prefix
- All: convert to snake_case

---

### Pattern 4: Add Configuration

```sql
{{
    config(
        materialized='view',  # or 'table' for warehouse
        tags=['source_system', 'domain', 'layer']
    )
}}
```

**Template for Staging**:
- Materialization: `view`
- Tags: `[source, domain, 'staging']`

**Template for Warehouse**:
- Materialization: `table`
- Tags: `[domain, 'warehouse', fact/dim]`

---

### Pattern 5: Add Basic Tests

**Minimum for Staging**:
```yaml
models:
  - name: stg_<source>_<object>
    columns:
      - name: <object>_pk
        tests:
          - unique
          - not_null
      - name: <critical_field>
        tests:
          - not_null
```

**Expand with**:
- Foreign key relationships
- Accepted values (for enums)
- Custom business logic tests

---

## Refactoring Checklist

Use this when refactoring any dbt model:

### File Structure
- [ ] File named: `stg_<source>_<object>.sql` or `int_<domain>_<object>.sql` or `<object>_dim/fct.sql`
- [ ] In correct directory: `models/<layer>/<source or domain>/`
- [ ] Referenced in `dbt_project.yml` if needed

### SQL Structure
- [ ] Has config block (materialization + tags)
- [ ] Uses CTE pattern (source → transformation CTEs → final select)
- [ ] Uses `{{ source() }}` or `{{ ref() }}` macros (not raw table names)
- [ ] Has comments for each major section
- [ ] WHERE clause explained if filtering data

### Field Naming
- [ ] Primary key has `_pk` suffix
- [ ] Foreign keys have `_fk` suffix
- [ ] Timestamps have `_ts` suffix
- [ ] Booleans have `is_` or `has_` prefix
- [ ] All fields are snake_case
- [ ] Fields grouped logically (pk → fks → descriptive → timestamps)

### Testing
- [ ] Primary key tested: unique + not_null
- [ ] Foreign keys tested: relationships
- [ ] Critical business fields tested: not_null or accepted_values
- [ ] Custom business logic tested if applicable

### Documentation
- [ ] Model description exists in schema.yml
- [ ] All critical columns documented
- [ ] Staging: 100% column documentation
- [ ] Integration: Key transformation columns documented
- [ ] Warehouse: All dimension/fact columns documented

### Code Quality
- [ ] Indentation consistent (4 spaces)
- [ ] Lines under 80 characters where possible
- [ ] No hard-coded values (use variables or sources)
- [ ] sqlfluff passes with no errors

---

## Time Investment vs Value

**Refactoring Effort**: 1-2 hours per model

**Value Gained**:
- ✅ Catches data quality issues (PK uniqueness, FK relationships)
- ✅ Self-documenting code (clear naming, tests, docs)
- ✅ Easier onboarding (new team members understand faster)
- ✅ Reduced bugs (conventions prevent common mistakes)
- ✅ Better maintainability (consistent patterns)
- ✅ Confidence in data quality (comprehensive testing)

**ROI**: High - upfront time investment pays off in reduced debugging and maintenance

---

## Key Takeaways

1. **Small changes, big impact**: Renaming fields and adding tests dramatically improves quality
2. **Conventions matter**: Consistent patterns make code predictable and maintainable
3. **Testing is essential**: Primary key and foreign key tests catch critical issues
4. **Documentation pays off**: 100% documentation seems like overhead but saves time later
5. **CTE pattern scales**: Easy to extend with additional transformations
6. **Use templates**: Copy from compliant models rather than starting from scratch

---

_Example refactoring guide from wire:dbt-development skill showing convention application_
