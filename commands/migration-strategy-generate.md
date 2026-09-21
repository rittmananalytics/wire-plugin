---
description: Generate platform-pair translation guide, phasing, rollback, equivalency criteria
argument-hint: <release-folder>
---

# Generate platform-pair translation guide, phasing, rollback, equivalency criteria

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
    'command': 'migration-strategy-generate',
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

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: migration_strategy
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: document
    path: "migration/migration_strategy.md"
    description: "Platform-pair translation guide, migration phases, rollback procedures, and equivalency success criteria"
  - type: document
    path: "artifacts/migration_strategy/dag_batch_{N}.md"
    description: "Per-batch model DAGs (one file per batch)"
preconditions:
  - artifact: migration_inventory
    action: review
    outcome: approved
valid_next:
  - validate
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: Generate platform-pair translation guide, phasing, rollback plan, and equivalency success criteria
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_strategy` and `artifact_file_path: migration/migration_strategy.md` before proceeding.

---

# Migration Strategy — Generate

## Purpose

Translates the approved migration inventory into an actionable execution strategy. Covers the platform-pair translation approach, migration phasing, rollback plan, and the equivalency criteria that will be used to confirm a successful migration before cutover.

## Prerequisites

- `migration/migration_inventory.md` with `review: approved`

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.md` (optional) — if present with `review: approved`, Step 5b's per-batch DAG generation should note the approved domain batches alongside the existing translation-batch (`dbt_audit.csv` `batch_number`) granularity. These are two different batch concepts — business-domain/cutover slices vs. translation-sequencing groups of ≤20 models — and the strategy doc must not conflate them. If `migration_batching` was never generated, proceed exactly as below with no behaviour change.
- `.wire/releases/$ARGUMENTS/status.md` — source_platform, target_platform
- Canonical platform pair files:
  - BigQuery → Snowflake: `wire/platform_pairs/bigquery_to_snowflake/translation_guide.md`
  - Snowflake → BigQuery: `wire/platform_pairs/snowflake_to_bigquery/translation_guide.md` (quick pattern table) and `translation_reference.md` (exhaustive reference — use its §11 gotcha checklist to scope the silent-behaviour-change risk classes the migration must validate for)
  - Shared: `wire/platform_pairs/dbt_neutral_translation.md` — the macro-first hierarchy and equivalence-testing backbone. Use it to set the per-layer translation approach: how far to push toward dbt-neutral macros (one maintainable project across both warehouses) versus a one-direction rewrite that decommissions the source. Record the decision in the strategy doc.
- **Engagement-level overrides (optional)**: `.wire/engagement/platform_pair_overrides/{pair}/translation_guide.md` — if present, layer on top of the canonical guide. Overrides let a team carry forward bespoke translations from one engagement to the next at the same client.

## Workflow

### Step 1: Load platform pair context

Read the canonical translation guide and type mapping for the active platform pair. Then, if `.wire/engagement/platform_pair_overrides/{pair}/` exists, layer its `translation_guide.md` on top — engagement overrides win where they cover the same construct, and supplement where they introduce new ones. Note any conflicts in the strategy doc under "Translation overrides applied" so the team can see exactly which decisions were taken from where.

These files define the default and engagement-specific translation decisions for all SQL constructs, data types, and configuration patterns.

### Step 2: Draft the translation approach

For each major category of migration work, document the chosen translation approach:

**Data type mapping**: Reference the type mapping file. Flag any types where lossless conversion is not guaranteed (e.g., BIGNUMERIC precision, GEOGRAPHY coordinate system differences).

**SQL dialect translation**: For each platform-specific feature detected in the db_object and dbt audits, document the translation pattern. Where the translation guide provides a macro-based approach, reference the macro. Where a bespoke approach is needed, describe it.

For **snowflake → bigquery** only, decide per layer whether to use the BigQuery Migration Service as an automated first pass before hand-finishing against the guide — see `wire/platform_pairs/snowflake_to_bigquery/bqms_first_pass.md`. It usually pays off for large, mechanical DDL sets and rarely for small or macro-heavy dbt projects. Record the decision here so the target_setup and dbt_migration steps know whether to invoke it.

**dbt configuration translation**:
- `adapter` profile changes
- `dispatch` macro overrides
- **Materialisation**: the default is **faithful preservation** — `dbt-migration-generate` carries each model's resolved materialisation across unchanged (incremental stays incremental with its strategy/partition/cluster, table stays table). Do not set a blanket materialisation default. If this engagement needs to *diverge* from the source — force a materialisation a model didn't have on the source — declare it as policy in a YAML file and point `migration.materialization_overrides_path` (in `status.md`) at it. The file's schema is `default: preserve` plus an `overrides` list of `select` / `exclude` / `force_materialized` rules (see the dbt-migration generate spec). Divergence is an opt-in optimisation, so it lives in engagement policy, never as a Wire default. Record each override rule and its rationale here. Client-specific rule *values* and the file live in the engagement (e.g. `.wire/engagement/<file>.yml`), not in the framework spec.
- Partition/cluster configuration equivalents

**Snapshot migration approach**: For every snapshot in the inventory (the `snapshot` object type), assign a per-snapshot migration strategy. A dbt snapshot is an SCD-2 history table whose closed versions cannot be regenerated from the current source — re-running the snapshot from empty on the target loses all history and breaks any downstream model that reads `dbt_valid_from`/`dbt_valid_to`. Two strategies:

- **`copy_and_continue`** (default, every snapshot unless explicitly overridden): copy the built snapshot table source→target preserving payload + SCD meta columns (`bulk-copy-migration-generate` in carve-out, or the copy path in a full migration), then run `dbt snapshot --select <snap>` once on the target to adopt and continue the history. This preserves every closed version. It is the default because it is the only strategy that keeps history, and it must not require a sign-off.
- **`rebuild_from_T`** (opt-in, requires a recorded data-owner sign-off): abandon the source history and start the target snapshot fresh from the baseline instant `T`. Only legitimate when the data owner has signed off that pre-`T` history is not required (e.g. the snapshot only ever feeds a "current state" consumer, or history is being deliberately reset). Record the signing data owner and date. **Never assign `rebuild_from_T` without a recorded sign-off** — absent a sign-off, the snapshot stays `copy_and_continue`.

Record each snapshot's assigned strategy, and for `rebuild_from_T` the sign-off reference, in this section and in the migration register (`migration-register-generate`). Read the SCD meta-column set and the `dbt_scd_id` continuation invariant from the active pair's **"Snapshot SCD mechanisms"** section — do not hardcode the meta-column types.

**Connector migration**: Whether Fivetran connectors will be cloned to new destinations or new connectors created from scratch on the target.

**Security migration**: How source roles/policies translate to target IAM/roles using the security audit's `translate` and `evaluate` objects.

For **tenant carve-out** (`migration.scope == tenant_carveout`), additionally define the tenant-scoped target IAM model from the security audit's `tenant_scoped` vs `shared` classification:

- **Two-project / tenant-scoped model**: place the extracted tenant's data in its own target project (BigQuery) or database (Snowflake), separated from shared/reference data. Shared roles are recreated platform-wide; `tenant_scoped` roles are granted only on the tenant's project/database.
- **RLS predicate**: for every in-scope table flagged with the tenant key, define the row-level security predicate on that key from `migration.tenant_predicate` (e.g. `tenant_id = 4815`). Record the exact predicate, the tenant-key column, and the IAM principals the policy grants to, so `target-setup-generate` can emit it directly.
- Reuse the platform pair's security mapping rather than inventing a mechanism. For snowflake → bigquery see `wire/platform_pairs/snowflake_to_bigquery/translation_reference.md` §16 — RLS via `CREATE ROW ACCESS POLICY ... FILTER USING`, column masking via Data Catalog policy tags (the same taxonomy used for PII).

When scope is absent or `full_migration`, this tenant block does not apply — security migration is unchanged.

### Step 3: Define migration phases

Divide the migration into sequential phases, each with a defined entry criterion, work items, and exit criterion:

1. **Target setup** — create target warehouse objects (DDL), roles, and permissions
2. **Parallel ingestion** — activate Fivetran connectors to target platform (source connectors remain active)
3. **dbt migration batches** — translate and validate dbt models batch by batch
4. **Orchestration migration** — recreate jobs pointing to target platform
5. **Equivalency validation** — run parallel equivalency checks until all pass
6. **Cutover rehearsal** — execute the full cutover sequence on staging at production scale; record step timings and prove the rollback works
7. **Cutover** — redirect production traffic, then keep source live through the rollback window (default 7–14 days) before a separate decommission step

For each phase, list:
- Dependencies (prior phases that must be complete)
- Estimated duration (from migration inventory effort estimates)
- Rollback procedure (what to do if this phase fails)

### Step 4: Define equivalency success criteria

For each in-scope table and dbt model, define the equivalency checks that must pass before cutover is approved:

- **Row count check**: source count ≈ target count (within tolerance defined per table — default ±0.1%)
- **Schema check**: column names, types, and nullability match
- **Value check**: statistical sampling — mean, min, max, null% for numeric columns; distinct count and null% for string columns
- **Freshness check**: target data is no more than 24 hours behind source (or within the connector sync frequency)
- **dbt tests**: all existing dbt tests pass on the target profile
- **Row-level checksum**: hashed row content matches over the same row set (catches drift that statistical sampling passes — see equivalency validate spec)
- **Business invariants**: define the engagement-specific control totals that must reconcile exactly (or near-exactly) — e.g. total revenue, active customer count, orders per key dimension. List each invariant with its query and tolerance here; the equivalency loop runs them against both platforms.

**Snapshot equivalency (three-layer gate, not row equivalence).** For every snapshot, a SELECT-only row-equivalence check is **not** a sufficient pass criterion — it cannot see SCD-2 continuity. Each snapshot must pass all three layers (defined and enforced in `dbt-migration-validate` / `equivalency-validate`): (a) **copy-parity at `T`** — schema including the SCD meta columns and their ordinal order, row count, and row-level checksum match at the baseline; (b) **continuation behaviour** — after the target `dbt snapshot` run, unchanged rows stay unchanged, changed rows open exactly one new version, hard-deletes are invalidated (when `invalidate_hard_deletes: true`), and a second run is idempotent; (c) **SCD integrity** — `dbt_scd_id` unique, `unique_key` and `dbt_valid_from` not null, no overlapping open versions per key. State this per-snapshot gate here so the equivalency loop knows a snapshot is judged on all three layers, never on row equivalence alone.

Specify the overall success threshold: cutover is unblocked when `checks_failing == 0` across all in-scope objects. Define how partial failures are handled (per-table hold vs full stop).

#### Define the frozen equivalency baseline

Equivalency must compare two *pinned* states, not two moving platforms — the source keeps ingesting and the target keeps loading, so a live-vs-live comparison surfaces timing differences, not translation differences. Define the baseline here; `dbt-migration-generate` builds against it and `equivalency-validate` compares against it (this is the "baseline defined in the migration strategy's equivalency section" that `reverse-etl-migration` and others reference).

Specify:

- **Baseline instant `T`** — a single cutoff timestamp (UTC). Both sides are pinned to `T`. Record how `T` is chosen (e.g. a quiet point after a completed Fivetran sync round).
- **Source pin (Snowflake)** — a **zero-copy clone at `T`**: `CREATE … CLONE … AT (TIMESTAMP => '<T>')` (or a time-travel read `AT (TIMESTAMP => '<T>')`) into a read-only `wire_baseline` schema. The clone is frozen, so continued source ingestion does not move the comparison. Record the clone location.
- **Target pin (BigQuery)** — a **Bronze watermark ≤ `T`**: for each Fivetran-landed table, the comparison includes only rows with `_fivetran_synced <= '<T>'` (or the equivalent loaded-at column), so the target reflects exactly what had landed by `T`. Record the per-connector watermark column.
- **Determinism** — both sides must be reproducible at `T`: no `CURRENT_TIMESTAMP`/`CURRENT_DATE`-relative logic, fixed sampling seeds. Models whose logic is time-relative are listed here so the deterministic-build switch can pin them.
- **Expected type-translation allow-list** — the cross-platform type changes that are *correct* and must not be flagged as value drift: e.g. `VARIANT → JSON`/`STRING`, `TIMESTAMP_NTZ → DATETIME`, `NUMBER`-scale rounding. List each with the normalisation applied before comparison.

`equivalency-validate` runs in **baseline-pin mode** against this definition. Record `T`, the clone location, the watermark columns, and the source repo commit so every equivalency result is reproducible.

### Step 5: Write the strategy document

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`

Use the template at `TEMPLATES/migration/migration_strategy.md`. Include:
- Platform pair summary
- Translation approach by category
- **Snapshot migration** object-type section: one row per snapshot with its assigned strategy (`copy_and_continue` / `rebuild_from_T`), and for every `rebuild_from_T` the recorded data-owner sign-off (name + date). State the default (`copy_and_continue`) and that `rebuild_from_T` never appears without a sign-off.
- Phase plan with timelines and rollback procedures
- Equivalency success criteria
- Risk register (top 5 risks with likelihood, impact, mitigation)
- Go/no-go checklist for cutover

### Step 5b: Generate per-batch migration DAGs

For each batch defined in the migration phases (or from `audit/dbt_audit.csv` if available at this stage), generate a Mermaid batch DAG file.

**Output location per batch**: `.wire/releases/$ARGUMENTS/artifacts/migration_strategy/dag_batch_{N}.md`

Create the directory if it doesn't exist. One file per batch. Each file is a standalone Mermaid flowchart — it will be updated in-place by `/wire:dbt-migration-generate` as models progress through the translation and equivalency loop.

**DAG format**:

```markdown
# Migration Batch {N} — Model DAG

*Status last updated: {TODAY}*
*Legend: ⬜ not started · 🟠 translated · ✅ passed · ❌ failed*

```mermaid
flowchart TD
  classDef notStarted fill:#999,color:#fff,stroke:#666
  classDef migrated fill:#f90,color:#000,stroke:#c60
  classDef complete fill:#2a2,color:#fff,stroke:#1a1
  classDef failed fill:#c00,color:#fff,stroke:#800

  model_a[stg_admin_site__leads]:::notStarted
  model_b[stg_admin_site__dealers]:::notStarted
  model_c[int_leads_with_dealers]:::notStarted

  model_a --> model_c
  model_b --> model_c
```
```

**Building the DAG**:

1. Source the model list for each batch from `audit/dbt_audit.csv` (column `batch_number`). If the audit CSV is not yet available, use the batch groupings defined in the migration phases (Step 3 above) as a placeholder — one node per model listed in the phase work items.

2. Build edges from `ref()` dependencies:
   - **Preferred**: read `<migration.dbt_project_path>/target/manifest.json` — it contains `depends_on.nodes` edges for every model.
   - **Fallback**: scan each model `.sql` for `ref(...)` calls to derive edges.
   - Only show edges where both the parent and child are **in the same batch**. For cross-batch dependencies (parent in batch M, child in batch N > M), add a dashed edge from an external reference node:

     ```
     ext_batch_M_model_x([model_x · batch M]):::notStarted
     ext_batch_M_model_x -.-> model_y
     ```

3. Initial state for all nodes: `:::notStarted` (grey). Do not assign any other state at strategy time — states are updated by `/wire:dbt-migration-generate` as the migration runs.

4. Node labels: use the model name (without schema prefix). Sanitise for Mermaid: replace `__` with `_`, avoid parentheses in node IDs. Use `[label]` (rectangular) for standard models, `([label])` (stadium) for external reference nodes, `{label}` (diamond) for models flagged `low` confidence in the dbt audit.

**Update the strategy document** (`migration_strategy.md`) to include a reference section listing all batch DAG files:

```markdown
## Migration Batch DAGs

Visual progress tracker for each migration batch. Updated automatically by `/wire:dbt-migration-generate`.

| Batch | File | Models |
|-------|------|--------|
| 1 | `artifacts/migration_strategy/dag_batch_1.md` | N models |
| 2 | `artifacts/migration_strategy/dag_batch_2.md` | N models |
```

### Step 6: Update status

```yaml
artifacts:
  migration_strategy:
    generate: complete
    file: migration/migration_strategy.md
    generated_date: "{{TODAY}}"
```

### Step 7: Output next command

```
/wire:migration-strategy-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_strategy` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_strategy` as artifact_id, `Migration Strategy` as artifact_name, and the `file` value from `artifacts.migration_strategy` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_strategy` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
