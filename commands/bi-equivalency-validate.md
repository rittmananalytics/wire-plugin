---
description: Tile-level parity: Looker and Omni results compared under a pinned as-of, verdicts in the model taxonomy; gates cutover
argument-hint: <release-folder> [--batch N 
---

# Tile-level parity: Looker and Omni results compared under a pinned as-of, verdicts in the model taxonomy; gates cutover

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
    'command': 'bi-equivalency-validate',
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
artifact: bi_equivalency
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> compares one content batch; --dashboards id1,id2 compares named dashboards; --post-cutover runs the post-cutover point against the published model"
produces:
  - type: report
    path: "migration/bi_equivalency_report_{N}.md"
    description: "Per-tile comparison for the run: sides, pinned as-of, filter bindings, counts, differing keys and columns, verdict"
  - type: report
    path: "migration/verdicts/run_{N}/<lane_id>.json"
    description: "Lane verdict file under the shared verdict schema, one per sweep lane, object_type tile"
preconditions:
  - artifact: omni_content
    action: generate
    outcome: complete
delegates_to:
  - utils/migration_agent_delegate
  - utils/precondition_gate
  - migration/equivalency/verdict_schema
description: Tile-level parity between each Looker tile and its rebuilt Omni tile, both pinned to the same as-of, verdicts in the model taxonomy; the gate cutover consumes
argument-hint: <release-folder> [--batch <id> | --dashboards id1,id2] [--post-cutover]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding. The gate reads `artifacts.omni_content.generate`; while content batches are still being written that field is `in_progress`. Treat a batch present in `artifacts.omni_content.batches_complete` as meeting the gate for that batch.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Both sides are READ ONLY queries. Looker tiles run through the Looker API
  with their saved query; Omni tiles run through omni query run against the
  branch (or the published model with --post-cutover). No document, tile,
  Look or model is edited.

Warehouse: every comparison runs the same tile twice against the same
  warehouse, once from each tool. Query count and estimated scan are recorded
  per run and count against the release budget's warehouse_spend line.
```

---

# BI Equivalency: Validate

## Purpose

`omni-content-validate` proves a rebuilt dashboard **exists** with the planned tiles. Nothing yet proves a tile returns the **same numbers** as the Looker tile it replaced. This command closes that with tile-level verdicts in the model taxonomy, the BI counterpart of `specs/migration/metabase_equivalency/validate.md`, and it is the gate cutover consumes: **every in-scope tile must hold `pass` or `pass_qualified` before users are switched to Omni.**

Like `equivalency-validate`, this is a repeatable loop command, not a generate/validate/review artifact. It runs per content batch as dashboards are created, and once more over the whole scope before cutover.

## Prerequisites

- The batch's manifest has rows at `state: created`
- `bi_migration.parity_as_of` set in status.md (the pinned instant; the plan sets it, and this command refuses to run unpinned)
- Looker API credentials and Omni CLI configured
- `migration/baseline.yaml` written by `bi-migration-plan-generate` (every verdict names the baseline it was measured against)
- One test contract per compared tile at `migration/parity/contracts/<dashboard_id>/<tile_key>.yaml` (Step 1b writes the missing ones from the content plan on first run)

## Verdict taxonomy

The model taxonomy applies unchanged: `pass`, `pass_qualified`, `pass_declared_deviation`, `diff_vintage`, `diff_availability`, `diff_schema_type`, `fail`, as defined in `specs/migration/equivalency/validate.md`. Two mechanisms recur for BI tiles and are the ones `pass_qualified` most often names:

| Mechanism | When it applies |
|---|---|
| `rounding` | Measure values differ only within the recorded tolerance (below) |
| `timezone_conversion` | A date-grained dimension shifts by one bucket at the boundary because Looker's `convert_tz` and Omni's `convert_tz` settings differ; claimable only when the model batch recorded the deliberate setting |
| `sort_only` | Same row set, same values, different order, on a tile with no explicit sort |

Explanations qualify a fail; they never upgrade it. A tile with no named mechanism is `fail`.

## Outcomes

A verdict says how the numbers compare. An outcome says what happened when the comparison ran. Every tile gets both, from the comparator script (Step 2):

| Outcome | Meaning | Verdict written |
|---|---|---|
| `PASS` | Two clean result sets, equal under the contract | `pass`, or `pass_qualified` with the mechanism |
| `FAIL` | Two clean result sets, different | `fail` |
| `ACCEPTED_DIFFERENCE` | Different, and `migration/parity/accepted_differences.yaml` has an entry for the tile with a named approver, a reason and a date (mirrored in `decisions.md`) | `pass_declared_deviation` |
| `BLOCKED` | The Looker query failed, so there is nothing to compare against. A source failure is never a target success | none |
| `INCONCLUSIVE` | A side reached the row limit (a truncated set cannot prove equivalence), or both sides were empty when the contract expected rows | none |
| `NOT_RUN` | Not compared this run: skipped tile, no contract, or standing evidence invalidated by drift (below) | none |

Only `pass`, `pass_qualified` and `pass_declared_deviation` satisfy the gate. `BLOCKED`, `INCONCLUSIVE` and `NOT_RUN` are `unresolved` in the roll-up and block cutover until resolved; they are never counted as passing, and never as failing.

**Evidence invalidation.** Each tile verdict carries an `evidence_fingerprint` (`scripts/bi_evidence.py fingerprint`, SHA-256 over seven components: the LookML definition, the emitted Omni definition, the dependency closure, the policy context, the data context, the test contract and the adapter versions), recorded in `migration/parity/evidence.csv`. `migration-drift-generate` recomputes it and writes `stale_kinds`; a tile whose row lists `numeric_parity` there is `NOT_RUN` for the gate until this command re-runs it. A presentation-only Omni edit stales `presentation_fidelity` alone and costs no warehouse query.

## Workflow

### Step 1: Resolve scope and the comparison sides

Scope is every `created` dashboard in `migration/omni_content/<batch_id>/manifest.csv` for `--batch <id>`, or the named `--dashboards`, or every created dashboard across all batches when neither is given. `bi_migration.parity_scope: prioritised` restricts the default to dashboards whose `usage_rank` is within the plan's parity cut; `all` compares everything created.

Per dashboard, the tile list comes from `migration/omni_content/<batch_id>/plan.json`. Skipped tiles and inline-text items are recorded as `not_compared` with their skip reason; they are never counted as passing or failing.

| Side | How the query runs |
|---|---|
| Source (Looker) | The element's saved query from `source/<dashboard_id>.json`, run through the Looker API `run_inline_query` (result format json), or the Looker MCP query tool, with the dashboard's default filter values applied and the date filter pinned (below) |
| Target (Omni) | The tile query from `omni documents get-queries <target_identifier>` (which carries the workbook model id), run with `omni query run --body '{"query": ...}'`, `branchId` set to `bi_migration.omni_branch`, then `omni query wait`; without `branchId` under `--post-cutover` |

**Pinning.** Both sides get a date filter on the tile's primary date field bounded at `bi_migration.parity_as_of`: the Looker filter as `before <as_of>` on the matching field, the Omni filter as a date object with `right_side` at the same instant. A tile with no date field is compared as-is and flagged `unpinned` in the report; a divergence on an unpinned tile that a matched-vintage re-run resolves is `diff_vintage`.

**Filter bindings.** Dashboard filters bind at the dashboard's default values on both sides. A tile whose Looker filter has no Omni control counterpart (skipped as `unmapped_filter` in the plan) is `not_compared`.

**Explicit limits and timezone.** Both sides run with the contract's `execution.limit` (the tile's own limit when it has one, else 5000) and `execution.timezone` set explicitly; the Looker and Omni defaults differ and are never relied on. A result that reaches the limit is `INCONCLUSIVE`, not compared.

The Omni result arrives as base64 Arrow IPC; decode it (pyarrow) before comparison. Write both sides as CSV under `migration/parity/results/run_{N}/<dashboard_id>/<tile_key>.{source,target}.csv`; they are the evidence the verdict points at.

**`--model-probes`.** Before any content exists, `--model-probes --batch <model batch>` compares the model alone: per view in the batch, a row count, a distinct count on the primary key, and each measure summed with no dimensions, both sides, under the batch's contracts at `migration/parity/contracts/model/<view>.yaml`. Verdicts are written with `object_type: view` and `method_class: model_probe`. Probe verdicts do not satisfy the gate; they find a wrong `aggregate_type`, a lost join filter or a timezone setting weeks before a dashboard shows it.

### Step 1b: Test contracts

A contract is the control plane's own record of what is being compared and how; not a Looker payload, not an Omni payload. One YAML per tile:

```yaml
test_id: <dashboard_id>__<tile_key>
source_object: "looker:<project>:dashboard:<id>/element:<element_id>"     # object_uri from the audit catalog
target_object: "omni:<instance>:document:<target_identifier>/tile:<key>"
baseline: <baseline id from migration/baseline.yaml>
execution:
  principal: <the user or attribute set both sides ran under>
  timezone: <IANA zone>
  data_snapshot: <bi_migration.parity_as_of>
  limit: <explicit row limit, both sides>
  cache_policy: bypass
comparison:
  row_semantics: multiset | ordered          # ordered only when the tile's sort is part of its meaning (a ranked top-N)
  key_fields: [<Omni view.field of every dimension and pivot>]
  field_map: {<Looker view.field>: <Omni view.field>}   # from the content plan
  measures:
    <Omni view.field>: {comparator: exact_integer | exact_decimal | floating_tolerance, precision: N, absolute_tolerance: x, relative_tolerance: x}
  dates: {fields: [<date key fields>], bucket: day | month, timezone_conversion_recorded: false}
  expected_rows: nonzero | any
  tile_sorted: true | false
```

On first run this command writes every missing contract from `plan.json` and the plan's field map, with these defaults: `exact_integer` for `count`, `count_distinct` and sums of integer columns; `exact_decimal` at the field's display precision for `sum`, `min` and `max` of decimal columns; `floating_tolerance` with `relative_tolerance: 0.005` (0.5%) and `absolute_tolerance: 0.005` for `average`, `median`, `percentile`, `type: number` ratios and table calculations; `timezone_conversion_recorded: true` only when the model batch's `omni_model.md` records the `convert_tz` decision for the view. The plan may tighten any tolerance per dashboard. A contract is hand-edited after that, never regenerated over; its SHA-256 is part of the evidence fingerprint, so an edit invalidates the standing verdict.

### Step 2: Compare at the tile grain

The comparison is a script, not a judgement. For each tile with two result files:

```bash
python3 <plugin-root>/scripts/bi_parity.py \
  --contract migration/parity/contracts/<dashboard_id>/<tile_key>.yaml \
  --source   migration/parity/results/run_{N}/<dashboard_id>/<tile_key>.source.csv \
  --target   migration/parity/results/run_{N}/<dashboard_id>/<tile_key>.target.csv \
  --source-status ok|error|truncated --target-status ok|error|truncated \
  --accepted migration/parity/accepted_differences.yaml \
  --out migration/verdicts/run_{N}/tiles/<dashboard_id>/<tile_key>.json
```

What the comparator does, in order (tested by `wire/tests/bi_migration/validate_bi_parity.py`):

1. **Execution first.** Source `error` is `BLOCKED`; target `error` is `FAIL`; either side at the limit is `INCONCLUSIVE`; both empty with `expected_rows: nonzero` is `INCONCLUSIVE`.
2. **Row count.** Exact.
3. **Row set as a multiset.** Keyed by `key_fields` after the field map; duplicate rows keep their multiplicity, so a lost duplicate fails where a set comparison would pass. Rows present on one side only are listed by key.
4. **Values, typed.** Per measure per matched row, with the contract's comparator. Null is distinct from zero, from an empty string and from a missing row. A `floating_tolerance` pass that needed the tolerance records `rounding`.
5. **Pivots.** A pivoted tile compares the unpivoted result: the pivot dimensions are key fields.
6. **Timezone.** When `timezone_conversion_recorded` is true and the sets differ, the comparator re-tries with every source date key moved one bucket forward, then back; an exact match either way is `pass_qualified` with `timezone_conversion`. A shift is never inferred without the recorded decision.
7. **Order.** `ordered` semantics fail on order alone; `multiset` semantics on a tile with `tile_sorted: false` record `sort_only`.

The tolerance and comparator used are written into every verdict document (`tolerances_used`), and the report repeats them per tile.

### Step 3: Verdicts

The verdict is the comparator's `verdict`; the agent does not overrule it. A row-count or key-set difference is `fail` unless a named mechanism explains every differing row (`diff_vintage` after a matched-vintage re-run on an unpinned tile, `diff_availability` only where the plan declares a window; both are set by re-running the comparator on the re-pulled result, not by editing the verdict). A value difference within tolerance on an averaged or ratio measure is `pass_qualified` with `rounding`. A one-bucket date shift with a recorded `convert_tz` decision is `pass_qualified` with `timezone_conversion`. Anything else is `fail`.

A `fail` becomes `pass_declared_deviation` only through `migration/parity/accepted_differences.yaml`: one entry per `test_id` with `reason`, `approver` (a named person) and `date`, mirrored as a ruling in `decisions.md`. The agent never adds an entry; the release director does.

### Step 4: Verdict log and register

Each lane writes one verdict file per run at `migration/verdicts/run_{N}/<lane_id>.json` under `specs/migration/equivalency/verdict_schema.md`, with `object_type: tile`, `model` set to `<dashboard_source_id>/<element_id>`, `file_version` set to the Omni document's `target_identifier` plus the branch commit, `method_class` `tile_pinned` (or `tile_unpinned`, or `model_probe`), and per tile the comparator's `outcome`, the `baseline` id, the contract path and its SHA-256, the two result file paths, and the `evidence_fingerprint`. The per-tile comparator documents under `migration/verdicts/run_{N}/tiles/` are the evidence; the lane file is the summary the single writer merges. Verdicts are merged into `migration/migration_verdict_log.csv` and the register by the single writer per the schema's merge rules. This command never writes the register from a lane.

**Roll-up.** Each dashboard's register row (`object_type: dashboard`) takes `last_equivalence_result` from its tiles: `pass` only when every compared tile is `pass`; `pass_qualified` when every compared tile is `pass` or `pass_qualified`; otherwise the worst tile verdict (`fail` beats any `diff_*`). A dashboard with any tile at `BLOCKED`, `INCONCLUSIVE` or `NOT_RUN` cannot roll up to a passing verdict: its row keeps its previous `last_equivalence_result` and the dashboard is listed as `unresolved` with the tiles and outcomes. A dashboard with no compared tiles (all `not_compared`) keeps `last_equivalence_result: null` and is listed in the report as `uncompared`. The evidence file `migration/parity/evidence.csv` (`model`, `object_type`, `evidence_fingerprint`, the seven components, `computed_at`, `stale_kinds`) gets one row per tile written or replaced this run, with `stale_kinds` cleared. Tile rows take their own verdict. `last_equivalence_t` is `parity_as_of` on every row written.

**Run points.** A normal run is `run_point: standard` and updates `last_equivalence_result`. `--post-cutover` is `run_point: post_merge_prod`: it compares against the published model after the branch merged, never touches `last_equivalence_*`, and advances a dashboard's `delivery_stage` to `production_verified` when its roll-up is `pass` or `pass_qualified` and its `delivery_stage` is `merged` (merge rule 5 in the verdict schema).

### Step 5: The cutover gate

`/wire:cutover-generate` for a `bi_migration` release requires every dashboard in the parity scope at `pass`, `pass_qualified` or `pass_declared_deviation` from this command, every prioritised dashboard compared (none `uncompared`), no tile `BLOCKED`, `INCONCLUSIVE` or `NOT_RUN` (none `unresolved`), and no evidence row with `numeric_parity` in `stale_kinds`. One `fail` or `diff_*` blocks the cutover runbook until it is fixed or formally accepted with a named person and reason in `decisions.md`. A dashboard that renders wrong numbers after users are switched is found by the client, which is the most expensive place to find it.

### Step 6: Report and status

`.wire/releases/$ARGUMENTS/migration/bi_equivalency_report_{N}.md`: per dashboard, then per tile: element id and title, sides, pinned as-of, filter bindings, tolerance, counts both sides, differing keys and columns (named), verdict and mechanism, evidence anchor; then the roll-up table per dashboard, the `not_compared` list with reasons, the budget line (queries run, scan estimate), and the merge summary.

```yaml
artifacts:
  bi_equivalency:
    last_run_date: "{{TODAY}}"
    run_count: N
    tiles_checked: N
    passing: N              # pass
    pass_qualified: N
    failing: N              # fail and every diff_*
    unresolved: N           # BLOCKED + INCONCLUSIVE + NOT_RUN tiles, plus uncompared dashboards
    blocked: N
    inconclusive: N
    accepted_differences: N # pass_declared_deviation
    contracts: N            # contracts on disk for tiles in scope
    stale_evidence: N       # evidence rows with numeric_parity in stale_kinds
    dashboards_passing: N   # roll-up pass, pass_qualified or pass_declared_deviation
    validate: pass | fail   # pass only when every dashboard in the parity scope rolls up to a passing verdict, none is uncompared or unresolved, and stale_evidence is 0
```

`validate: pass` is the field the cutover gate reads.

## Under the release director model

Each content batch is one **parity sweep** lane. The brief names the batch, owns `migration/verdicts/run_{N}/<lane_id>.json` and its state file, and carries a warehouse budget line: the plan's estimated queries for the batch (two per compared tile). A lane over its estimate disclosed the overrun in its report; it does not stop mid-batch. The lane writes its verdict file incrementally after each tile, so a killed lane resumes at the first tile not in its own file. It reports once, with the roll-up counts and any tile it could not compare.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/bi_equivalency_report_{N}.md`
- `.wire/releases/$ARGUMENTS/migration/verdicts/run_{N}/<lane_id>.json`
- `.wire/releases/$ARGUMENTS/migration/verdicts/run_{N}/tiles/<dashboard_id>/<tile_key>.json` (comparator documents)
- `.wire/releases/$ARGUMENTS/migration/parity/contracts/<dashboard_id>/<tile_key>.yaml` (written once, then hand-edited)
- `.wire/releases/$ARGUMENTS/migration/parity/results/run_{N}/<dashboard_id>/<tile_key>.{source,target}.csv`
- `.wire/releases/$ARGUMENTS/migration/parity/evidence.csv`
- Read: `.wire/releases/$ARGUMENTS/migration/parity/accepted_differences.yaml` (written by the release director, never by this command)
- Updated `.wire/releases/$ARGUMENTS/migration/migration_verdict_log.csv` (by the single writer)
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (by the single writer)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_equivalency` as artifact, `validate` as action.

3. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bi_equivalency` as artifact, `validate` as action.

Execute the complete workflow as specified above.
