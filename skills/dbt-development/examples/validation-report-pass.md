# dbt Model Validation Report: PASS

Example of a new staging model that passes every check.

---

## dbt Model Validation Report

**Model:** `stg_back_office__users.sql`
**Kind:** staging
**Scope:** new (added on this branch since merge-base `4f2c1a9`)
**Convention source:** RA defaults (`wire/conventions/dbt.yml`) | checker run with `--changed-from 4f2c1a9`
**Form rulings:** none

### Summary
- 31 checks passed
- 0 errors, 0 warnings, 1 suggestion

### Naming
- File name `stg_back_office__users.sql`: plural staging name, in `models/staging/stg_back_office/`
- Reads only `source('back_office', 'users')`

### SQL structure and style
- Config description opens `Grain: One row per user account.`
- Import CTE `s_users`; one unit of work per CTE; the deduplication CTE carries a comment saying why rows are removed
- Last CTE `final`; model ends `select * from final`
- Four-space indentation, longest line 104 characters, explicit casts through macros

### Columns
- Eight column groups in order, each with its Jinja comment (no primary or foreign keys in staging, as required)
- Entity prefix on every column; boolean names `user_is_active`, `user_was_deleted`
- `user_account_balance_amount` converted from cents to decimal base currency
- `user_average_session_duration_seconds` states its unit; `user_profile_completion_ratio` is on the 0 to 1 scale
- Attribute strings lowercased; `user_natural_key` and `user_account_natural_key` keep their case
- Date cast with `ra_type_date()`

### Configuration
- No materialization in the model; the staging folder config sets `view`

### Testing
- `user_natural_key`: `unique`, `not_null`
- `not_null` and `dbt_utils.at_least_one` on columns populated in every row; `at_least_one` alone on `user_email`, which is null on some older accounts
- `dbt_utils.accepted_range` 0 to 1 on `user_profile_completion_ratio`
- Test key `data_tests:` (dbt 1.8)

### Documentation
- Every column references a doc block in `models/field_descriptions.md`

### Source declarations
- `users` declared in `_sources.yml` with `identifier: user_accounts`, a `Grain:` line, a `Use it for` sentence, every column described, "Personal data." on `name` and `email`, and `freshness` on `_fivetran_synced`

### sqlfluff
- 0 violations

## Recommendations

### Errors
None.

### Warnings
None.

### Suggestions (project-level, never applied automatically)
1. `dbt_project.yml` sets `+materialized` for staging under the key `analytics` while the project is named `client_analytics`. dbt ignores configs under the wrong key, so staging models currently build with the default materialization. Correcting the key would change how existing models build; discuss with the client before changing it.
