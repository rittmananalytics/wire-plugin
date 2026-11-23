---
description: "Tile-level parity: Looker and Omni results compared under a pinned as-of, verdicts in the model taxonomy; gates cutover"
argument-hint: "<release-folder> [--batch N | --dashboards id1,id2]"
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

## Pair: tableau_to_looker

This pair is experimental (see `specs/migration/tableau_audit/generate.md`).

- **Source side.** Each Tableau sheet's rows through REST Query View Data (`python3 <plugin-root>/scripts/tableau_export.py view-data --view-luid <luid> --filter <field>=<value> ... --out <file>.csv`), with the dashboard's default filter values and the date pinned at `parity_as_of`. On Server from 2025.1 and on Cloud, the VizQL Data Service may be used for published data sources. The view LUID is the sheet's `view_luid` in `bi_content_catalog.csv`; a sheet with no LUID is not published as a view, so read it through a dashboard that shows it. Query View Data returns values as the sheet displays them: currency symbols and thousands separators (which the comparator reads) and rounding to the sheet's number format (which it cannot undo), so set each measure's `precision` to the displayed precision. In files mode there is no headless source side: export each sheet by hand and record `method_class: manual_export`.
- **Target side.** The LookML dashboard element's query through the Looker API `run_inline_query` or the Looker MCP `query` tool, on the migration branch.
- **Extracts.** For a sheet on an extract-backed data source, record the extract's last refresh time in the contract's `data_context` with `parity_as_of`. If the extract refreshed after the parity run, the tile is `INCONCLUSIVE`, not `PASS` (`tableau_export.py diff` flags it as `extract_refreshed_after_parity`).

## Pair: metabase_to_looker

This pair is experimental (see `specs/migration/metabase_source_audit/generate.md`).

- **Source side.** Each card's rows through the Metabase API, raw values rather than display formatting: `python3 <plugin-root>/scripts/metabase_export.py card-data --card <id> [--dashboard <id> --dashcard <id> --param <parameter id>=<value> ...] --out <file>.csv`. With `--dashboard` and `--dashcard` the card runs as it does on that dashboard, with the dashboard's filter values. The command writes `<file>.csv.status`: `truncated` when Metabase capped the rows (2,000 by default), which makes the tile `INCONCLUSIVE`.
- **Target side.** The LookML dashboard element's query through the Looker API `run_inline_query` or the Looker MCP `query` tool, on the migration branch.
- **Dates.** Metabase returns a date bucket as the timestamp of its first day (`2026-10-01T00:00:00Z`); Looker returns the bucket's label (`2026-10`). Declare each grouped date key in `comparison.dates.grain` (`day`, `week`, `month`, `quarter` or `year`) so both are compared at that grain.
- **Relative date filters.** Metabase's "previous N units, including this one" is Looker's `N+1 units`; without the current unit it is `N units ago for N units`. Run both sides on the same day, and record `parity_as_of`.

## Pair: looker_studio_to_looker

This pair is experimental. The source side is the same as for `looker_studio_to_omni` below: each chart's Route C recording (`looker_studio_parity.py`), the expected rows for every connector. The target side is the LookML dashboard element's query through the Looker API or the Looker MCP `query` tool. Fill each contract from the model batch's `parity_map.json` (element, and recording column to Looker field), run the element with the recording's date range as an absolute filter, and declare grouped date keys in `comparison.dates.grain`. A chart with a breakdown dimension records only the series Looker Studio drew: compare that subset (every recorded row must be in the Looker result, with the same values) and record the series limit as an accepted difference.

## Pair: omni_to_looker

This pair is experimental (see `specs/migration/omni_source_audit/generate.md`).

- **Source side.** Each tile's saved query (`omni documents get-queries`), run as saved with raw values: `python3 <plugin-root>/scripts/omni_export.py tile-data --document <id> --query-key <key> --out <file>.csv`. It runs a pivoted tile unpivoted (long rows, which is what the contract compares) and writes `<file>.csv.status`: `truncated` when the result reached the tile's row limit, which makes the tile `INCONCLUSIVE`. A tile at its row limit (a top-N table, or a capped one) is re-run on both sides at a parity limit above its rows: `--limit 5000` here and the same limit on the Looker query, and recorded in the contract's `execution.limit`.
- **Target side.** The LookML dashboard element's query through the Looker API `run_inline_query` or the Looker MCP `query` tool, on the migration branch, with the element's own filters and without the dashboard filters' defaults (the Omni side runs without control values too).
- **Contracts.** Fill each from the model batch's `parity_map.json` (element, and Omni field to Looker field). Omni returns a date bucket as a date (`2026-10-01`) and Looker as the bucket's label (`2026-10`); declare each grouped date key in `comparison.dates.grain`.
- **Relative date filters.** Run both sides on the same day and record `parity_as_of`. A filter listed as an approximate date window in `needs_human.json` is confirmed before its tile can pass.

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. The source side is the same as for `tableau_to_looker` (Query View Data) and `metabase_to_looker` (card data) above. The target side is the Omni tile's query, read from the document draft (`omni documents v2-get-draft`) and run against the branch: `omni query run --body '{"query": <tile query with modelId>, "branchId": "<branch>", "resultType": "json", "formatResults": false}'`, so values are raw, not formatted. The JSON rows are keyed by field label: write them to CSV with the tile's `fields` as the header, in order. Fill each contract from the model batch's `parity_map.json` (source field to Omni field). Metabase returns a date bucket as the timestamp of its first day and Omni as a date; declare each grouped date key in `comparison.dates.grain` as a map from field to grain (`{<omni field>: month}`).

## Pair: looker_studio_to_omni

This pair is experimental in 4.2.2 (see `specs/migration/looker_studio_audit/generate.md`).

The source side is not re-run. Looker Studio offers no query API, so the expected result for each chart is its Route C recording, made during the audit capture:

- **Contracts.** Use `migration/parity/looker_studio/<report_id>/recordings/<key>/contract.yaml` (written by `looker_studio_parity.py`, `target_object` and `field_map` filled by `omni-content-generate`). The source result is the recording's `source.csv`.
- **Pinning.** Run the Omni tile with the contract's `execution.date_range` as fixed dates and `execution.timezone`, not with `parity_as_of`. A relative range in the report (for example "last 28 days") was resolved to fixed dates when it was recorded.
- **Data that moved since capture.** If late-arriving data changes the warehouse after the capture, a FAIL can be vintage, not logic. Re-capture the report (`looker-studio-audit-generate`, update mode) and re-run before investigating; record it as `diff_vintage` when the re-capture resolves it.
- **Ruled changes.** A tile whose metric changed under a metric catalogue ruling (including every `sum_of_ratio` finding) is `ACCEPTED_DIFFERENCE` with the ruling id from `decisions.md` as the reason.
- **Blocked.** Tiles on `pipeline` or `blocked` data sources with no warehouse copy are `BLOCKED` with that reason. Tiles with no recording are `NOT_RUN`.


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
| YYYY-MM-DD HH:MMZ | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time **in UTC**, written `YYYY-MM-DD HH:MMZ`
  (24-hour, a literal `Z` after the minutes, no `T`, no seconds, no offset):
  `2026-10-17 14:05Z`. Get it with `date -u +"%Y-%m-%d %H:%MZ"` (or
  `python3 <wire>/scripts/log_time.py now`), never from the local clock. The
  same form is used for every time written into a log row, including an
  original time quoted in Detail (`ran 2026-10-17 14:28Z`), in the release log
  and in ticket run logs. From Wire 4.4.3; see "Time zones" below.
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
  - `blocked` — `specs/utils/precondition_gate.md` Step 2 stopped the command on an unmet blocking precondition and the consultant chose not to override; Detail is `gate: <dep_artifact>.<dep_action> required <outcome>, was <actual>` and the Command cell carries the command in full. The Wire mod's commands band shows these rows as `Not run: <command>, gate: <...>`
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

  When a persona is set for the run (`specs/utils/personas.md`), add
  ` as <persona>` to the value: `typed as delivery-manager`,
  `orchestrator [a1b2c3] as delivery-manager`. No persona: the value alone.

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
| YYYY-MM-DD HH:MMZ | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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
   Rows are compared as "Time zones" below says.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Update `status.md` keys in place, then check the file.** When a command
   records a result in `status.md`, it changes the existing key; it never adds
   a second copy of a key in the same block. A value worth keeping (an earlier
   approval date) moves to a `prior_<key>` field or stays in this log, never
   in a duplicate key, because YAML keeps only the last copy and ignores the
   first without an error (wire-plugin#2). The same applies to anyone editing
   the file by hand or by script. After writing `status.md` and before
   appending the row, run `python3 <wire>/scripts/status_file.py check
   .wire/releases/<release_folder>`. If it reports a problem in a line this
   command just wrote, fix it now. If the problem was there before, leave it,
   say so in the output and point to `/wire:status-sync <release_folder>`
   (`specs/utils/status_sync.md` Step 1b). In orchestrated mode the
   orchestrating session runs the check when it writes `status.md` from a
   lane's state file.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.
9. **One time zone.** Every Timestamp, and every time quoted in Detail, is UTC
   with the `Z` suffix. A row is never written in local time, and a time
   with no zone is never converted by guessing the zone it was written in.
10. **Review rows say what they are.** A review result recorded from a merged
    pull request, not from a review command run, follows
    `specs/utils/status_sync.md` Step 4g: By is the approver, Detail says
    `recorded from PR #<n> approved by <name>`, and Session is what ran the
    roll-up.

## Time zones

From Wire 4.4.3 every Timestamp is UTC, `YYYY-MM-DD HH:MMZ`. Before that the
rule said local time, and logs mixed UTC rows with rows in the writer's local
time, so a ticket could appear to close before it opened.

- **Writing.** `date -u +"%Y-%m-%d %H:%MZ"`. A row's time is the UTC time the
  command finished. A roll-up row's Timestamp is the UTC time of the roll-up.
- **Rows with no zone.** `YYYY-MM-DD HH:MM` without `Z` is a row written
  before 4.4.3. It stays valid, is never rewritten, and is read as "zone
  unknown": it may be in any zone from UTC-12 to UTC+14.
- **Anything else** (`2026-10-17T14:05Z`, `14:05+01:00`, `14:05 BST`) is
  unparseable and reported as such.
- **Ordering** (rule 6, `/wire:status-sync` Step 4f). Two rows in the same
  form compare on the values written. A UTC row next to a zone-unknown row is
  out of order only when no zone in that range puts the pair in order; when
  some zones do and some do not, the pair is `zone_unknown`, listed for
  information and not a defect. A log that changes from local time to UTC in
  British summer time (`15:05` then `14:10Z`) is therefore not flagged.
- **Never earlier than the last row.** A roll-up stamps its rows with the
  later of now and the last row's time when the last row is UTC. A last row
  with no zone is not copied into a new row.

The rule is implemented in `<wire>/scripts/log_time.py` (`now`,
`check <execution_log.md>`), used by `ticket_delivery.py merge-log` and tested
by `wire/tests/core/validate_execution_log_order.py`. The Wire mod's metrics
backfill (below) reads both forms: it matches a row on its command and date,
with a day's slack, not on its time.

## Metrics Backfill (Claude Code)

From 4.1.0 the Wire mod (`hooks/register.ts`, a function hook in the Claude
Code plugin) fills the metric cells. It replaces the `Stop` settings hook
(`hooks/wire-metrics.sh` and `wire_metrics.py`), which re-read the session
transcript after each turn.

1. Each Wire command opens a run when it starts: a typed `/wire:` command, or
   a Wire command called through the Skill tool by the orchestrating session,
   a lane or Autopilot.
2. Every model request adds its measured usage to the run open in its own
   loop (the main session, or one subagent). Counts come only from the usage
   the API reports, never estimates.
3. When that loop's turn ends, the run closes and the mod fills the
   Duration (only if still `n/a`), Tokens and Cost cells of the newest row
   whose Command cell names the command, whose Tokens cell is still `n/a`, and
   which is dated no earlier than the day before the run started (a date, not
   a time, because commands write the row's time themselves and it is often
   rough). It
   never touches another cell or row, and never widens a row without the
   metric columns.
4. A row written after the run closed (an orchestrating session writing a
   lane's row once the lane reports) is filled when that write happens.
5. Cost comes from the mod's price table; an unrecognised model leaves Cost
   at `n/a` with Tokens filled.

`/wire-usage` prints the session's runs with their duration, tokens and cost;
`/wire-ran` prints each run in full with its result (4.5.0), as the band above
the prompt draws it. The plugin's `metrics` option, or `WIRE_METRICS=false`,
turns the backfill off. On runtimes without the mod (Gemini CLI), the metric cells keep the
values the workflow wrote.

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
| 2026-02-22 14:30Z | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35Z | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40Z | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12Z | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00Z | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15Z | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30Z | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00Z | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15Z | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00Z | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30Z | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45Z | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00Z | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05Z | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20Z | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
| 2026-02-25 11:02Z | /wire:data_model-generate | complete | ticket CUS-199, ran 2026-02-25 09:40Z: 4 tables | Jane Smith | orchestrator [d4e5f6] | 9m 12s | 201544 | $1.51 |
| 2026-02-25 11:02Z | /wire:data_model-review | approved | recorded from PR #64 approved by John Doe (ticket CUS-199, approved 2026-02-25 10:55Z) | John Doe | orchestrator [d4e5f6] | n/a | n/a | n/a |
```

The last two rows are a ticket roll-up (`specs/utils/status_sync.md` Step 4g)
run by an orchestrating session: the first was rolled up from the ticket's run
log; the second records a review result from the ticket's merged pull request,
so By is the approver, Session is the session that ran the roll-up, and the
metric cells stay `n/a` because no review command ran.
