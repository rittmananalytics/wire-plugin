---
sidebar_position: 11
title: "Tutorial: Tenant Carve-out"
---

# Tutorial: Tenant Carve-out

This walkthrough covers the **tenant carve-out** variant of a platform migration — extracting a single tenant's data from a shared Snowflake platform into a dedicated BigQuery project, rather than migrating the whole platform. It assumes you know the standard migration flow from the [Platform Migration tutorial](./platform-migration); here we focus only on what the carve-out adds.

The carve-out is a variant, not a separate release type. Audits, inventory, strategy, dbt migration, equivalency, and cutover all run as normal. Four extra commands and some tenant scoping make the difference.

## Statement of Work

```
**Rittman Analytics × Meridian Retail**
**Engagement**: Regional-tenant carve-out, Snowflake → BigQuery
**Type**: Fixed price, staged

Meridian Retail runs a shared multi-tenant Snowflake platform. One regional
business unit (`tenant_id = 1042`) is being divested and must move to its own
BigQuery project, isolated from every other tenant's data. The carve-out
covers ~3 years of history. Reporting is on Metabase.

Stage 1 deliverables (gated, part-paid): region tagging, and the GDPR /
data-residency assessment including a legal review of the historical window.
```

## Setting up the carve-out

At `/wire:new`, choose **Platform Migration**, then answer the scope question:

```
Migration scope?
  1. Full migration (default)
  2. Tenant carve-out
> 2

Tenant predicate (the WHERE clause / tenant key that scopes the tenant):
> tenant_id = 1042

Reporting / BI tool?  > Metabase
```

This writes to `status.md`:

```yaml
migration:
  scope: tenant_carveout
  tenant_predicate: "tenant_id = 1042"
  reporting_tool: metabase
```

Every migration command now reads `migration.scope`. With `full_migration` (or the field absent) nothing below changes. With `tenant_carveout` the predicate threads through equivalency and the security chain, and the four carve-out commands become part of the flow.

One branching note before you start cutting branches: `01-tenant-carveout` tracks a moving parent migration release, so sync it with periodic `git merge <parent-branch>` rather than rebase, and once you've cut a per-batch branch from it, don't rebase-and-force-push the carve-out branch — that orphans the batch branch by moving the commit its merge-base points at. See [Branching strategy](../release-types/platform-migration#branching-strategy) for the full reasoning.

## Step 1 — Region tagging (after the audits)

Once the five audits are approved, classify every in-scope item by whether it belongs to the regional tenant being carved out.

```
/wire:region-tagging-generate 01-tenant-carveout --region north
```

This reads the audit CSVs and writes `migration/region_tags.csv`, sorting each item into one of three buckets:

| Bucket | Signal | Example |
|---|---|---|
| confident-region | name suffix / destination / WHERE-clause match | `stg_orders_north`, a sync to the regional Salesforce |
| shared-row-level | carries the tenant key but serves all tenants | `dim_customers` keyed by `tenant_id` |
| global-deferred | no market tag at all | `dim_date`, currency reference tables |

The command produces **candidates, not decisions** — it never emits an include/exclude flag and never removes anything. Validation confirms all three buckets are populated and every in-scope item is classified exactly once:

```
/wire:region-tagging-validate 01-tenant-carveout
✓ Check 1 — all three buckets populated
✓ Check 2 — 412 in-scope items, each classified exactly once
```

`-review` is the human adjudication gate. The reviewer works the pile — every shared-row-level item gets a lineage trace and a row sample, then a ruling: carve in (with the row-level predicate), split, or defer.

```
/wire:region-tagging-review 01-tenant-carveout
```

## Step 2 — Data-residency assessment (alongside strategy)

This is the Stage 1 contractual deliverable. RA prepares it **as data processor** — it structures the GDPR and residency questions and the legal review of the ~3-year window, and flags every legal determination for the client's DPO.

```
/wire:data-residency-assessment-generate 01-tenant-carveout
```

`data_residency_assessment.md` leads with a processor-not-counsel banner, then: GDPR scope and lawful basis, residency constraints for the target region, the historical-window review, the processor safeguards RA implements, and a consolidated list of `[CLIENT DPO/LEGAL]` items. RA does not assert the lawful basis — `-validate` fails if it does, or if the required-client-input section is empty:

```
/wire:data-residency-assessment-validate 01-tenant-carveout
✓ all seven sections present and non-empty
✓ processor-not-counsel framing present
✓ lawful basis and retention ruling flagged [CLIENT DPO/LEGAL], not asserted
```

`-review` is the client DPO/legal sign-off gate. RA cannot self-approve — the lawful basis and the retention ruling on the historical window are the controller's to make.

## Step 3 — Metabase reporting layer

Because `reporting_tool: metabase`, audit and migrate the reporting layer alongside the warehouse work.

```
/wire:metabase-audit-generate 01-tenant-carveout
/wire:metabase-migration-generate 01-tenant-carveout
```

The audit catalogues collections, dashboards, cards (with their SQL), database connections, and permission groups. The migration translates native-SQL card dialect to BigQuery, remaps permission groups, validates on a throwaway decoy collection against a frozen baseline, then repoints the Metabase database connection from Snowflake to BigQuery in two stages with per-stage rollback. It will not run without a client-supplied query inventory.

## Step 4 — Bulk copy, in place of re-ingestion

A carve-out copies the tenant's existing history rather than re-ingesting it. `bulk-copy-migration` replaces `ingestion-migration` in the flow.

```
/wire:bulk-copy-migration-generate 01-tenant-carveout
```

The runbook copies each in-scope table via the BigQuery Data Transfer Service or a GCS-staged path, every extract filtered by `tenant_id = 1042`. It runs under a service account scoped to the tenant's target project only, with a tenant guard that refuses any extract missing the predicate or pointed at a production project. The copy is two-stage with an equivalency gate between:

```
Stage 1 — pilot partition (one month) → equivalency check 1 (row count) + check 6 (checksum)
          gate: both pass, tenant-scoped, on source and target
Stage 2 — remainder
```

`-review` is a safety gate: written approval authorises the first copy execution, Stage 1 only.

## Step 4a — dbt model relocation, when the carve-out is staged after its parent migration

Meridian's carve-out above runs **alongside** the parent Snowflake→BigQuery migration — the tenant's dbt models still need translating, so `dbt-migration` stays in the sequence exactly as shown in Step 4 above and the "Where the carve-out lands" diagram below.

A different, common shape: the carve-out is scoped as a **second release, after the parent platform migration has already landed** — the whole estate is already on BigQuery, and the tenant's dbt models are already correct, already-translated target-dialect SQL sitting in the parent release's dbt repo. Re-running `dbt-migration`'s translate-and-equivalency loop against SQL that's already correct is pointless work re-deriving the same answer. This is where `dbt-carveout-relocate` replaces `dbt-migration` in the sequence — it relocates the already-correct SQL into the carve-out's own dbt project instead of re-translating it, injecting the tenant row filter only where a model is genuinely shared:

```
/wire:dbt-carveout-relocate-generate 02-tenant-carveout --wave B01 \
    --source-dbt-project-path ../01-lift-and-shift/dbt \
    --target-dbt-project-path ../tenant-north-dbt \
    --target-project meridian-north-data-playground
```

For each model in the wave, it reads the bucket `region-tagging-review` adjudicated it into (`migration/region_tags_adjudicated.csv`, filtered to `adjudicated_ruling: carve_in`):

- **`confident-region`** (tenant-exclusive, e.g. `stg_orders_north`) — the `.sql` and its companion schema YAML are copied unchanged.
- **`shared-row-level`** (e.g. `dim_customers`) — copied, then `WHERE tenant_id = 1042` is injected into the model's outermost `SELECT`. Where the injection point isn't clean — a top-level `UNION`, no single top-level `SELECT` — the model is copied unmodified and flagged `manual_review_required` rather than guessed.

```
/wire:dbt-carveout-relocate-validate 02-tenant-carveout --target-dbt-project-path ../tenant-north-dbt
✓ Check 1 — every carve_in model has a relocated file
✓ Check 2 — every shared-row-level model's file independently re-derives the predicate
✓ Check 3 — no confident-region model carries an unexpected predicate
✓ Check 5 — target project compiles cleanly
```

Check 2 re-reads the relocated file's own text rather than trusting the generate run's manifest — the same "re-derive, don't trust the report" posture `dbt-audit-validate` and `migration-batching-validate` use elsewhere. `-review` is the human approval gate: it blocks on any unresolved `manual_review_required` model, and presents a diff sample of the injected predicates so the reviewer confirms them by eye, not just by check result.

```
/wire:dbt-carveout-relocate-review 02-tenant-carveout
```

Run this once per environment — playground first, then production once playground equivalency passes, by re-running `-generate` with `--target-project meridian-north-data-source` (or wherever production resolves).

## Step 5 — Logical-access UAT (before cutover)

Before cutover, prove the isolation actually holds.

```
/wire:logical-access-uat-generate 01-tenant-carveout --region north
```

The plan derives its tests from the IAM boundaries in `target_setup_scripts/04_security.sql` — tenant-scoped grants, the RLS predicate, the scoped service account, PII masking. Every boundary gets a positive test and at least one negative test:

```
| Test | Boundary | Role | Type | Expected |
| T-04 | tenant grant | tenant_north_analyst | negative | query another tenant's project → permission denied |
| T-07 | RLS predicate | tenant_north_analyst | negative | shared table → only this tenant's rows, zero other-tenant rows |
```

`-validate` is strict: it fails unless every IAM boundary in `04_security.sql` has at least one negative test.

```
/wire:logical-access-uat-validate 01-tenant-carveout
✓ every IAM boundary has ≥1 negative test
```

`-review` executes the matrix, captures evidence, and takes the three-attestation sign-off. A negative test that returns another tenant's data fails the gate regardless of how many positives pass, and routes back to `target-setup` to fix the boundary.

## How equivalency changes

You do not run a different equivalency command. The existing checks gain the tenant predicate on both source and target, so the carve-out validates only the carved-out tenant's rows. Row count, value sampling, freshness, checksum, and aggregate control totals all scope to `tenant_id = 1042`. Schema stays structural and unchanged — there is no row data for a predicate to act on. No new check types were added.

## Where the carve-out lands in the sequence

```
audits → region-tagging → inventory
       → strategy + data-residency-assessment
       → target-setup (tenant-scoped GRANTs + RLS in 04_security.sql)
       → bulk-copy-migration   (in place of ingestion-migration)
       → dbt-migration → metabase-migration
       → equivalency (tenant-scoped)
       → logical-access-uat → cutover → migration-report
```

If the carve-out is staged **after** its parent migration has already landed (Step 4a), `dbt-carveout-relocate` takes `dbt-migration`'s place in that line — everything else in the sequence is unchanged:

```
       ...
       → bulk-copy-migration   (in place of ingestion-migration)
       → dbt-carveout-relocate (in place of dbt-migration) → metabase-migration
       → equivalency (tenant-scoped)
       ...
```

Everything not listed here runs exactly as in the standard [Platform Migration tutorial](./platform-migration).
