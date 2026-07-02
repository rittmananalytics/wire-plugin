# dbt Audit: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Source platform**: {{SOURCE_PLATFORM}}
**dbt project path**: {{DBT_PROJECT_PATH}}

## Summary

| Component | Count |
|-----------|-------|
| Models | |
| — Buildable (`enabled=true`) | |
| — Disabled (`enabled=false`, null batch) | |
| — Simple | |
| — Moderate | |
| — Complex | |
| Sources | |
| Tests | |
| Models without tests | |
| Macros | |
| — Needing translation | |
| Seeds | |
| Snapshots | |
| Analyses | |
| Translation batches | |

## Model Distribution by Layer

| Layer | Count | Complexity Distribution |
|-------|-------|------------------------|
| Staging (stg_) | | |
| Intermediate (int_) | | |
| Mart (fct_ / dim_) | | |
| Other | | |

## Top Platform-Specific Features

| Feature Tag | Model Count | Impact |
|-------------|------------|--------|
| | | |

## Batch Plan

Batches are ordered by a manifest-derived topological sort over the model dependency graph — not a heuristic. Every model's `ref()` parents sit in an earlier-or-equal batch. Forward-reference count for this plan: {{FORWARD_REFERENCE_COUNT}} (must be 0).

| Batch | Model Count | Complexity Mix | Estimated Translation Hours |
|-------|------------|---------------|---------------------------|
| 1 | | | |
| 2 | | | |

## Macros Requiring Translation

> **⚠️ Classification caveats.** The NEEDS-translation set is a single specialist-pass read of every macro body — a floor count, not independently re-verified. Schema-qualified UDF calls in model SQL (`schema.fn_x(...)`) are invisible to the manifest's macro graph and to a macro-name text scan, so `Model Reach` figures for the UDF layer understate reality.

| Macro Name | Project | Tier | Category | Action | Model Reach |
|------------|---------|------|----------|--------|-------------|
| | | | | | |

## Batch-Zero Macro Translation Plan

Full plan: `batch_zero_plan.json` (machine-readable) and `batch_zero_macro_plan.md` (narrative). Macros with `action: translate` are rewritten in tier order — all of tier 0, then tier 1, then tier 2 — entirely before model batch 1 begins.

| Tier | Macro Count |
|------|-------------|
| 0 | |
| 1 | |
| 2 | |

| Non-translation bucket | Macro Count |
|------------------------|-------------|
| Redesign (no target equivalent — architectural decision) | |
| Manual-review, out of scope (session/catalog/dev-tooling ops) | |

## Models Without Tests

| Model | Layer | Risk Note |
|-------|-------|----------|
| | | |

## Notes

[Add any specific findings about the dbt project here. Record: forward-reference count from the batch sort; whether the manifest or the text-scan fallback was used (fallback = medium confidence); that the macro classification is a single specialist-pass read; any models found on disk but absent from the manifest.]
