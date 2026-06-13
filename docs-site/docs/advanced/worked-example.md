---
sidebar_position: 1
title: Worked Example
---

# Worked Example: Barton Peveril Live Pastoral Analytics

This walkthrough traces a complete Wire engagement from initial kick-off through delivery handover, using a real-world further education client. It covers every command in the canonical sequence and shows two Wire Agents features in practice: auto-delegation during the design phase, and batch dispatch via `/wire:delegate` at the start of development.

The engagement is a `full_platform` release using BigQuery, dbt, Looker, and Apache Airflow for orchestration.

## Engagement overview

| | |
|-|-|
| **Client** | Barton Peveril Sixth Form College, Hampshire |
| **Engagement** | Live Pastoral Analytics (SOW 2) |
| **Duration** | 2 weeks (Feb 2–13, 2026) |
| **Release type** | `full_platform` |
| **Orchestration** | Apache Airflow (college IT already runs Airflow for timetabling) |

**SOW deliverables**: Live pastoral pipeline (ProSolution + Focus → BigQuery), Looker semantic layer, SPA Operational Dashboard, data team and end-user training, technical documentation.

## Phase 1: Requirements (Day 1)

### Engagement setup

```
/wire:new
→ Client: Barton Peveril Sixth Form College
→ Engagement name: barton_peveril
→ Release type: full_platform
→ Release ID: 01-barton-peveril-live-pastoral
→ Branch: feature/barton-peveril-live-pastoral
→ .wire/releases/01-barton-peveril-live-pastoral/status.md created
  16 artifacts across 6 phases, all at not_started
```

After `/wire:new`, copy the SOW PDF and ProSolution SQL schema examples into `releases/01-barton-peveril-live-pastoral/requirements/`.

### Requirements — auto-delegated to `discovery-analyst`

```
/wire:requirements-generate 01-barton-peveril-live-pastoral
→ [auto-delegated to discovery-analyst agent]
```

The agent reads the SOW and SQL examples and produces a 13-section requirements specification: FR-1 through FR-9 with acceptance criteria, NFR-1 through NFR-7 (performance, security, freshness SLAs), and a deliverable-to-artifact mapping. It appends two entries to `decisions.md`:

- Modelled attendance at daily-snapshot grain, not register-level — register-level would require 6× the Fivetran MAR volume
- Excluded `student_notes.body` from replication scope — free-text pastoral records create a GDPR data minimisation risk

```
/wire:requirements-validate 01-barton-peveril-live-pastoral
→ [auto-delegated to discovery-analyst agent]
→ PASS

/wire:requirements-review 01-barton-peveril-live-pastoral
→ [main session — review gates stay with the consultant]
→ Fathom context: pre-engagement call transcript pulled
→ Approved by Head of MIS, 2026-02-03
```

### Delivery playbook

Before moving into design, generate a playbook for the full release:

```
/wire:playbook-generate 01-barton-peveril-live-pastoral
```

This reads the approved requirements and `status.md` and produces:

1. A Mermaid flowchart of the complete artifact sequence, colour-coded: teal for Wire commands, orange for offline activities (workshops, UAT), red for open questions that block progression. Two red gates are surfaced: OQ-1 (attendance granularity) and OQ-2 (Airflow DAG deployment access).

2. A narrative delivery playbook at `planning/barton_peveril_playbook.md` — 14 steps covering the 10-day schedule, who acts at each gate, and the inputs each phase needs from the client.

This is a planning utility — it creates no tracked artifact and blocks nothing.

## Phase 2: Design (Days 2–4)

### Conceptual model — auto-delegated to `data-designer`

```
/wire:conceptual_model-generate 01-barton-peveril-live-pastoral
→ [auto-delegated to data-designer agent]
```

Produces a business-level entity model: five domain entities (`Student`, `Attendance`, `PastoralNote`, `SPAAlert`, `Assignment`) with a Mermaid `erDiagram` showing cardinalities.

```
/wire:conceptual_model-validate 01-barton-peveril-live-pastoral
→ [auto-delegated to data-designer agent] → PASS

/wire:conceptual_model-review 01-barton-peveril-live-pastoral
→ [main session]
→ Approved by Head of MIS + Head of Student Services, 2026-02-04
→ Decision: SPAAlert is a first-class entity, not a flag on PastoralNote
```

### Pipeline design — auto-delegated to `pipeline-engineer`

```
/wire:pipeline_design-generate 01-barton-peveril-live-pastoral
→ [auto-delegated to pipeline-engineer agent]
```

Produces the full pipeline architecture document: ProSolution source schema analysis, three Fivetran replication scenarios with cost comparison, and 10 design decisions. Decision taken before review: Scenario C (Hybrid) — daily view for attendance dashboard, raw tables for drill-through.

```
/wire:pipeline_design-validate 01-barton-peveril-live-pastoral → PASS
/wire:pipeline_design-review 01-barton-peveril-live-pastoral
→ Approved 2026-02-05; scope addition: Markbook/Assignment data added to D1
```

### Data model — auto-delegated to `data-designer`

```
/wire:data_model-generate 01-barton-peveril-live-pastoral
→ [auto-delegated to data-designer agent]
```

Produces `_sources.yml` for both source schemas with freshness thresholds, 4 staging models, 5 warehouse models, a physical ERD, and cross-system join key documentation.

```
/wire:data_model-validate 01-barton-peveril-live-pastoral → PASS
/wire:data_model-review 01-barton-peveril-live-pastoral
→ Approved 2026-02-06 after one iteration
→ student_risk_summary grain changed: daily → current-state snapshot
```

### Mockups

```
/wire:mockups-generate 01-barton-peveril-live-pastoral
→ [main session — no specialist agent for wireframes]
```

Three wireframes: at-risk student list, unanswered SPA alert tracker, student detail drillthrough.

```
/wire:mockups-review 01-barton-peveril-live-pastoral
→ Approved 2026-02-06
→ Change request: add "days since last SPA contact" column
```

### End of Week 1 — close the session

All four design artifacts approved. Before switching off:

```
/wire:session:end 01-barton-peveril-live-pastoral
```

Wire summarises: 6 artifacts completed, two open items (OQ-2 still open), next session focus is Phase 3 Development, recommends starting with `/wire:delegate`.

## Phase 3: Development (Days 5–8)

### Day 5 morning — resume and plan

New session, two days later:

```
/wire:start
→ Select: 01-barton-peveril-live-pastoral
→ Choose: Plan session
```

Wire shows the release state (6/16 artifacts done), lists the next four at `not_started`, surfaces the two open items, and recommends `/wire:delegate`.

### Batch dispatch with `/wire:delegate`

```
/wire:delegate 01-barton-peveril-live-pastoral
```

Wire inspects `status.md`, identifies all development artifacts at `not_started`, and presents the delegation plan:

```
pipeline-engineer        → pipeline-generate, pipeline-validate
dbt-developer            → dbt-generate, utils-run-dbt, dbt-validate
orchestration-engineer   → orchestration-generate, orchestration-validate
semantic-layer-developer → semantic_layer-generate, semantic_layer-validate

4 agents will run in parallel. Review commands stay in this session.
```

### What the agents produce

**`pipeline-engineer`** — Fivetran connector config for ProSolution (SQL Server CDC) and Focus (REST API), plus a Cloud Function for Focus auth token refresh. Error handling: dead-letter queue to `pipeline_errors` BigQuery table, Slack alerting on consecutive failures.

**`dbt-developer`** — 9 dbt models (4 staging views, 5 warehouse tables), surrogate keys via `dbt_utils.generate_surrogate_key()`, 47 tests (not_null + unique on every PK, relationship tests on every FK). Adds to `decisions.md`:

- Used `BashOperator` not `PythonVirtualenvOperator` for dbt tasks — college Airflow already has dbt-core installed; a virtual env would add 90s per run for no isolation benefit
- `student_risk_summary` materialised as table with `full_refresh=false` — model accumulates historical snapshots; incremental would require a unique_key that changes the grain

**`orchestration-engineer`** — Generates the Airflow DAG (`dags/barton_peveril_pipeline.py`):

```python
with DAG(
    dag_id="barton_peveril_pipeline",
    schedule_interval="*/30 * * * *",  # every 30 minutes, matches NFR-3
    start_date=datetime(2026, 2, 10),
    catchup=False,
) as dag:
    prosolution_sensor = BigQueryTableExistenceSensor(
        task_id="check_prosolution_loaded", ...
    )
    focus_sensor = BigQueryTableExistenceSensor(
        task_id="check_focus_loaded", ...
    )
    dbt_run = BashOperator(task_id="dbt_run", bash_command="dbt run ...")
    dbt_test = BashOperator(task_id="dbt_test", bash_command="dbt test ...")
    [prosolution_sensor, focus_sensor] >> dbt_run >> dbt_test
```

Also produces `airflow_connections.md` and `airflow_variables.md`. Adds to `decisions.md`: set schedule to `*/30` to match the 30-minute freshness SLA in NFR-3; sensors ensure the cadence is a ceiling not a guarantee.

**`semantic-layer-developer`** — LookML views for all 5 warehouse models, risk signal measures (`attendance_deterioration_flag`, `pastoral_note_spike_flag`, `unanswered_alert_flag`), and the `pastoral_risk` explore. Includes `days_since_last_spa_contact` (fulfils the mockups change request).

### Development reviews (Days 6–8)

Review gates stay in the main session:

```
/wire:pipeline-review 01-barton-peveril-live-pastoral → Approved 2026-02-11
/wire:dbt-review 01-barton-peveril-live-pastoral → Approved 2026-02-11
/wire:orchestration-review 01-barton-peveril-live-pastoral
→ IT infrastructure lead confirms BashOperator approach
→ OQ-2 formally closed: dags/ synced via Git Sync
→ Approved 2026-02-11
/wire:semantic_layer-review 01-barton-peveril-live-pastoral → Approved 2026-02-12
```

With semantic_layer approved, generate the dashboard:

```
/wire:dashboards-generate 01-barton-peveril-live-pastoral
/wire:dashboards-validate 01-barton-peveril-live-pastoral → PASS
/wire:dashboards-review 01-barton-peveril-live-pastoral → Approved 2026-02-12
```

## Phase 4: Testing (Days 9–10)

```
/wire:data_quality-generate 01-barton-peveril-live-pastoral
→ [auto-delegated to data-quality-engineer agent]
```

Adds: 30-minute freshness Slack alert, row count reconciliation (ProSolution vs `attendance_fct`, ±2% tolerance), null rate monitoring, FK hit rate check.

```
/wire:data_quality-validate 01-barton-peveril-live-pastoral → PASS
/wire:data_quality-review 01-barton-peveril-live-pastoral → Approved 2026-02-13
```

UAT with SPAs and pastoral leads:

```
/wire:uat-generate 01-barton-peveril-live-pastoral
```

UAT plan mapped to FR-1 through FR-9. One iteration: "days since last SPA contact" needed rounding to whole days.

```
/wire:uat-review 01-barton-peveril-live-pastoral
→ Approved by Head of Student Services, 2026-02-13
```

## Phase 5: Deployment (Day 11)

```
/wire:deployment-generate 01-barton-peveril-live-pastoral
```

Generates: step-by-step deployment runbook, Airflow DAG enable instructions with Git Sync confirmation, monitoring setup, rollback procedures.

```
/wire:deployment-validate 01-barton-peveril-live-pastoral → PASS

/wire:utils-deploy-to-dev 01-barton-peveril-live-pastoral
→ 9 models built, 47 tests passing, DAG runs in dev, dashboards visible in Looker dev

/wire:deployment-review 01-barton-peveril-live-pastoral
→ IT lead + analytics lead
→ Dev results presented, runbook walked through
→ Approved 2026-02-13

/wire:utils-deploy-to-prod 01-barton-peveril-live-pastoral
→ Fivetran connectors activated
→ Airflow DAG enabled in production (Git Sync confirmed)
→ Dashboards published to Looker production
→ Monitoring alerts live
```

## Phase 6: Enablement (Days 12–13)

```
/wire:training-generate 01-barton-peveril-live-pastoral
```

**Data Team Enablement** (Day 12 morning): pipeline architecture, dbt model structure, Airflow DAG operation, LookML extension, hands-on trace of a data point from ProSolution to Looker.

**End User Training** (Day 12 afternoon): dashboard navigation, interpreting risk signals, data freshness expectations, how to raise a data quality issue.

```
/wire:training-validate 01-barton-peveril-live-pastoral → PASS
/wire:training-review 01-barton-peveril-live-pastoral → Approved 2026-02-14
```

```
/wire:documentation-generate 01-barton-peveril-live-pastoral
→ [delivery-lead agent reads all approved artifacts and decisions.md]
```

Produces: architecture overview, dbt model reference, Airflow DAG runbook, LookML field catalogue, operational runbook.

```
/wire:documentation-validate 01-barton-peveril-live-pastoral → PASS
/wire:documentation-review 01-barton-peveril-live-pastoral → Approved 2026-02-14
```

### Archive

```
/wire:archive 01-barton-peveril-live-pastoral
→ 16 artifacts, 48 generate/validate/review actions, 11 decisions.md entries
→ Jira Epic BP-1 closed
```

## What the engagement produced

| Artifact | Format |
|---|---|
| Requirements specification | `.wire/releases/.../requirements.md` |
| Delivery playbook | `.wire/releases/.../planning/barton_peveril_playbook.md` |
| Conceptual entity model | `.wire/releases/.../conceptual_model.md` |
| Pipeline design | `.wire/releases/.../pipeline_design.md` |
| Physical data model | `.wire/releases/.../data_model.md` |
| Dashboard wireframes | `.wire/releases/.../mockups.md` |
| dbt project | 9 models, 47 tests |
| Airflow DAG | `dags/barton_peveril_pipeline.py` |
| LookML | `pastoral_risk` explore, SPA Operational Dashboard |
| Technical documentation | Architecture, DAG runbook, field catalogue, ops runbook |
| Training materials | Data team session + end-user session |
| `decisions.md` | 11 agent decisions recorded across the engagement |
