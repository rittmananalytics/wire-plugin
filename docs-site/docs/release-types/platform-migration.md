---
sidebar_position: 11
title: Platform Migration
---

# Platform Migration Release

The Platform Migration release type covers the full lifecycle of migrating a data platform from one warehouse stack to another. It supports bidirectional BigQuery ↔ Snowflake migrations and introduces two structural features: a two-zone artifact model and an iterative equivalency loop.

**Supported platform pairs**: `bigquery_to_snowflake`, `snowflake_to_bigquery`

## Artifact zones

**Audit zone** — read-only analysis of the source platform. No writes to any external system.

| Artifact | Command | Purpose |
|---|---|---|
| `ingestion_audit` | `/wire:ingestion-audit-*` | Catalog all Fivetran connectors, sync configs, column selections |
| `db_object_audit` | `/wire:db-object-audit-*` | Enumerate databases, schemas, tables, views, procedures |
| `security_audit` | `/wire:security-audit-*` | Catalog roles, permissions, users, service accounts |
| `dbt_audit` | `/wire:dbt-audit-*` | Catalog dbt models, classify by migration complexity |
| `orchestration_audit` | `/wire:orchestration-audit-*` | Catalog orchestration jobs, schedules, and dependencies |
| `migration_inventory` | `/wire:migration-inventory-*` | Synthesise all five audits into a unified catalogue |

**Migration zone** — writes to the target platform. Safety-gated commands require explicit confirmation.

| Artifact | Safety gate | Purpose |
|---|---|---|
| `migration_strategy` | No | Platform-pair translation decisions, phasing, rollback |
| `target_setup` | **Yes** | Target warehouse config, schemas, roles, service accounts |
| `ingestion_migration` | **Yes** | Reconfigure/replicate Fivetran connectors to target platform |
| `dbt_migration` | No | Translate dbt models batch by batch to target dialect |
| `orchestration_migration` | **Yes** | Recreate orchestration jobs on target platform |
| `equivalency_validation` | No (loop) | Iterative row-count, schema, value, freshness comparison |
| `cutover` | **Yes** | Go-live runbook — point of no return |
| `migration_report` | No | Post-migration record |

## Setting up a Platform Migration release

Run `/wire:new` and select **Platform Migration**. You will be asked five additional questions:

1. **Source platform** — BigQuery or Snowflake
2. **Target platform** — must differ from source
3. **dbt project path** — relative to repo root
4. **Orchestration tool** — Dagster, dbt Cloud, Airflow, or None
5. **Connectivity** — public endpoint or private network requiring an MCP tunnel

## Audit zone: parallel by default

```
/wire:migration-audit-all <release-folder>
```

This fans out five subagents simultaneously. Before launching, you will see a token cost confirmation with options to run in parallel or sequentially.

## dbt audit and complexity classification

`dbt-audit-generate` reads every `.sql` model file and assigns a complexity rating:

| Rating | Criteria |
|---|---|
| `trivial` | No platform-specific features; view or table materialization |
| `low` | 1–2 platform-specific functions with direct target equivalents |
| `medium` | 3+ platform-specific functions, OR incremental materialization |
| `high` | Nested/repeated field logic, complex incremental strategies |
| `blocked` | Depends on an out-of-scope object, OR uses a feature with no known target equivalent |

## dbt migration: batched processing

```
/wire:dbt-migration-generate <release-folder>            # next pending batch
/wire:dbt-migration-generate <release-folder> --batch 3  # specific batch
/wire:dbt-migration-generate <release-folder> --model stg_salesforce__accounts  # single model
```

Each model gets one of three translation treatments:
- **auto-translate**: Mechanical syntax substitution applied with high confidence
- **guided-translate**: Non-trivial dialect difference — translated then flagged with `-- WIRE:REVIEW`
- **rewrite**: Logic tightly coupled to source platform features — flagged with `-- WIRE:REWRITE`

## Equivalency validation loop

Once data is flowing into both platforms:

```
/wire:equivalency-validate <release-folder>
```

Each run performs five check types: row count, schema, value, freshness, and dbt tests. When a check fails:

```
/wire:equivalency-investigate <release-folder> --object carwow_sales.fct_orders
/wire:equivalency-fix <release-folder> --object carwow_sales.fct_orders --approach "Update TIMESTAMP_DIFF translation"
```

`cutover-generate` is blocked until `checks_failing: 0`.

## Safety gates

Four commands require explicit confirmation before proceeding:
- **`target-setup-review`** — confirms DDL scripts have been reviewed, target environment is isolated, client has approved in writing
- **`ingestion-migration-review`** — confirms target landing schemas are ready, parallel running window is agreed
- **`orchestration-migration-review`** — confirms all orchestration jobs have been reviewed
- **`cutover-review`** — the point of no return. Requires all equivalency checks passing, written client sign-off, rollback window agreed

## Full command sequence

```
/wire:new                                            # release_type: platform_migration

# ── AUDIT ZONE (read-only) ──────────────────────────────────────
/wire:migration-audit-all <release>

# Per-audit validate + review gates
/wire:ingestion-audit-validate <release>
/wire:ingestion-audit-review <release>
/wire:db-object-audit-validate <release>
/wire:db-object-audit-review <release>
/wire:security-audit-validate <release>
/wire:security-audit-review <release>
/wire:dbt-audit-validate <release>
/wire:dbt-audit-review <release>
/wire:orchestration-audit-validate <release>
/wire:orchestration-audit-review <release>

# Synthesis — requires all five audits approved
/wire:migration-inventory-generate <release>
/wire:migration-inventory-validate <release>
/wire:migration-inventory-review <release>

# ── MIGRATION ZONE ──────────────────────────────────────────────
/wire:migration-strategy-generate <release>
/wire:migration-strategy-validate <release>
/wire:migration-strategy-review <release>

# ⚠ SAFETY GATE
/wire:target-setup-generate <release>
/wire:target-setup-validate <release>
/wire:target-setup-review <release>

# ⚠ SAFETY GATE
/wire:ingestion-migration-generate <release>
/wire:ingestion-migration-validate <release>
/wire:ingestion-migration-review <release>

# dbt migration — batched; repeat for each batch
/wire:dbt-migration-generate <release>
/wire:dbt-migration-validate <release>
/wire:dbt-migration-review <release>

# ⚠ SAFETY GATE
/wire:orchestration-migration-generate <release>
/wire:orchestration-migration-validate <release>
/wire:orchestration-migration-review <release>

# Equivalency loop — repeat until checks_failing == 0
/wire:equivalency-validate <release>
/wire:equivalency-investigate <release> --object <table_or_model>
/wire:equivalency-fix <release> --object <table_or_model>

# ⚠ SAFETY GATE — point of no return
/wire:cutover-generate <release>
/wire:cutover-validate <release>
/wire:cutover-review <release>

/wire:migration-report-generate <release>
/wire:migration-report-validate <release>
/wire:migration-report-review <release>

/wire:archive <release>
```
