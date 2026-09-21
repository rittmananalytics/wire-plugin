---
description: Run equivalency checks across all in-scope tables (parallel fan-out)
argument-hint: <release-folder> [--batch N 
---

# Run equivalency checks across all in-scope tables (parallel fan-out)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'equivalency-validate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: validate
artifact: equivalency
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Run equivalency checks across all in-scope tables (repeatable loop, lane-based parallel fan-out, taxonomy verdicts, optional frozen-baseline tier-3 mode)
argument-hint: <release-folder> [--batch N | --wave id | --snapshots [names]] [--baseline] [--run-point standard|pre_raise|post_merge_prod]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before running any queries, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  All queries against the source platform are SELECT only.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, or DROP against the source.

Target reads from: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If any check query would write to a source platform or production project, stop and report the conflict.

---

# Equivalency — Validate

## Purpose

This is a repeatable loop command — not a standard generate/validate/review artifact. It runs all seven check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum, business invariants) across all in-scope migration objects, updates the equivalency tracking block in status.md, and unblocks the cutover command when `checks_failing == 0`.

Each invocation adds a new entry to `equivalency_validation.loop_history` in status.md, preserving the full audit trail of every run.

## Prerequisites

- `orchestration_migration review: approved`
- Target platform has data (Fivetran connectors have completed at least one sync)

## Behaviour

This command can be run as many times as needed. There is no "approved" state — the loop continues until equivalency passes or the team decides to proceed to cutover despite known failures (requires explicit override).

For a BigQuery-side query anywhere below, route it through `specs/utils/bigquery_mcp_fallback.md` (`operation: read`) on a connection failure rather than failing the check — a BigQuery MCP outage is not itself an equivalency failure, and must not be reported as one.

## Verdict taxonomy

Every object gets one verdict per run, not a bare PASS/FAIL. The classification is deterministic (tests mirror it: `wire/tests/platform_migration/validate_verdict_taxonomy.py`). Inputs: did any check diverge, and what named mechanism was the divergence drilled to.

| Verdict | Rule |
|---|---|
| `pass` | No check diverged. |
| `pass_qualified` | Divergence whose named mechanism is on the pair's benign allow-list (e.g. a type widening in `type_translation_allowlist`). |
| `pass_declared_deviation` | Divergence fully accounted for by a declared-deviation record (Step 1f2): the target is right, the source is provably wrong, and the upstream fix is tracked. Claimable **only** when the record's direction and magnitude account for the entire delta; a partial match is not this verdict. |
| `diff_vintage` | Divergence explained by data vintage: the two sides reflect different load instants. Claiming it requires a matched-vintage re-run (pin both sides to the same instant) that passes, or is scheduled and referenced. |
| `diff_availability` | Divergence explained by source data that has not landed on the target (e.g. history not yet copied). Where the object carries a **declared window** (Step 1e), the verdict binds to it: mechanism `declared_window_availability`, with the window's floor/cap/exclusions as structured fields on the verdict row — and it is claimable **only** when the in-window comparison passes exactly. |
| `diff_schema_type` | Divergence explained by a type-translation difference beyond the allow-list, drilled to the exact column and cast. |
| `fail` | Divergence with no named mechanism, or a mechanism that indicates a translation defect. |

**Explanations qualify a fail — they never upgrade it to a pass.** A prose explanation with no named mechanism is still `fail`. A named mechanism earns the matching `diff_*` verdict; only the pair's allow-list earns `pass_qualified`. Verdicts bind to the exact `file_version` (the model's `last_migrated_commit`): re-translating a model voids its verdict.

**How verdicts count.** For `checks_failing` and the cutover gate: `pass`, `pass_qualified`, and `pass_declared_deviation` count as passing; `fail` and every `diff_*` count as failing until a formal acceptance is recorded for that object (the existing "accepted differences formally documented" path), after which the object counts as accepted, not passing. For `dbt-migration-batch-raise` eligibility, see that command's gate table — models whose output leaves the warehouse require an exact `pass`.

## Verdict bar

Counts alone are triage, never a verdict. A `pass` requires, per object: row counts at the object's declared grain (distinct-key counts, not bare `COUNT(*)`), schema in source ordinal order, a surrogate-key or row-hash aggregate over the compared window, and a **declared method class** (`full_history`, `windowed_event` for event models compared over a shared exact window, `aggregate_only` where row-level comparison is impracticable — record why, `expected_empty` where both sides measured zero rows and the model carries the relocate-stamped expected-empty marker: the both-sides-empty gate in Step 2 governs when this class is claimable). Every divergence is drilled to a named mechanism before the verdict is written; "small diff, looks fine" is not a mechanism.

## Run points

`--run-point` records **when in the delivery pipeline** the comparison ran; default `standard`. The checks themselves do not change — what changes is scope defaults, what the verdict updates, and who invokes it:

- `standard` — the normal loop (this command, run directly). Updates `last_equivalence_*` in the register.
- `pre_raise` — invoked by `dbt-migration-batch-raise` over a candidate batch before the PR is opened: a smoke comparison of the branch-built scratch relations against source. Updates `last_equivalence_*`.
- `post_merge_prod` — invoked by `equivalency-post-merge-verify` over merged models: production target tables against source, at the full verdict bar. Never updates `last_equivalence_*`; a `pass`/`pass_qualified` advances `delivery_stage` to `production_verified` (merge rule 5 in `specs/migration/equivalency/verdict_schema.md`).

Every verdict row carries its run point into the verdict log, so "verified before raise" and "verified in production" stay distinct assurance states.

## Workflow

### Step 1: Load scope

Read the list of in-scope tables and dbt models from `migration/migration_inventory.md`. This is the full check scope.

**Scope by batch (optional).** With `--batch N`, restrict the scope to the objects in migration batch `N` (the batch groupings from `migration_strategy` / `dbt_audit.csv`). This lets equivalency fan out and run per batch — validate batch 1 as soon as its models reach terminal state, rather than waiting for the whole estate. Without `--batch`, the scope is every in-scope object. The run metadata (Step 5) records which batch a run covered.

**Scope by wave (optional).** With `--wave <id>`, restrict the scope to every object `migration/migration_batching.csv` assigns to that wave — the authoritative execution schedule, not `dbt_audit.csv`'s topological micro-batches, and not restricted to dbt models: a wave's connectors, warehouse objects, dbt models, orchestration jobs, and reverse-ETL syncs are all in scope together, matching how `migration-batching-generate` groups them as one independently-schedulable slice. Resolution is identical to `dbt-migration-generate`'s Step 1w (normalise the wave id, load `migration_batching. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).csv`, filter to `batch_id`) except it does **not** filter by `object_type` — every object type in the wave is included. `--batch` and `--wave` read different numbering schemes and cannot be combined — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.` The run metadata (Step 5) records which wave a run covered.

**Scope by snapshot (optional).** With `--snapshots`, restrict the scope to the snapshot object-type nodes and run **only check type 9** (the snapshot three-layer gate) over them — skipping every other check type. `--snapshots` (bare) selects every snapshot object-type node (`object_type = snapshot` in the migration inventory / register, cross-referenced to `audit/dbt_snapshots.csv`); `--snapshots name1,name2` only the named snapshots. Selection resolves against the snapshot object-type rows, never the model selector — a name that resolves to a model but not a snapshot node is listed as unresolved (`[wire] --snapshots: "<name>" is not a snapshot object-type node — check audit/dbt_snapshots.csv.`) and an empty resolved set aborts with `[wire] No snapshots matched --snapshots. Aborting.`. This is the retrofit companion to `dbt-migration-generate --snapshots` / `dbt-migration-validate --snapshots` — validate the snapshot gate on its own without re-running the whole estate. Normal `--batch`/`--wave` runs still run check type 9 over any in-scope snapshot inline; `--snapshots` is an additional targeted scope. Standalone scope — abort if combined with `--batch`, `--wave`, `--model`, `--models`, `--select`, `--exclude`, or `--macros`: `[wire] --snapshots is a standalone scope. Run it on its own; do not combine with --batch/--wave/--model/--models/--select/--exclude/--macros.` The run metadata (Step 5) records that the run was snapshot-scoped.

**Lane-based fan-out.** For projects with >50 in-scope objects (or any batch over that size): partition the scope into lanes — one per schema, dbt layer, or domain — and run one subagent per lane. Each lane runs the per-object check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum) for its assigned objects and writes its results **incrementally** to its own lane verdict file, `migration/verdicts/run_{N}/{lane_id}.json`, in the shape defined by `specs/migration/equivalency/verdict_schema.md` — rewriting the file after each object so a killed lane loses at most the in-flight object and a resumed lane skips objects already in its file. Lanes never write the register or the verdict log; the coordinating run merges every lane file using the deterministic merge rules in `specs/migration/equivalency/verdict_schema.md` (Step 5b). Business invariants (check type 7) are run once for the release, not per lane, since many are cross-table aggregates. Small scopes (a single lane) still write one verdict file and go through the same merge — one code path, not two.

**Tenant carve-out scoping**

Read `migration.scope` from status.md. When it is absent or `full_migration`, run every check exactly as specified below — no predicate is applied and behaviour is unchanged.

When `migration.scope == tenant_carveout`, apply a tenant filter as a `WHERE` clause on **both** source and target in every data-bearing check, so equivalency validates only the extracted tenant's rows. The parallel fan-out above is unchanged — each subagent threads its objects' filters through the checks for its assigned objects.

- **Row count (1)**, **value sampling (3)**, **freshness (4)**, **row-level checksum (6)**, and **business invariants / aggregate control totals (7)** all add the filter to both sides.
- **Schema (2)** compares column names, types, and nullability — it is structural, not row-data, so the filter does not change what it checks; it runs unchanged.
- **Governance (8)** compares column-level protection metadata — also structural, not row-data — so the filter does not apply; it runs unchanged.
- **dbt tests (5)** run through dbt against the already tenant-scoped target models, so no filter is injected into the test SQL.

No new check types are introduced. min/max already lives inside value sampling (check 3); row-level checksum (check 6) and aggregate control totals (check 7) already exist. The carve-out only narrows the row set each existing check sees.

**Resolve the filter per object, from the registry (v3.11.3).** The filter is **not** `migration.tenant_predicate` applied to everything. Read the object's row from `migration/tenant_predicate_registry.csv` and apply the read contract in `specs/utils/tenant_predicate_registry.md`:

| Registry `mechanism` | Filter applied to both sides |
|---|---|
| `row_predicate`, `derived_expr`, `account_cascade` | `WHERE <expression>` from the row |
| `object_carve` | None. The object is wholly in the carve-out; compare it whole |
| `inherited` | None. Its rows are tenant-only on both sides already; record the `resolving_node` in the verdict |
| `unresolved`, or no row for the object | **Verdict `fail`, reason `unresolved_predicate`** |
| Non-empty `expression` failing the well-formedness check | **Verdict `fail`, reason `malformed_expression`** |

One carve-out needed five mechanisms simultaneously across one release — a plain row predicate, a differently-named column on globalised models, an object-level schema-prefix carve where no row predicate exists, an enumerated account-id list, and a derived expression over a composite key. A single config string cannot express that, so applying one to every object silently compares the wrong row sets.

**An unresolved object is never compared unfiltered.** Verdict `fail`, reason `unresolved_predicate`, naming the object and that no registry mechanism exists — not a `diff_*` value, because nothing was compared and there is no divergence to classify. Unfiltered is the one wrong answer that looks like a real finding: the source side returns every tenant's rows, so the comparison fails for a reason that has nothing to do with the migration, and a reviewer spends the afternoon on a phantom.

**A malformed expression blocks the same way (#200).** Before applying any resolved expression, run the well-formedness check defined in `specs/utils/tenant_predicate_registry.md`: balanced parentheses, closed quotes, no dangling `{{`. A failing expression is verdict `fail`, reason `malformed_expression`, naming the object and the violation; it is never applied, and never repaired by guesswork. The 3.11.x writers truncated comma-bearing expressions at the first comma (a semi-join cut mid-subquery, an unterminated regex), and the truncated rows kept the right column count, so only the expression text itself shows the damage. This applies wherever a registry expression is resolved, relocate-mode comparisons included.

If the registry file itself is absent while `scope == tenant_carveout`, stop and report — re-run `region-tagging-generate` to seed it, or `/wire:upgrade` for a release created before v3.11.3. If `migration.tenant_predicate` is null **and** the registry has no resolved row for an in-scope object, that object is `unresolved` per the table above.

Carve-out lane verdict files record `scope: tenant_carveout` and `tenant_predicate_sha256` (the SHA-256 of the exact filter applied — the resolved per-object expression, not the global config string), per `specs/migration/equivalency/verdict_schema.md` — a carve-out verdict must never be mistakable for a full-estate one. From v3.11.3 they also record the resolved `mechanism` and, for `inherited`, the `resolving_node`: a verdict reached with no filter must say which of `object_carve` and `inherited` earned that, since the two are not interchangeable evidence.

**Relocate-mode comparison (carve-out staged after the parent migration, v3.11.1).** Models whose register row carries `origin: relocate` in `notes` (written by `dbt-carveout-relocate-generate`) were copied from the already-migrated parent target, not translated from the source platform — so comparing them against the source platform re-proves the parent's work, not the carve-out's. For these models only, the comparison sides change: the **source side is the parent target project's production relation with the model's resolved registry filter applied** (parent project from `migration.parent_target_project`), and the **target side is the tenant project's relation, unscoped** (the tenant project is single-tenant by construction). Every check type, pin, and taxonomy rule is otherwise unchanged. Both sides resolve per Step 1g (#201): the parent-side relation from the parent register row's fully qualified `bq_target`, the tenant-side relation from this register's row; either side that cannot be resolved exactly is `unresolved_target` for that model, never a name-matched guess. If `migration.parent_target_project` is null while relocate-origin models are in scope, stop and report for those models — the comparator needs a parent to compare against. Non-relocate models in the same carve-out (translated fresh from the source platform) keep the standard both-sides-predicated comparison above.

**The parent target must itself be proven before it is a comparison basis (#180).** Using the parent relation as the trusted side assumes the parent's own verdict — a comparison against an unproven or failing parent proves nothing about the carve-out. Per relocate-origin model, read its register row's `parent_verdict_ref` (and, where `migration.parent_release` is set, the parent register row it points at): when the parent verdict is `pass` or `pass_qualified`, compare as above; when it is `fail`, any `diff_*`, `null`, or the linkage is blank, do **not** compare — record the model as blocked with reason `parent_verdict_insufficient`, naming the parent reference (or its absence), and route the fix to the parent release. A blocked model counts as failing for `checks_failing`; it is evidence owed, not evidence given.

### Step 1b: Baseline-pin mode (deterministic equivalency)

By default the checks read live source and target tables. With `--baseline` (or when `migration.equivalency_baseline` is set in status.md), run in **baseline-pin mode** against the frozen baseline defined in the migration strategy's "frozen equivalency baseline" section — comparing two pinned states at instant `T`, not two moving platforms.

**(a) Pinned reads.** For every data-bearing check, replace the live table references with the pinned states:
- **Source (Snowflake)** — read the **zero-copy clone at `T`** (the `wire_baseline` schema, `… AT (TIMESTAMP => '<T>')`), never the live table. Continued source ingestion does not move the comparison.
- **Target (BigQuery)** — restrict to the **Bronze watermark**: add `AND _fivetran_synced <= '<T>'` (or the per-connector loaded-at column named in the baseline) so the target reflects exactly what had landed by `T`.

Read `T`, the clone location, the per-connector watermark columns, and the expected type-translation allow-list from `migration.equivalency_baseline`. If `--baseline` is passed but the baseline is undefined in the strategy, stop and report — define it first (`migration-strategy-generate`).

**(b) Deterministic-build switch.** Under baseline mode, make every query reproducible at `T`:
- Replace `CURRENT_TIMESTAMP` / `CURRENT_DATE` / `NOW()` and `CURRENT_DATE`-relative windows (e.g. `WHERE created_at >= CURRENT_DATE - 30`) with values fixed at `T` on **both** sides, so a model's "last 30 days" means the same 30 days on each platform.
- Fix the sampling seed / row-selection so value-sampling (check 3) and the tier-3 comparator draw the **same** rows on each platform across re-runs.
- Tenant-carveout scoping (above) still applies — the predicate ANDs with the watermark/clone filters.

When neither `--baseline` nor `migration.equivalency_baseline` is present, behaviour is unchanged (live reads, no determinism rewrites) — which is exactly the gap Step 1c closes.

### Step 1c: Pin the as-of instant for relative-date models (live mode only)

**Skip this step entirely when running in baseline-pin mode (Step 1b).** The deterministic-build switch there already replaces every relative-date function with a value fixed at `T` on both sides — that fully supersedes this step. This step exists for the common case: a **live-mode** run, with no baseline defined, still needs to guard against timing skew for the specific models that reference "now".

A model whose SQL references "now" — `CURRENT_DATE()`, `CURRENT_TIMESTAMP()`, `NOW()`, `GETDATE()`, or a `DATEADD(..., CURRENT_DATE())`-style window — evaluates "today" at whatever instant its side of the check runs. If the source check runs even minutes before the target check, a window near the live edge ("last 7 days including today", an intraday cutoff) genuinely produces different row counts, aggregates, and samples on the two sides. That is a false divergence caused by timing, not by the migration.

**Detect flagged models.** Scan the SQL of every in-scope dbt model — both the source-dialect SQL and the translated target SQL — case-insensitively for relative-date/time functions:

- `CURRENT_DATE`, `CURRENT_TIMESTAMP`, `CURRENT_TIME`, `LOCALTIMESTAMP`
- `NOW(`, `GETDATE(`, `SYSDATE`, `SYSTIMESTAMP`
- `DATEADD`, `DATE_ADD`, `DATE_SUB`, `TIMESTAMP_ADD`, `TIMESTAMP_SUB` where any argument contains one of the above

Any model with at least one hit is a **relative-date-flagged model**. Note: `dbt_audit.csv`'s `feature_tags` column does not currently carry a tag for these functions (see `platform_pairs/*/feature_detection.md`), so scan the model SQL directly — do not rely on the audit tags.

**Resolve the pinned as-of once.** At the start of the run, before any check on either side, run a single `SELECT CURRENT_TIMESTAMP()` against the source platform. From the result derive:

- `pinned_as_of_ts` — the timestamp, in UTC
- `pinned_as_of_date` — the UTC date component

These two values are fixed for the entire run. When fanning out to parallel subagents (Step 1), pass both values into every subagent prompt so all objects — however long the run takes — evaluate against the identical instant.

**Apply the pin via literal substitution.** For each flagged model, run the data-bearing checks (row count, value sampling, row-level checksum) over a **pinned inline relation** instead of the stored table: take the model's compiled SQL on each platform, replace every relative-date/now call with the pinned literal in that platform's syntax (`DATE '{pinned_as_of_date}'` for date functions, `TIMESTAMP '{pinned_as_of_ts}'` for timestamp functions — e.g. `DATEADD(day, -7, CURRENT_DATE())` becomes `DATEADD(day, -7, DATE '{pinned_as_of_date}')`), then run the check as `SELECT ... FROM ( {pinned SQL} ) AS t` on both sides. The tenant predicate, when in scope, still applies on top. Neither BigQuery nor Snowflake allows overriding `CURRENT_DATE()` via a session variable, so literal substitution over the compiled SQL is the mechanism — do not attempt to "run both sides quickly" as a substitute.

For flagged models materialised as tables, the stored data on each side reflects "now" at its own build time, so the stored tables can legitimately differ at the live edge even when the migration is correct. If the pinned comparison passes but the stored tables differ, record it as a timing artefact, not a divergence.

**Record the pin.** For every flagged model, record the pinned as-of value used against its results in the equivalency report (Step 4) and write `pinned_as_of` into the run's `loop_history` entry (Step 5), so any re-run or investigation can see exactly what instant was used.

### Step 1d: Deployment warehouse type pre-flight

Before the check types run, establish the **deployment** warehouse's actual column types so the schema check (check type 2) validates against them, not against a scratch/sample/playground validation warehouse whose types differ. Run `specs/utils/deployment_type_preflight.md` for the in-scope objects: it reads the deployment warehouse's column types (from `migration.deployment_project` in status.md if set, else the prod-like target in `profiles.yml` — never the validation warehouse), loads the active pair's **"Deployment type-divergence patterns"** section, and returns per-model divergence findings plus an explicit warning when the validation and deployment warehouses differ.

When the validation and deployment warehouses are the same warehouse (the common case — equivalency usually runs against the live deployment target), this records "validation and deployment warehouse are the same — no type-drift risk" and is otherwise a no-op. When they differ, record the warning in the equivalency report (Step 4) and treat any firing type-divergence pattern as a failing object with reason `deployment_type_divergence`, so a model that only passes because the validation warehouse's types differ from deployment is flagged before cutover. Skip only if no deployment warehouse is reachable — recording that the pre-flight could not run rather than passing silently.

### Step 1e: Declared-window / availability-bounded comparison (#180)

A migration target routinely holds less history than the source — a carve-out's Bronze connectors are young, a bring-in lands a bounded window — so a full-table comparison reads 90–99% short for a reason that is availability, not translation. Before this step existed, every such PR body re-argued the qualifier by hand. The declared window makes it a first-class, structured claim the verdict itself carries.

**Resolving the window (per object).** An object has a declared window when either applies:

1. **Explicit** — `migration.declared_windows` in status.md carries an entry for the object (or a table pattern matching it): `floor`, optional `cap`, optional `exclusions` (each with a reason). `floor_derivation: explicit`.
2. **Auto-derived** — the object's target-side upstream landing table exists and its history floor is readable: derive `floor` as the target Bronze `MIN(loaded_at)` (the connector's loaded-at column from the ingestion audit) or, where partition metadata is cheaper, the earliest populated partition. Record which one as `floor_derivation: bronze_min_loaded_at | partition_metadata`.

The `cap` defaults to the run's pinned as-of instant (Step 1c) — or the baseline `T` in baseline mode — so live drift past the pin never enters the comparison. `exclusions` are always explicit and always carry a reason (the connector's initial-load day, a documented ramp-up window); an exclusion with no reason is invalid and ignored with a warning. The window applies on the object's declared time column (from the ingestion audit / model metadata); an object with no resolvable time column cannot carry a declared window and is compared full-table as before.

**How the checks use it.** The data-bearing checks (1, 3, 6, 7) run as specified. When a check diverges on an object that has a declared window, re-run the comparison **in-window** — both sides filtered to `floor <= <time_column> <= cap`, minus the exclusions, on top of any tenant filter — at the same verdict bar (exactness inside the window, not tolerance).

**Verdict binding (deterministic — tests mirror it: `wire/tests/platform_migration/validate_declared_window.py`).**

| Condition | Verdict |
|---|---|
| In-window comparison exact, and every missing row sits before the floor, after the cap, or inside a declared exclusion | `diff_availability`, mechanism `declared_window_availability`, with the structured `window` fields (`floor`, `floor_derivation`, `cap`, `exclusions`, `in_window_result: pass`) on the verdict row per `specs/migration/equivalency/verdict_schema.md` |
| In-window comparison diverges (any missing, extra, or differing row inside the window) | `fail` — an in-window divergence is never availability |
| Shortfall not fully explained by the window (missing rows inside `floor..cap` outside every exclusion) | `fail` |
| Object short with no declared window and no resolvable floor | The existing rules apply unchanged: `fail`, unless a named mechanism earns another `diff_*` verdict |

`diff_availability` still counts as failing for `checks_failing` and the cutover gate until formally accepted, and it is not sufficient for `equivalence_before_pr` batch-raise eligibility — the window makes the claim structured and checkable, it does not upgrade the verdict. The report (Step 4) records the window per object, and a month-by-month in-window drill may be included as supporting evidence where the client asks for it. `dbt-migration-batch-raise` renders the window fields in the PR body for every `declared_window_availability` verdict it ships under `ship_then_verify`.

### Step 1f: Load the connector-emission known-differences registry (#180)

Some divergences are a **connector behaviour class**, not a migration defect: the two platforms' connectors for the same source emit different row sets by design — one emits zero-metric filler rows, the other does not. The class recurs on every table that connector lands, and without a registry each team re-discovers and re-argues it per PR.

Load the engagement's known-differences registry from `migration.known_differences_path` in status.md, defaulting to `migration/known_differences.yaml` in the release folder (template: `TEMPLATES/migration/known_differences.yaml`). No file means no registered differences — every divergence classifies under the standard rules. Entries carry: `id`, `connector`, `table_pattern`, `difference_class`, `direction` (`target_surplus` | `source_surplus`), `detection_query`, `verdict_treatment` (always `pass_qualified`), `provenance`, `verified_date`.

**Classification (deterministic — tests mirror it: `wire/tests/platform_migration/validate_known_differences.py`).** When a data-bearing check diverges on an object:

1. Find registry entries whose `connector` matches the object's landing connector and whose `table_pattern` matches the object, and whose `direction` matches the observed surplus side.
2. Run the entry's `detection_query`. The entry applies **only when the query accounts for the entire delta** — every surplus row isolates to the registered class, exactly.
3. On a full match: verdict `pass_qualified`, `divergence_mechanism: known_connector_emission:<id>`, with the entry's `provenance` cited in the report. A partial match (the query explains some rows but not all) is **not** a match: the residual is an unexplained divergence and the standard rules classify it (`fail` unless another named mechanism applies) — the report records how much the entry explained so the investigation starts from the residual.
4. No matching entry: the standard rules apply unchanged. **An unregistered surplus still fails.** The registry never widens by default; a new behaviour class enters it only as a recorded entry with its proof.

This is the connector-behaviour analogue of the pair's `type_translation_allowlist`: both qualify a divergence with a named, pre-proven mechanism; neither hides one.

### Step 1f2: Declared deviations — target right, source wrong (#219)

A migration can correctly diverge from a **defective** source model. On one carve-out, a source model's cross-market dedup discarded 47% of the tenant's rows at source; the carve-out fixed it, so the target was right and the source was wrong, with the source fix tracked upstream. `known_differences.yaml` (Step 1f) does not cover this: that registry records connector behaviour classes that recur across tables by design; a declared deviation records a proven defect in one named source model.

**The record.** Declared deviations live in the same file Step 1f loads (`migration/known_differences.yaml`, or `migration.known_differences_path`), under the key `declared_deviations`. Entries carry: `id`, `model` (the object it applies to, exactly), `defect` (what is wrong in the source model), `evidence_query` (the query that isolates the defect's rows and proves the count), `upstream_fix_ref` (the ticket/PR tracking the source-side fix), `direction` (`target_surplus` | `source_surplus`), `expected_magnitude` (the row count, or exact rule, the defect accounts for), `verdict_treatment` (always `pass_declared_deviation`), `provenance`, `verified_date`. No file, or no `declared_deviations` key, means none are declared.

**Classification (deterministic — tests mirror it: `wire/tests/platform_migration/validate_carveout_ship_gates.py`).** When a data-bearing check diverges on an object:

1. Find `declared_deviations` entries whose `model` equals the object and whose `direction` matches the observed surplus side.
2. Run the entry's `evidence_query`. The entry applies **only when the recorded magnitude accounts for the entire delta**, the same discipline as Step 1f: a partial match is not a match. The residual is an unexplained divergence, classified by the standard rules (`fail` unless another named mechanism applies), with the report recording how much the entry explained.
3. On a full match: verdict `pass_declared_deviation`, `divergence_mechanism: declared_deviation:<id>`, with the `defect`, `evidence_query` result, and `upstream_fix_ref` cited in the report. The verdict never silently absorbs unrelated deltas: rule 2 enforces that.
4. No matching entry: the standard rules apply unchanged.

**Monitoring corollary.** Row-count monitoring (the cutover runbook's post-cutover monitoring checklist, and any scheduled row-count alerting) excludes declared-deviation models from its alert thresholds: their counts are expected to differ from source by the recorded magnitude, so an alert threshold tuned to parity fires on them every cycle. List them separately with their expected magnitude instead of alerting on them.

### Step 1g: Resolve each object's physical target exactly (#201)

Every data-bearing check below reads the target side at a fully qualified physical relation (`project.dataset.table` / `database.schema.table`). Resolve it exactly, per object, before any check runs (deterministic; tests mirror it: `wire/tests/platform_migration/validate_target_resolution.py`):

1. **Register path.** The object's register row carries a `bq_target` with exactly three dot-separated segments: use it as-is.
2. **Manifest fallback (legacy rows only).** A two-segment `bq_target` is the pre-#201 dbt-relative form. Resolve the row's model in the target-side manifest by name and compose `<database/project>.<schema>.<alias>` (the model name only when no alias is set, dbt's own fallback). Report the row and recommend `/wire:upgrade` (Step 6c re-resolves the register). No manifest node for the model: **verdict `fail`, reason `unresolved_target`**.
3. **Existence.** Confirm the resolved relation exists on the target (a metadata read: `INFORMATION_SCHEMA.TABLES` / `__TABLES__`). A resolved path with no relation behind it is also **`unresolved_target`**: comparing against a non-existent table returns an empty result that reads as a verdict when it is nothing.

**`unresolved_target` is a named outcome, never a `pass`, never a silent skip.** Nothing was compared, so no `diff_*` value applies: like `unresolved_predicate`, it is verdict `fail` with the reason named, it counts as failing for `checks_failing`, and it appears in the report per object with what failed to resolve (blank/malformed `bq_target`, no manifest node, or relation not found).

**Guessing is banned.** Never search the target for a table named like the model, and never accept a single metadata match as the target. One wave-1 post-merge verification run (2026-08-20) showed why: a `schema` + `alias` model materialises under a prefix-stripped physical name (`salesforce_case` builds `salesforce.case`) that name-equality cannot find; the same table name under two datasets let the wrong-dataset guess report a false divergence of 70,229 rows that was an exact match (23,298 = 23,298) in the right dataset; and the reverse guess compared against a non-existent table and returned a silent empty result. This is the physical-side counterpart of the node-identity rule (`model.<package_name>.<model_name>`): a model name is a join key into the register and the manifest, never a physical name.

### Step 2: Run all check types

For each in-scope object, run check types 1–6 and check type 8 (governance); for each in-scope snapshot, additionally run check type 9 (the snapshot three-layer gate). Run check type 7 (business invariants) once per release. For each object:

**Under `--snapshots` scope**, run **only check type 9** over the resolved snapshot set — skip check types 1–8 (and the release-level check 7) entirely. Every other scope runs check type 9 over its in-scope snapshots as described above; `--snapshots` simply narrows the run to the snapshot gate alone.

**Both-sides-empty gate (#219).** A zero-row model passes every data-bearing check vacuously: 0 = 0 on counts, hashes agree on nothing, dbt tests find no rows to fail. Before recording any verdict for an object whose row counts (under the object's resolved filter) are zero on **both** sides, read the model's SQL for the expected-empty marker `dbt-carveout-relocate-generate` stamps as a header comment (`-- EXPECTED EMPTY (<tenant>): ...`). The classification is deterministic (tests mirror it: `wire/tests/platform_migration/validate_carveout_ship_gates.py`):

| Source rows | Target rows | Marker | Outcome |
|---|---|---|---|
| 0 | 0 | present | Verdict `pass`, method class `expected_empty`, with the marker's reason and measured source figures cited as the evidence: an explicit verdict, never a vacuous one |
| 0 | 0 | absent | Verdict `fail`, reason `empty_unexplained`: the run refuses to verify a both-sides-empty model that carries no marker; nothing was meaningfully compared |
| one or both sides > 0 | | present | The gate does not decide the verdict (the standard rules classify the divergence), but the marker is reported stale (`marker_stale`): a marked-empty model that has grown rows contradicts its own marker |
| one or both sides > 0 | | absent | Gate not engaged; the standard checks run unchanged |

`empty_unexplained` follows the same pattern as `unresolved_predicate` and `unresolved_target`: a named failure reason on verdict `fail`, counting as failing for `checks_failing`, never a `diff_*` (there is no divergence to classify). The fix belongs at relocate: measure the model, establish the reason, stamp the marker (`dbt-carveout-relocate-generate` Step 2b), and re-run.

**Check type 1 — Row count**
```sql
-- Source
SELECT COUNT(*) AS row_count FROM source_project.source_schema.table_name;
-- Target
SELECT COUNT(*) AS row_count FROM target_db.target_schema.table_name;
-- Tenant carve-out (migration.scope == tenant_carveout): add the object's resolved registry filter
-- (specs/utils/tenant_predicate_registry.md) as a WHERE clause to both queries.
```
PASS: |source_count - target_count| / source_count ≤ tolerance (default 0.1%, configurable per table in migration strategy)
FAIL: Count outside tolerance
Relative-date-flagged models (Step 1.5): count over the pinned inline relation on both sides, not the stored table.

**Check type 2 — Schema (set + column order)**
Compare column names, types, and nullability between source and target. Use the **deployment** warehouse types from the Step 1d pre-flight as the target side wherever the validation warehouse differs from deployment, and fail on any firing deployment type-divergence pattern (reason `deployment_type_divergence`) — a schema check against a scratch warehouse's types passes while the deployment warehouse's types would error at cutover.

**Column order (W6b).** Do not compare column sets only — a reordered projection passes a set comparison while breaking positional consumers (UNION/INSERT by position, CSV/SAR exports, BI and reverse-ETL pinned to column order). Query both sides with `SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.COLUMNS ... ORDER BY ordinal_position` and compare the **sequences**, per the pair's **"Schema-parity / column-order"** section:
- Source columns must appear first, in source ordinal order.
- The pair's migration-appended tail allow-list (audit/load-timestamp columns, then region/surrogate globalize keys — concrete names from the engagement override) may follow, at the tail, in the declared category order. Strip allow-listed tail columns before comparing the source-column sequence.
- **Set first, then order.** A target column that is neither a source column nor an allow-listed tail column (an unexpected column), or a missing source column, is the schema check's existing set-mismatch FAIL (extra/missing columns) — not `column_order_drift`. `column_order_drift` is reserved for a **pure reorder**: the column set already matches (all source columns present, every tail column allow-listed) but the sequence differs from source order (or the allow-listed tail is out of category order). This keeps `column_order_drift` a deterministic, parity-restoring reorder — which is why `dbt-migration-fix` auto-applies it.
- **Waiver**: a model carrying `column_order_waived: <reason>` in the migration register / model `meta` suppresses `column_order_drift` for that model only (the reason is recorded in the result). Never globally disabled.

PASS: Column sets match (modulo expected type translations per type_mapping.md), no deployment type-divergence pattern fires, and the target column sequence equals the source ordinal order plus any allow-listed tail columns (or a `column_order_waived` waiver is recorded).
FAIL: Missing columns, extra columns, unexpected type changes, a fired deployment type-divergence pattern, or a column-order mismatch (`column_order_drift`) with no recorded waiver.

**Check type 3 — Value sampling**
For numeric columns: compare mean, min, max, null percentage (sample 10K rows if table >10M rows)
For string columns: compare distinct count and null percentage
PASS: Statistical measures within ±1% (configurable)
FAIL: Deviation outside threshold
Min and max are already part of this check — no separate min/max check type is needed.
Tenant carve-out: compute every statistic over the object's resolved registry filter on both source and target (and take the 10K-row sample from within the scoped set).
Relative-date-flagged models (Step 1.5): compute every statistic over the pinned inline relation on both sides.

**Check type 4 — Freshness**
Compare max(updated_at) or max(loaded_at) between source and target.
PASS: Target is within max(sync_frequency, 24h) of source
FAIL: Target data is more than 24 hours stale relative to source
Tenant carve-out: apply the object's resolved registry filter to the max() on both sides. Without it the source max() reflects all tenants and the check would falsely fail against a target holding only the extracted tenant.

**Check type 5 — dbt tests**
Run `dbt test --profiles-dir ~/.dbt --target target_profile` for the translated dbt models.
PASS: All tests pass
FAIL: List failing tests

**Check type 6 — Row-level checksum**
Statistical sampling (check type 3) can pass while individual rows differ — two columns can share a mean and min/max and still be wrong row by row. The checksum check closes that gap by hashing the row content and comparing.

For each in-scope table, compute a hash over the concatenated, canonically-ordered column values and compare an aggregate of those hashes between source and target. For tables ≤10M rows, hash all rows; for larger tables, hash a deterministic sample (e.g. rows where `MOD(ABS(FARM_FINGERPRINT(pk)), 100) = 0`) so the same rows are sampled on both sides.

```sql
-- BigQuery side
SELECT COUNT(*) AS n, SUM(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS hash_agg
FROM target_db.target_schema.table_name AS t;
-- Snowflake side
SELECT COUNT(*) AS n, SUM(HASH(OBJECT_CONSTRUCT(*)::STRING)) AS hash_agg
FROM source_project.source_schema.table_name;
-- Tenant carve-out: add the object's resolved registry filter to both sides, and apply it inside the deterministic
-- sampling filter for large tables so the same scoped rows are sampled on each platform.
```
Canonicalise before hashing so the comparison is not defeated by benign representation differences — see the edge-case checklist below. Relative-date-flagged models (Step 1.5): hash over the pinned inline relation on both sides. PASS: aggregate hashes match over the same row set. FAIL: mismatch (drill into the differing rows via `equivalency-investigate`).

**Check type 7 — Business invariants**
The checks above confirm the data moved; invariants confirm it still *means* the same thing. For each invariant defined in the migration strategy, run the same aggregate query on both platforms and compare.

Typical invariants: total revenue (`SUM(amount)` over orders), active customer count, row counts per key dimension (e.g. orders per region), and any control total the client already trusts. These are engagement-specific and come from `migration_strategy.md`.

PASS: each invariant matches within its defined tolerance (default: exact for counts, ±0.01% for monetary sums to allow for float representation). FAIL: list the invariant, source value, target value, and delta.
Tenant carve-out: add the object's resolved registry filter to each aggregate control-total query on both sides so the invariant is computed over the extracted tenant only. These are the same aggregate control totals as for a full migration — only the row set is narrowed.

**Check type 8 — Column governance / masking equivalence**
Row-level equivalency (checks 1, 3, 6, 7) confirms the data moved; it cannot see column-level security metadata. A column masked at source but landing **unprotected** at target produces identical rows — so every data check passes while the security posture silently regresses. This check closes that gap. It is deliberately separate from row-level equivalency: it compares *protection*, not data.

For each translated model, compare column-level protection at **target** against the **source** platform's protection for the same column, using the mechanisms the active pair names in its "Column governance / masking mechanisms" section:
- Derive the **expected protection** from the source column metadata (e.g. Snowflake `meta.masking_policy`; BigQuery `policy_tags`). A source column carrying a masking policy / policy tag is expected protected; one without is not.
- Read the **actual** target protection from the translated companion YAML (the `policy_tags` / `meta.masking_policy` authored by `dbt-migration-generate` Step 3b item 4) and, where deployed, the target column's catalog binding.
- FAIL when a column protected at source is unprotected at target (reason `governance_regression`), naming the model, column, and the source masking policy / policy tag that was dropped. A column protected at both sides PASSES; a column protected at neither PASSES (nothing to protect); a column newly protected at target only (no source policy) is not a failure but is recorded as an info note.

This is dialect-agnostic — only the source/target mechanism names come from the pair. It runs unchanged under tenant carve-out (protection metadata is not row-scoped) and does not read row data. Where `dbt-migration-generate` flagged an unresolved masking policy `MANUAL REVIEW REQUIRED` (Step 3b item 4 miss), that column is a governance FAIL here until the tag is resolved — the two are the same gap seen from generate-time and validate-time.

PASS: every source-protected column is protected at target. FAIL: list each column protected at source but unprotected at target, with the dropped policy/tag.

**Check type 9 — Snapshot three-layer gate**
Checks 1, 3, and 6 confirm rows moved; for a dbt snapshot that is not enough — a snapshot is an SCD-2 history table, and a SELECT-only row-equivalence cannot see whether history was preserved and continued correctly. For every in-scope snapshot (an `object_type = snapshot` object in the inventory / migration register), **a row-equivalence pass is explicitly rejected as the snapshot's pass criterion**. The snapshot passes only when all three layers pass; each layer independently gates. Read the SCD meta-column set and types from the active pair's **"Snapshot SCD mechanisms"** section (dialect-agnostic — only the meta-column types come from the pair).

- **9a — Copy-parity at `T`.** In baseline mode, the target snapshot relation matches the source clone at `T`: schema **including the four SCD meta columns** (`dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to`) and their ordinal order (payload first, meta columns at the tail in that order), row count, and the row-level checksum (check 6) over the same pinned row set. A `rebuild_from_T` snapshot (recorded sign-off) is exempt from copy-parity — assert it started fresh at `T` and record the sign-off.
- **9b — Continuation behaviour.** After the target `dbt snapshot` run: unchanged upstream rows open no new version; a changed row opens exactly one new version (prior `dbt_valid_to` closed, new `dbt_valid_to` NULL); hard-deletes are invalidated when `invalidate_hard_deletes: true`; a second run is idempotent.
- **9c — SCD integrity.** `dbt_scd_id` unique; `unique_key` and `dbt_valid_from` not null; at most one open version (`dbt_valid_to IS NULL`) per `unique_key` (no overlapping open versions).

PASS: every in-scope snapshot passes 9a, 9b, and 9c. FAIL (reason `snapshot_scd_regression`): name the snapshot and the failing layer(s). This check runs unchanged under tenant carve-out — the tenant predicate narrows the row set each layer sees, but the three layers are unchanged. It is structural/history-shaped, not defeated by the row-level checks passing.

**Edge cases to canonicalise (checks 3, 6, 7)**
These cause false mismatches or, worse, false passes. Account for them before comparing:
- **NULL vs empty string** — `''` and `NULL` may have been merged or split in translation. Compare null-handling explicitly.
- **Unicode / encoding** — normalise (NFC) before hashing; the same glyph can have multiple byte representations.
- **Timezone** — compare timestamps in a single canonical zone (UTC). A model that silently shifted timezone will pass a row count and fail here.
- **Numeric precision / scale** — `NUMBER(38,9)` → `NUMERIC`/`BIGNUMERIC` can round. Round both sides to an agreed scale before hashing monetary columns.
- **Float ordering / trailing zeros** — `1.0` vs `1` and `-0.0` vs `0.0` hash differently; cast to a fixed format first.

### Step 2b: Tier-3 value-level comparator (baseline mode)

In baseline-pin mode, strengthen value sampling (check 3) and the row-level checksum (check 6) into a full tier-3 value comparison over the pinned states. It has two layers, run per in-scope object:

**Per-column aggregate fingerprints.** For each column, compute a deterministic fingerprint on both sides and compare:
- Numeric: `COUNT`, `COUNT` non-null, `SUM`, `MIN`, `MAX`, and a scale-normalised `SUM` (round to the agreed scale) — catches precision/rounding drift.
- String/other: `COUNT` non-null, `COUNT(DISTINCT)`, and `SUM(FARM_FINGERPRINT(value))` / `SUM(HASH(value))` over canonicalised (NFC, trimmed) values.
- Temporal: `MIN`, `MAX`, and distinct-count, compared in UTC.
A column passes when every fingerprint matches (exact for counts; within the agreed scale tolerance for normalised sums).

**Normalised cross-platform row hash.** Hash each row's canonically-ordered, normalised column values and compare an aggregate of the row hashes over the same pinned row set (the deterministic-build switch guarantees the same rows). Normalise **before** hashing so equivalent values hash identically across platforms: cast numerics to a fixed scale, timestamps to UTC microseconds, NULL/empty-string per the edge-case rules, booleans/case-folding consistent. For tables >10M rows, hash the deterministic sample from check 6.

**Expected type-translation allow-list.** Apply the allow-list declared in `migration.equivalency_baseline` so a *correct* cross-platform type change is normalised, not flagged as drift. At minimum:
- `VARIANT → JSON` or `STRING` — compare canonicalised JSON text (sorted keys, no insignificant whitespace), not raw bytes.
- `TIMESTAMP_NTZ → DATETIME` — compare as wall-clock at the same precision; do not apply a timezone shift.
- `NUMBER`-scale rounding — round both sides to the agreed scale before comparing.
A difference that the allow-list explains is **not** a failure; record it as an expected translation in the report. A difference outside the allow-list is a value-drift failure with the column, both fingerprints, and a sample of differing primary keys (drill via `equivalency-investigate`).

Tier-3 runs only in baseline mode (it needs the pinned, deterministic states to be meaningful). In live mode, checks 3 and 6 run as before.

### Step 3: Compile results

Aggregate:
- `checks_total`: total checks run
- `checks_passing`: objects that passed all applicable check types (plus the release-level invariant result)
- `checks_failing`: checks with at least one failure
- `checks_by_type`: breakdown of pass/fail per check type
- Per-object summary: which checks passed/failed for each object

**Pinning coverage check.** Cross-check the relative-date-flagged model list from Step 1c against the models whose data-bearing checks recorded a pinned as-of value. Any flagged model whose checks ran unpinned has an invalid result regardless of pass/fail — count it as failing with reason `unpinned_relative_date_check` and re-run its checks with the pin applied before the run can be considered complete. Detecting the risk and then silently not applying the pin is exactly the failure mode this step exists to prevent.

### Step 4: Write equivalency report

**Output location**: `.wire/releases/$ARGUMENTS/migration/equivalency_report_{run_number}.md`

Use the template at `TEMPLATES/migration/equivalency_report.md`. Include:
- Run summary: date, run number, total/passing/failing
- **Run metadata** (every run, so the result is reproducible): mode (`live` | `baseline`); batch (`N` or `all`); and in baseline mode — the baseline instant `T`, the per-connector Fivetran/loaded-at watermarks applied, the Snowflake clone location (`wire_baseline` schema + `AT(TIMESTAMP)`), and the source repo commit (`migration_sources.dbt.commit` / snapshot SHA). A live run records `mode: live` and why baseline was not used. In live mode, also record the `pinned_as_of_ts` / `pinned_as_of_date` used for this run (Step 1c) and the list of relative-date-flagged models it was applied to — null/empty if none were in scope.
- Expected type translations applied (from the allow-list) — recorded as expected, not failures
- Table-level results: one sub-section per in-scope table/model — see below
- Objects failing by check type
- Top 10 failures sorted by severity (schema failures first, then count, then value)

**Table-level results.** The report is organised at the table level, not as a flat check list — clients review reconciliation per table. For every table/model in scope, write a sub-section containing:
- **Row count**: PASS/FAIL, with source count, target count, and delta
- **All columns present**: yes/no — naming any missing or extra columns (this surfaces check type 2 per table)
- **Sampled column values match**: yes/no — naming any columns whose sampled statistics deviated (this surfaces check type 3 per table)
- One line for each remaining applicable check (freshness, dbt tests, row-level checksum)
- **Column governance preserved**: yes/no — naming any column protected at source but unprotected at target (this surfaces check type 8 per table)
- **Pinned as-of**: the pinned value used, for relative-date-flagged models only

These lines surface existing check types 1, 2, and 3 per table — no new check logic is introduced. The two explicit yes/no lines are required for every table, including passing ones: an all-clear must say so per table, not only in the aggregate summary.

### Step 5: Update status

```yaml
migration:
  equivalency_validation:
    checks_total: N
    checks_passing: N
    checks_failing: N
    last_run_date: "{{TODAY}}"
    loop_history:
      - run: 1
        date: "{{TODAY}}"
        passing: N
        failing: N
        pinned_as_of: "{{PINNED_AS_OF_TS}}"   # UTC; null if no relative-date-flagged models in scope
        report: migration/equivalency_report_1.md
        mode: live | baseline
        run_point: standard | pre_raise | post_merge_prod
        batch: N | all
        wave: null | "B01"                # set only when run with --wave
        snapshots: false | true           # true only when run with --snapshots (check type 9 gate only)
        baseline_t: null | "<T>"          # baseline instant (UTC), baseline mode only
        clone_location: null | "<db>.wire_baseline"
        target_watermark: null | "_fivetran_synced <= <T>"
        source_commit: null | "<sha>"     # snapshot SHA used for the source side
    status: "passing" | "failing" | "complete"
```

Set `status: complete` only when `checks_failing == 0`.

### Step 5b: Merge lane verdicts into the register and the verdict log

Merge every lane verdict file for this run into `migration/migration_register.csv` and `migration/migration_verdict_log.csv`, following the deterministic merge algorithm in `specs/migration/equivalency/verdict_schema.md` exactly: every well-formed verdict appends one log row (seed the log from `TEMPLATES/migration/migration_verdict_log.csv` if absent — it is append-only, never rewritten); `standard` and `pre_raise` verdicts update `last_equivalence_result` (the taxonomy verdict), `last_equivalence_t` (the baseline `T` in baseline mode, else `null`), and `last_validated_commit` (the source commit validated against — the baseline `source_commit` in baseline mode, else the current source HEAD); `post_merge_prod` verdicts advance `delivery_stage` only. This run is the **single writer** for both files — no lane writes them directly. Include the merge summary (appended / updated / malformed / conflict / not_merged / unknown_model counts) in the report. The register update is what lets the drift gate distinguish "validated, then drifted" from "never validated". Skip the register update silently if the register doesn't exist; still write the log.

### Step 6: Output results

If `checks_failing == 0`:
```
All equivalency checks PASS (N/N objects)

Ship the verdict-passing models that are not yet in a client PR:
/wire:dbt-migration-batch-raise $ARGUMENTS [--wave <id>]

When the whole estate is shipped and verified, cutover is unblocked:
/wire:cutover-generate $ARGUMENTS
```

If `checks_failing > 0`:
```
Equivalency checks: N passing, N failing

Top failures:
[List top 5 failing objects with check type and detail]

To investigate a specific failure:
/wire:equivalency-investigate $ARGUMENTS --object <table_or_model>

To apply a fix and re-run affected checks:
/wire:equivalency-fix $ARGUMENTS --object <name> --approach <description>

Re-run all checks after fixes:
/wire:equivalency-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact_id, `Equivalency Validation` as artifact_name, and the `file` value from `artifacts.equivalency` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `validate` as action.

Execute the complete workflow as specified above.
