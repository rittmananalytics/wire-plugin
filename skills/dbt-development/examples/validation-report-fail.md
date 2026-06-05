# dbt Model Validation Report - FAILING

> Example of a dbt model with multiple issues requiring fixes

---

## Model Information

**Model**: `hubspot_contacts.sql`
**Layer**: Staging (appears to be)
**Source**: HubSpot CRM
**Validated**: 2025-10-27
**Status**: ⚠️ **FAILING** - 12 issues found (6 critical, 4 important, 2 nice-to-have)

---

## Validation Summary

| Category | Status | Score | Issues |
|----------|--------|-------|--------|
| **Naming Conventions** | ❌ Fail | 1/5 | 3 critical |
| **SQL Structure** | ⚠️ Partial | 2/5 | 2 important |
| **Field Naming** | ❌ Fail | 2/5 | 2 critical |
| **Configuration** | ⚠️ Partial | 1/3 | 1 important |
| **Testing** | ❌ Fail | 0/4 | 1 critical |
| **Documentation** | ⚠️ Partial | 1/3 | 1 important + 2 nice-to-have |
| **Overall** | ❌ **FAIL** | **7/25** | **12 issues** |

---

## Model Code (Current - With Issues)

```sql
-- models/staging/hubspot_contacts.sql

select
    id,
    createdate,
    hs_object_id,
    lastmodifieddate,
    email,
    firstname,
    lastname,
    company,
    phone,
    lifecyclestage,
    hs_lead_status
from {{ source('hubspot', 'contacts') }}
where is_deleted = false
```

---

## Critical Issues (Must Fix)

### 🚨 Issue 1: Incorrect File Name
**Category**: Naming Conventions
**Severity**: Critical

**Problem**:
- File name: `hubspot_contacts.sql`
- Should be: `stg_hubspot_contacts.sql`

**Why This Matters**:
- Missing `stg_` prefix makes layer unclear
- Breaks naming convention expectations
- Harder to identify model purpose in dbt DAG
- Violates staging layer naming standards

**Fix**:
```bash
mv models/staging/hubspot_contacts.sql models/staging/hubspot/stg_hubspot_contacts.sql
```

---

### 🚨 Issue 2: Missing CTE Pattern
**Category**: SQL Structure
**Severity**: Critical

**Problem**:
- Direct select from source (no CTE)
- No `source` and `renamed` pattern
- Logic mixed with source reference

**Why This Matters**:
- Makes model harder to extend
- Breaks established pattern
- Reduces readability
- Difficult to add transformations later

**Fix**:
```sql
with source as (
    select * from {{ source('hubspot', 'contacts') }}
),

renamed as (
    select
        -- fields here
    from source
    where is_deleted = false
)

select * from renamed
```

---

### 🚨 Issue 3: No Primary Key Suffix
**Category**: Field Naming
**Severity**: Critical

**Problem**:
- Field: `id`
- Should be: `contact_pk`

**Why This Matters**:
- Primary key not identifiable
- Breaks downstream joins
- Testing framework expects `_pk` suffix
- Convention violation

**Fix**:
```sql
id as contact_pk
```

---

### 🚨 Issue 4: Missing Timestamp Suffixes
**Category**: Field Naming
**Severity**: Critical

**Problem**:
- Fields: `createdate`, `lastmodifieddate`
- Should be: `created_ts`, `modified_ts`

**Why This Matters**:
- Unclear data type (date? timestamp?)
- Breaks timestamp naming convention
- Makes queries less readable

**Fix**:
```sql
createdate as created_ts,
lastmodifieddate as modified_ts
```

---

### 🚨 Issue 5: No Tests Defined
**Category**: Testing
**Severity**: Critical

**Problem**:
- No schema.yml file
- No primary key tests (unique + not_null)
- No relationship tests
- No field validations

**Why This Matters**:
- Data quality issues undetected
- Duplicate records possible
- Broken relationships unnoticed
- Fails testing requirements for staging

**Fix**: Create `schema.yml`:
```yaml
version: 2

models:
  - name: stg_hubspot_contacts
    description: Staging model for HubSpot contacts
    columns:
      - name: contact_pk
        description: Primary key - HubSpot contact ID
        tests:
          - unique
          - not_null
      - name: email
        description: Contact email address
        tests:
          - not_null
```

---

### 🚨 Issue 6: Incorrect Directory Structure
**Category**: Naming Conventions
**Severity**: Critical

**Problem**:
- Current: `models/staging/hubspot_contacts.sql`
- Should be: `models/staging/hubspot/stg_hubspot_contacts.sql`

**Why This Matters**:
- Source-specific models should be in source subdirectory
- Breaks organizational convention
- Makes codebase harder to navigate

**Fix**:
```bash
mkdir -p models/staging/hubspot
mv models/staging/hubspot_contacts.sql models/staging/hubspot/stg_hubspot_contacts.sql
```

---

## Important Issues (Should Fix)

### ⚠️ Issue 7: No Field Grouping
**Category**: SQL Structure
**Severity**: Important

**Problem**:
- Fields listed randomly
- No logical grouping (pk, fks, descriptive, timestamps)
- Hard to scan and understand

**Why This Matters**:
- Reduces readability
- Makes maintenance harder
- Doesn't follow convention

**Fix**: Group fields logically:
```sql
-- Primary Key
contact_pk,

-- Descriptive Fields
email,
first_name,
last_name,
company_name,
phone,

-- Status Fields
lifecycle_stage,
lead_status,

-- Timestamps
created_ts,
modified_ts
```

---

### ⚠️ Issue 8: Inconsistent Field Naming
**Category**: Field Naming
**Severity**: Important

**Problem**:
- Fields: `firstname`, `lastname`, `lifecyclestage`, `hs_lead_status`
- Mix of formats: camelCase source names kept, HubSpot prefixes retained

**Why This Matters**:
- Inconsistent style
- Source-specific prefixes (`hs_`) should be removed
- Not snake_case throughout

**Fix**:
```sql
firstname as first_name,
lastname as last_name,
lifecyclestage as lifecycle_stage,
hs_lead_status as lead_status
```

---

### ⚠️ Issue 9: Wrong Materialization
**Category**: Configuration
**Severity**: Important

**Problem**:
- No config block
- Defaults to `view` (correct), but not explicit
- No tags

**Why This Matters**:
- Configuration should be explicit
- Tags help with selective execution
- Best practice to declare materialization

**Fix**:
```sql
{{
    config(
        materialized='view',
        tags=['hubspot', 'crm', 'staging']
    )
}}
```

---

### ⚠️ Issue 10: Incomplete Documentation
**Category**: Documentation
**Severity**: Important

**Problem**:
- No schema.yml file
- No model description
- No column descriptions
- Fails 100% documentation requirement for staging

**Why This Matters**:
- Staging layer requires 100% documentation
- Team doesn't understand model purpose
- Columns are unclear to downstream users

**Fix**: Add to schema.yml:
```yaml
models:
  - name: stg_hubspot_contacts
    description: >
      Staging model for HubSpot contacts. Contains all active (non-deleted)
      contacts with basic contact information and lifecycle stage.
    columns:
      - name: contact_pk
        description: Primary key - HubSpot contact ID
      - name: email
        description: Primary email address for contact
      # ... document all columns
```

---

## Nice-to-Have Issues (Polish)

### 💡 Issue 11: Source HubSpot Field Names Exposed
**Category**: Field Naming
**Severity**: Nice-to-have

**Problem**:
- Field: `hs_object_id`
- HubSpot-specific internal ID exposed

**Why This Matters**:
- Not business-friendly
- Exposes source system internals
- May not be needed downstream

**Recommendation**:
- Remove if not used downstream
- Or rename to `hubspot_object_id` if needed

---

### 💡 Issue 12: No Comments Explaining Logic
**Category**: SQL Structure
**Severity**: Nice-to-have

**Problem**:
- WHERE clause has no comment
- `is_deleted = false` filter unexplained

**Why This Matters**:
- Business logic undocumented
- Future maintainers don't know why filter exists

**Recommendation**:
```sql
-- Filter out deleted contacts (soft deletes in HubSpot)
where is_deleted = false
```

---

## sqlfluff Results

```bash
$ sqlfluff lint models/staging/hubspot_contacts.sql

== [models/staging/hubspot_contacts.sql] FAIL
L:   3 | P:   1 | L003 | Indentation not consistent with previous lines
L:   4 | P:   1 | L003 | Indentation not consistent with previous lines
L:  14 | P:   1 | L011 | Implicit aliasing of table reference
L:  15 | P:   7 | L014 | Unqualified column reference

6 linting issues found
```

❌ **Linting issues detected**

---

## Priority Fix Roadmap

### Phase 1: Critical Fixes (Must Do Before Merge)

**Effort**: 2 points (~1 hour)

1. ✅ **Rename file**: `hubspot_contacts.sql` → `stg_hubspot_contacts.sql`
2. ✅ **Move to directory**: Create `models/staging/hubspot/` subdirectory
3. ✅ **Add CTE pattern**: Wrap in `source` and `renamed` CTEs
4. ✅ **Fix primary key**: `id` → `contact_pk`
5. ✅ **Fix timestamps**: Add `_ts` suffixes
6. ✅ **Create tests**: Add schema.yml with PK tests (unique + not_null)

**Result**: Model becomes mergeable and follows basic conventions

---

### Phase 2: Important Improvements (Should Do This Sprint)

**Effort**: 1 point (~30 minutes)

1. ✅ **Group fields logically**: PK → descriptive → status → timestamps
2. ✅ **Fix all field names**: Snake case, remove HubSpot prefixes
3. ✅ **Add config block**: Explicit materialization + tags
4. ✅ **Document model**: Add descriptions for model and all columns

**Result**: Model meets full staging layer standards

---

### Phase 3: Polish (Can Do Later)

**Effort**: 0.5 points (~15 minutes)

1. ✅ **Remove/rename** `hs_object_id` if not needed
2. ✅ **Add comments** explaining business logic (WHERE clause)
3. ✅ **Run sqlfluff fix**: Auto-fix linting issues

**Result**: Model is reference-quality

---

## Corrected Model (After Fixes)

```sql
-- models/staging/hubspot/stg_hubspot_contacts.sql

{{
    config(
        materialized='view',
        tags=['hubspot', 'crm', 'staging']
    )
}}

with source as (

    select * from {{ source('hubspot', 'contacts') }}

),

renamed as (

    select
        -- Primary Key
        id as contact_pk,

        -- Descriptive Fields
        email,
        firstname as first_name,
        lastname as last_name,
        company as company_name,
        phone,

        -- Status Fields
        lifecyclestage as lifecycle_stage,
        hs_lead_status as lead_status,

        -- Timestamps
        createdate as created_ts,
        lastmodifieddate as modified_ts

    from source

    -- Filter out deleted contacts (soft deletes in HubSpot)
    where is_deleted = false

)

select * from renamed
```

**Validation Result**: ✅ **PASS** - 25/25

---

## Key Takeaways

### What Makes This Model Non-Compliant

1. **Missing staging prefix** (`stg_`)
2. **No CTE pattern** (direct select)
3. **Wrong field naming** (no `_pk`, `_ts` suffixes)
4. **No tests** (fails data quality requirements)
5. **No documentation** (fails 100% staging requirement)
6. **Wrong directory structure** (flat instead of source subdirectory)

### How to Avoid These Issues

✅ **Use existing staging models as templates** (see `stg_salesforce_accounts.sql`)
✅ **Run validation early** (don't wait for PR)
✅ **Follow checklist**:
- [ ] File name: `stg_<source>_<object>.sql`
- [ ] Directory: `models/staging/<source>/`
- [ ] CTE pattern: source → renamed → select
- [ ] Field naming: `_pk`, `_fk`, `_ts` suffixes
- [ ] Config block with materialization + tags
- [ ] Tests: PK (unique + not_null) + critical fields
- [ ] Documentation: 100% for staging

---

## Comparison: Before vs After

| Aspect | Before (Failing) | After (Passing) |
|--------|------------------|-----------------|
| **File name** | `hubspot_contacts.sql` | `stg_hubspot_contacts.sql` |
| **Directory** | `models/staging/` | `models/staging/hubspot/` |
| **SQL pattern** | Direct select | CTE pattern |
| **Primary key** | `id` | `contact_pk` |
| **Timestamps** | `createdate` | `created_ts` |
| **Tests** | None | 4+ tests |
| **Documentation** | 0% | 100% |
| **Score** | 7/25 (28%) | 25/25 (100%) |

---

_Example validation report from wire:dbt-development skill showing non-compliant model with fix roadmap_
