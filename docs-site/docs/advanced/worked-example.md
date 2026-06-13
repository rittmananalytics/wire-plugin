---
sidebar_position: 1
title: Worked Example
---

# Worked Example: Barton Peveril College

This walkthrough traces a complete Wire engagement from initial kick-off through delivery handover, using a real-world further education client. Barton Peveril is a sixth-form college in Hampshire. The engagement covers student data, finance, and operational analytics — a `full_platform` release type with BigQuery, dbt, and Looker.

## Engagement setup

The project folder is `20240115_barton_peveril_full_platform`. The CLAUDE.md at the root contains project context — the student management system (Quercus), the MIS (Unit-e), finance system (PS Financials), and the key stakeholders.

```
/wire:new
```

Wire prompts for release type (`full_platform`), project name (`barton_peveril`), client contact, and delivery start date. It writes:
- `.wire/releases/20240115_barton_peveril_full_platform/` — engagement folder
- `.wire/releases/20240115_barton_peveril_full_platform/status.md` — starts at Phase 0

## Phase 1 — Requirements

### Problem definition

```
/wire:problem-definition-generate 20240115_barton_peveril_full_platform
```

Wire reads the CLAUDE.md, searches Fathom for any kick-off call transcripts, and drafts the problem definition document. It surfaces three key gaps the college has articulated:

1. No single view of student progression from application through to destination
2. Finance reporting done manually in Excel — no connection to actuals from PS Financials
3. Staff using three separate systems to track attendance, pastoral notes, and performance

The draft maps each problem to a proposed data domain and a set of named metrics.

```
/wire:problem-definition-validate 20240115_barton_peveril_full_platform
/wire:problem-definition-review 20240115_barton_peveril_full_platform
```

The review command presents the draft and opens a feedback loop. The principal asks to add "destinations data" (what students go on to after A levels) as a fourth domain. Wire records this as a design decision in the execution log, updates the document, and marks it Approved.

### High-level design

```
/wire:high-level-design-generate 20240115_barton_peveril_full_platform
/wire:high-level-design-validate 20240115_barton_peveril_full_platform
/wire:high-level-design-review 20240115_barton_peveril_full_platform
```

The HLD document specifies four data domains (Students, Finance, Attendance, Destinations), the source systems for each, and the target mart tables in BigQuery. It also records the agreed ingestion approach: Fivetran for PS Financials, custom Python Cloud Functions for Quercus and Unit-e (neither has a Fivetran connector).

### Source-to-target mapping

```
/wire:source-to-target-map-generate 20240115_barton_peveril_full_platform
/wire:source-to-target-map-validate 20240115_barton_peveril_full_platform
/wire:source-to-target-map-review 20240115_barton_peveril_full_platform
```

Wire asks for access to the source system schemas. The client provides read-only BigQuery export snapshots of Quercus and Unit-e. Wire reads the `INFORMATION_SCHEMA` and builds the mapping document — source columns, target columns, transformation rules, data types, and null handling.

## Phase 2 — Design

### dbt project structure

```
/wire:dbt-project-design-generate 20240115_barton_peveril_full_platform
/wire:dbt-project-design-validate 20240115_barton_peveril_full_platform
/wire:dbt-project-design-review 20240115_barton_peveril_full_platform
```

Wire generates the project structure design: five staging schemas (one per source system), two integration schemas (student events, finance), and four mart schemas. It specifies that Quercus and Unit-e each use a separate staging schema to keep source system logic isolated before unification.

### Looker design

```
/wire:looker-design-generate 20240115_barton_peveril_full_platform
/wire:looker-design-validate 20240115_barton_peveril_full_platform
/wire:looker-design-review 20240115_barton_peveril_full_platform
```

Wire produces a Looker design document: models, explores, and dashboard wireframes for each data domain. The student domain gets three explores — `students`, `student_courses`, `student_destinations`. The VP of Data notes in the review that the attendance explore should filter out exclusion records by default (Quercus marks excluded students differently from absent ones). Wire records this as a Looker design decision and updates the default filters in the spec.

## Phase 3 — Development

### Ingestion

```
/wire:ingestion-generate 20240115_barton_peveril_full_platform
```

Wire generates:
- Fivetran connector configuration for PS Financials (BigQuery destination, 6-hour sync)
- Python Cloud Function code for Quercus full-extract (runs nightly, writes to `raw_quercus` BigQuery dataset)
- Python Cloud Function code for Unit-e incremental extract (runs hourly, writes to `raw_unit_e`)

The Cloud Function code follows the Wire standard for Cloud Run deployments: `requirements.txt`, `Dockerfile`, `main.py`, and a `cloudbuild.yaml` for CI deployment.

### dbt models

Wire generates staging, integration, and mart models in batches — one domain at a time.

```
/wire:dbt-models-generate 20240115_barton_peveril_full_platform --domain students
/wire:dbt-models-generate 20240115_barton_peveril_full_platform --domain finance
/wire:dbt-models-generate 20240115_barton_peveril_full_platform --domain attendance
/wire:dbt-models-generate 20240115_barton_peveril_full_platform --domain destinations
```

For the students domain, Wire generates:
- `stg_quercus__students.sql`, `stg_unit_e__students.sql` — source-system staging
- `int_students__unified.sql` — coalesces the two staging sources with deduplication logic
- `dim_students.sql`, `fct_student_course_enrolments.sql`, `fct_student_destinations.sql` — mart layer

```
/wire:dbt-models-validate 20240115_barton_peveril_full_platform --domain students
```

The validate step runs `dbt compile`, `dbt run --select students`, and `dbt test --select students`. It surfaces two test failures: a `not_null` test on `student_pk` is failing because 14 Quercus records have a null student ID (data quality issue in the source). Wire records this in the execution log as a known data issue and proposes adding a `where student_id is not null` filter to the staging model.

### LookML

```
/wire:lookml-generate 20240115_barton_peveril_full_platform --domain students
/wire:lookml-validate 20240115_barton_peveril_full_platform --domain students
```

Wire generates base views from the mart layer DDL, then adds the business logic specified in the Looker design document — the attendance default filter, the enrollment status dimension, and the destinations dimension group.

## Phase 4 — Testing

```
/wire:uat-test-plan-generate 20240115_barton_peveril_full_platform
```

Wire generates a UAT test plan with 47 test cases across all four data domains. Each test case specifies the test type (row count, column value, business rule), the Looker explore or dashboard to test in, the expected result, and the source system cross-reference to verify against.

The UAT is run with the college's data team. 43 of 47 cases pass first time. The four failures are:

1. Student headcount in Looker doesn't match the college's manual count for the current academic year — traced to a filter on `is_active` that should also filter by academic year
2. Finance actuals are double-counting — traced to a Fivetran sync that runs twice daily and a missing deduplication key
3. The attendance percentage calculation differs from the college's own calculation — their method excludes bank holidays; Wire's initial implementation doesn't
4. One destinations dashboard tile is blank — a `null` reference in the LookML `sql_table_name`

All four are fixed within the sprint and UAT is re-run to confirm.

## Phase 5 — Deployment

```
/wire:deployment-runbook-generate 20240115_barton_peveril_full_platform
/wire:deployment-runbook-validate 20240115_barton_peveril_full_platform
/wire:deployment-runbook-review 20240115_barton_peveril_full_platform
```

The runbook covers: BigQuery dataset creation in production, Fivetran connector activation, Cloud Function deployment via Cloud Build, dbt Cloud job configuration, and Looker production deploy. Each step has a rollback procedure.

Go-live is completed in a 2-hour maintenance window on a Saturday morning.

## Phase 6 — Enablement

```
/wire:analytics-enablement-generate 20240115_barton_peveril_full_platform
```

Wire generates user documentation for three personas: the data team (dbt and BigQuery access), data analysts (Looker power users), and business stakeholders (dashboard consumers). It also generates a data dictionary covering all 4 data domains, keyed to the mart table names and Looker explore names the college will use day-to-day.

## What the engagement produced

| Artefact | Location |
|---|---|
| Problem definition | `.wire/releases/.../problem_definition.md` |
| High-level design | `.wire/releases/.../high_level_design.md` |
| Source-to-target map | `.wire/releases/.../source_to_target_map.md` |
| dbt project | `dbt/` (44 models, 127 tests) |
| LookML | `looker/` (4 models, 9 explores, 12 dashboards) |
| Cloud Functions | `ingestion/` (2 functions, CI-deployed) |
| Deployment runbook | `.wire/releases/.../deployment_runbook.md` |
| User documentation | `.wire/releases/.../enablement/` |
| Execution log | `.wire/releases/.../execution_log.md` (38 decisions recorded) |
