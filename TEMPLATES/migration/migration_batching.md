# Migration Batching: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Source → Target**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}

> **CANDIDATES, NOT DECISIONS.** This is a proposed partition of the migration inventory into domain batches, derived from the real dependency graph. No batch is approved, final, or scheduled. Batch composition, target dates, and owners are decided at `/wire:migration-batching-review` — until that gate runs, this artifact is not authoritative for scheduling.

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

## Batch-Zero Macro Dependency

The following batches contain models with non-empty `platform_macros` (from `audit/dbt_audit.csv`) and therefore cannot start until the batch-zero macro translation pass (`audit/batch_zero_plan.json`) is complete:

| Batch | Affected models | Macros |
|-------|----------------|--------|
| {{BATCH_ID}} | {{MODEL_COUNT}} | {{MACRO_NAMES}} |

## Notes

[Merges forced by bidirectional edges, grouping-signal decisions, and anything the reviewer should weigh at adjudication.]
