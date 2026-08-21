# Migration Batching: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Source → Target**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}

> **CANDIDATES, NOT DECISIONS.** This is a proposed partition of the migration inventory into domain batches, derived from the real dependency graph. No batch is approved, final, or scheduled. Batch composition, target dates, and owners are decided at `/wire:migration-batching-review` — until that gate runs, this artifact is not authoritative for scheduling.

## Partition Mode

**Mode**: {{PARTITION_MODE}} (`domain`, `build_ordered_waves`, or `readiness_waves`)

[Domain mode: "One batch per domain group; the domain dependency graph is a viable acyclic DAG." Build-ordered mode: state the SCC evidence — the domains form a single strongly-connected component (SCC count / largest-SCC size vs domain count), so no domain grouping can be both acyclic and declare every cross-batch edge. The partition of record is therefore build-ordered waves: a topological sort of the model graph cut into {{WAVE_COUNT}} waves, each depending on the full prefix of earlier waves. The `domain` column is retained on every row for client/milestone rollup, but it is not the build order. Readiness mode: state the selection basis (`migration.scope: tenant_carveout` plus `migration.parent_release`, or the `--partition-mode` override) and that waves are readiness bands: B00 shipped history, ready, one gated wave per approval group, waiting on parent, residue, plus the PEN-UNRESOLVED and PEN-EXCLUSION-PENDING holding pens.]

## Seed Reconciliation

**Seed plan**: {{SEED_PATH_OR_NONE}}

[What was kept from the seed, what changed and why — including every group merge forced by the graph. Or: "No seed provided — groupings are pure graph-derived."]

## Batch Summary

| Batch | Name | Domain | Objects | Effort (hrs) | Depends on | Batch-zero prerequisite |
|-------|------|--------|---------|--------------|------------|------------------------|
| {{BATCH_ID}} | {{BATCH_NAME}} | {{DOMAIN}} | {{OBJECT_COUNT}} | {{EFFORT_HOURS}} | {{DEPENDS_ON_BATCHES}} | {{YES_NO}} |

[Note any size outliers and why — a small foundational batch that blocks many others matters more for scheduling than its own hours.]

## Batch Dependency DAG

```mermaid
flowchart LR
  {{BATCH_ID}}["{{BATCH_ID}} {{BATCH_NAME}}"]
  %% one node per batch, one edge per batch dependency (prerequisite --> dependent)
```

## Parallel-Safe Groupings

Batches within a group have zero dependency edges (either direction) between their member objects and can be scheduled in parallel.

| Group | Batches | Basis |
|-------|---------|-------|
| {{GROUP_ID}} | {{BATCH_IDS}} | {{ZERO_EDGE_CONFIRMATION}} |

## Readiness Bands

*Readiness mode only: omit this section entirely in the other modes.*

| Band | Wave(s) | Models | What unlocks it |
|------|---------|--------|-----------------|
| Shipped (history) | B00 | {{COUNT}} | Nothing: already on the client's main. Preserved across re-runs |
| Ready | {{WAVE_IDS}} | {{COUNT}} | Nothing: rules ruled, parent merged. Split: {{SELF_CONTAINED_COUNT}} approved self-contained, {{RIDER_COUNT}} no-approval riders |
| Gated: {{GROUP_LABEL}} | {{WAVE_ID}} | {{COUNT}} | Client approval of the rule: `{{RULE_TEXT}}` (record via `region-tagging-review` or a `resolved_by: manual` registry edit, then re-run) |
| Waiting on parent | {{WAVE_ID}} | {{COUNT}} | Parent-release translations merging on the client's main (evidence: {{LIVE_READ_OR_REGISTER}}) |
| Residue | {{WAVE_ID}} | {{COUNT}} | Pen resolutions and/or multiple approvals: pen readers and mixed-gate closures |
| PEN-UNRESOLVED | (pen) | {{COUNT}} | A carve mechanism being established for each item |
| PEN-EXCLUSION-PENDING | (pen) | {{COUNT}} | A rescope of each `defer`/`split`-ruled item |

[List models with no parent register row (not parent-gated; authored in this release), any prior-B00 rows kept despite a register discrepancy, and any rider chains terminating in an unresolved row (registry defects).]

### Cutover partition (secondary view)

*Wave modes only (build-ordered and readiness) — omit this section entirely in domain mode.*

Build order (the waves above) and cutover/domain order **diverge** here: in build-ordered mode the SCC fallback fired precisely because no domain grouping could stay acyclic and declare every cross-batch edge; in readiness mode the waves are readiness bands. Either way the waves are not domain-coherent. This table is the domain-grouped rollup for client communication and milestone planning — it is **not** required to be acyclic or edge-complete, unlike the wave partition; it does not feed `depends_on_batches`, size balancing, or the parallel-safe analysis above.

| Domain | Object count | Wave(s) its objects landed in |
|--------|--------------|-------------------------------|
| {{DOMAIN}} | {{OBJECT_COUNT}} | {{WAVE_IDS}} |

[Name explicitly which domains end up spread across the most waves, so nobody mistakes a wave number for this grouping.]

## Batch-Zero Macro Dependency

The following batches contain models with non-empty `platform_macros` (from `audit/dbt_audit.csv`) and therefore cannot start until the batch-zero macro translation pass (`audit/batch_zero_plan.json`) is complete:

| Batch | Affected models | Macros |
|-------|----------------|--------|
| {{BATCH_ID}} | {{MODEL_COUNT}} | {{MACRO_NAMES}} |

## NO-DEP — No Model Dependency (Human Triage Required)

**Count**: {{NO_DEP_COUNT}} objects (state 0 explicitly if none)

Objects below have no real graph edge to any model — no `source()` reference or other consumer found anywhere in the buildable graph. They are **not** defaulted into wave/batch 1 or any other batch; they sit here until a reviewer decides to decommission, later-wave, or hand-confirm each one as genuinely foundational at `/wire:migration-batching-review`.

| Object | Type | Source audit | Notes |
|--------|------|--------------|-------|
| {{OBJECT_ID}} | {{OBJECT_TYPE}} | {{SOURCE_AUDIT}} | {{WHY_NO_CONSUMER_FOUND}} |

## Notes

[Merges forced by bidirectional edges, grouping-signal decisions, and anything the reviewer should weigh at adjudication.]
