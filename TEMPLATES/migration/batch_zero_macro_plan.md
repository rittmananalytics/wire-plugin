# Batch-zero macro translation plan — {{RELEASE_FOLDER}} ({{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}})

Companion to `batch_zero_plan.json`. Migration input for the {{RELEASE_FOLDER}} release.

> **⚠️ PROVISIONAL — {{VERSION}}. Not final. Do not treat as authoritative until the caveats below are closed.**
>
> - **One specialist read (floor {{FLOOR_COUNT}}).** The NEEDS-translation set is a single specialist-pass read of every macro body — count-verified and impact-joined, but not independently re-read line-by-line. A few borderline items could reclassify.
> - **UDF model-reach is under-traced.** UDFs are called `schema.fn_x(...)` in models, which neither the manifest's macro graph nor a macro-name scan captures. Every UDF-layer `model_reach` figure understates reality.
> - **{{MANUAL_EDGES_NOTE}}** (any dependency edges added manually because schema-qualified UDF calls are invisible to the scan — state which, or "None").

The macro layer is translated as a **batch-zero pass, before model batch 1**. A widely-used macro can be expanded by hundreds of models scattered across every translation batch, so it cannot sit "in" a model batch — it must be rewritten up front, once, so every model downstream compiles against an already-translated macro.

Scope: **{{NEEDS_TRANSLATION_COUNT}} of {{TOTAL_MACRO_COUNT}}** macro definitions need {{SOURCE_PLATFORM}}→{{TARGET_PLATFORM}} translation. {{TIER_BREAKDOWN_SENTENCE}}. Two further buckets are handled outside the translation pass ({{REDESIGN_COUNT}} redesign, {{MANUAL_REVIEW_COUNT}} manual-review).

## Tiers

Tier is the macro-to-macro dependency depth within the NEEDS set — a macro must be translated *after* any NEEDS macro it calls, so the translated version exists when it's referenced.

- **Tier 0 ({{TIER_0_COUNT}})** — leaf macros with no NEEDS-macro dependencies. Translate in any order.
- **Tier 1 ({{TIER_1_COUNT}})** — depend only on tier 0.
- **Tier N ({{TIER_N_COUNT}})** — depend only on tiers <N. (Add a row per tier present.)

**The rule:** translate all of tier 0 (any order, parallelisable), then all of tier 1, then tier 2, and so on — all before model batch 1 begins.

## Dependency chains

Describe each chain that produces the tier-1+ macros — the composition paths everything above tier 0 sits on:

1. **{{CHAIN_1_NAME}}:** {{CHAIN_1_DESCRIPTION}} (e.g. `fn_helper__*` (tier 0) → `fn_parse_ppc_names` (tier 1) → `create_udfs` (tier 2)). Note any edges added manually because schema-qualified UDF calls are invisible to the scan.
2. **{{CHAIN_2_NAME}}:** {{CHAIN_2_DESCRIPTION}}

{{CYCLES_STATEMENT}} (state "No cycles", or list any found — a cycle is a validation FAIL).

## Non-translation buckets (outside the pass)

- **Redesign — no {{TARGET_PLATFORM}} equivalent ({{REDESIGN_COUNT}}):** {{REDESIGN_MACRO_LIST}}. These need an architectural decision, not a dialect translation. Surface at the human review gate.
- **Manual-review, out of scope ({{MANUAL_REVIEW_COUNT}}):** {{MANUAL_REVIEW_MACRO_LIST}}. These are {{SOURCE_PLATFORM}} session/catalog/dev-tooling operations (e.g. `ALTER SESSION`, external-table refresh, clone/drop schema), not model-build SQL. They don't belong in the batch-zero translation pass and have no {{TARGET_PLATFORM}} equivalent as written.

## Categories (best-effort tag)

Derived from detected constructs plus name pattern — coarse for multi-construct macros:

| Category | Count |
|---|---|
| {{CATEGORY_1}} | {{CATEGORY_1_COUNT}} |
| {{CATEGORY_2}} | {{CATEGORY_2_COUNT}} |

## Caveats

- **One specialist read, count-verified not re-read.** The NEEDS classification is a single specialist-pass read of every macro body, count-verified and impact-joined but not independently re-read line-by-line. A few borderline items could reclassify; the floor is **{{FLOOR_COUNT}}**.
- **UDF model-reach is under-traced.** UDFs deploy as SQL functions called `schema.fn_x(...)` in models, which the macro graph and macro-name scan do not capture. `model_reach` counts for the UDF layer (and any auto-derived UDF dependency edges) understate reality — treat them as floors, and record any edges added by hand.
