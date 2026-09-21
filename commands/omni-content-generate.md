---
description: Plan and create Omni dashboards for a batch of Looker dashboards and Looks; skipped tiles listed with reasons
argument-hint: <release-folder> [--batch N 
---

# Plan and create Omni dashboards for a batch of Looker dashboards and Looks; skipped tiles listed with reasons

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
    'command': 'omni-content-generate',
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
artifact: omni_content
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
      description: "--batch <id> plans (and, once validated, writes) one content batch; --all processes every incomplete content batch in order; --write executes the write step for a batch whose plan has validated"
produces:
  - type: document
    path: "migration/omni_content/omni_content.md"
    description: "Batch summary: per batch, dashboards planned and created, tiles planned, tiles skipped by reason"
  - type: report
    path: "migration/omni_content/<batch_id>/plan.json"
    description: "The dry-run plan for the batch: per dashboard, the Omni document body to create, the control map, and every skipped tile with its reason"
  - type: report
    path: "migration/omni_content/<batch_id>/manifest.csv"
    description: "One row per dashboard: source_id, target_identifier, state (planned | created | failed), tile counts"
preconditions:
  - artifact: omni_model
    action: validate
    outcome: PASS
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: Rebuild one batch of Looker dashboards as Omni documents against the translated model, as a plan first and a write second; every tile that cannot be rebuilt programmatically is listed with its reason, never dropped silently
argument-hint: <release-folder> [--batch <id> | --all] [--write]
---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_content` and `artifact_file_path: migration/omni_content/omni_content.md` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Looker: READ ONLY. Dashboard definitions are read through the Looker API
  (or the Looker MCP). Nothing on the Looker instance is edited, moved,
  or deleted. Looker stays live as the rollback path until cutover.

Omni: the plan step writes NOTHING to Omni. The write step (--write) creates
  NEW documents only, in the folder the plan names. It never edits or deletes
  an existing Omni document, and it touches only documents whose
  target_identifier it recorded itself in manifest.csv.

Warehouse: the plan step runs no queries. The write step runs none either;
  Omni renders tiles when a user opens the document.
```

If a planned document's title matches an existing Omni document in the target folder, the plan records `collision: true` and the write step refuses that dashboard until the release director rules (rename, replace, or skip).

---

# Omni Content: Generate

## Purpose

Rebuilds Looker dashboards and Looks as Omni documents on the translated model. The command is split in two on purpose, the same way the Metabase carve-out transport is (`specs/migration/metabase_carveout/transport_generate.md`): a **plan** that decides every tile's fate and writes nothing to Omni, a **validate** that checks the plan against the branch, and a **write** that executes only a validated plan. The plan is the dry run. Nothing is created in Omni until `/wire:omni-content-validate` has passed for the batch and this command is re-run with `--write`.

What the rebuild can and cannot do is fixed by Omni's document API and by what the model carries. A tile whose every field exists on the branch becomes a `queryPresentation`; dashboard filters become `controls` with per-tile `map` entries; the layout becomes a `containers` tree. A text or markdown tile becomes an `inline-text` content item when its markdown is plain, and a listed manual item when it uses Liquid. A tile that references a field the model does not have is skipped with reason `unmapped_field`, and the model batch is where that is fixed, not here.

## Prerequisites

- `artifacts.omni_model.validate: pass` for the model batch this content batch depends on (the gate reads the overall value; when model batches are still in progress, the plan's `depends_on_batch` names the model batch and its presence in `batches_validated` is what this command checks)
- `omni_model review: approved` before the write step (the plan may be produced earlier)
- Looker API credentials (`LOOKERSDK_BASE_URL`, `LOOKERSDK_CLIENT_ID`, `LOOKERSDK_CLIENT_SECRET`) or the Looker MCP connected
- Omni CLI configured against the target profile

## Inputs

- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv` (rows with `batch_kind: content`)
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv` (dashboards, Looks, tiles, folders, usage)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<model batch>/**` (emitted views and topics; the field namespace)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (parity-or-redesign ruling per dashboard, target folder structure)
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- `wire/bi_pairs/looker_to_omni/content_mapping.md` (tile type to `chartType`, filter kinds, control types)
- `wire/bi_pairs/looker_to_omni/tooling.md` (Omni's dashboard inspector and builder scripts, and how this command may use them)
- `wire/bi_pairs/looker_to_omni/content_mapping.md`, section "Rules from Omni's own dashboard migration guide": every control in every tile's map, no quarter-grained date keys, hidden fields left out of `fields`, table pivots in `query.pivots` and chart pivots as the series field, parameters as Mustache block templated filters, never delete by name
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Resolve the batch

Read `migration/bi_migration_batches.csv` and keep `batch_kind: content` rows. `--batch <id>` selects one batch (`b05` or `5`); `--all` processes every content batch not in `artifacts.omni_content.batches_complete`; no flag selects the lowest incomplete one. Confirm the batch's `depends_on_batch` (a model batch) is in `artifacts.omni_model.batches_validated`; stop and name it otherwise.

Rows with `ruling: drop` are excluded and their register rows set to `state: removed`. Rows with `ruling: redesign` are planned only when the plan document carries the redesigned tile list for that dashboard; otherwise they are parked (`kind: ruling`) and skipped this run.

### Step 2: Read each dashboard from Looker

For each dashboard row, fetch the definition through the Looker API: `dashboard(id)` for elements, filters and layout; each element's `query` or `result_maker` for fields, filters, sorts, pivots, limits, table calculations and visualisation config; `dashboard_filters` and each element's `listen` map. Omni's `looker_dashboard_inspect.py` (see `wire/bi_pairs/looker_to_omni/tooling.md`) prints the same structure and may be used as the extractor. For a Look, fetch `look(id).query` and treat it as a one-tile dashboard.

Record the raw definition alongside the plan (`migration/omni_content/<batch_id>/source/<dashboard_id>.json`) so validate and parity can re-derive from it without another Looker call.

### Step 3: Map every tile

For each tile, in this order:

1. **Fields.** Map each Looker `view.field` to the Omni `view.field` on the branch. The view name is the emitted view's name (the converter preserves it unless the plan renamed it, in which case the plan's rename table applies); a dimension group timeframe `created_month` maps to `created_at[month]`. A field that does not exist on the branch skips the tile with reason `unmapped_field`, naming the field. Do not substitute a similar field.
2. **Filters.** Tile filters and dashboard filters become Omni filter objects (`{ "kind": "EQUALS", "type": "string", "values": [...] }`, `{ "type": "date", "kind": "TIME_FOR_INTERVAL_DURATION", ... }`), never the shorthand string. A filter expression the mapping table does not cover skips the tile with reason `unmapped_filter`.
3. **Table calculations.** Arithmetic and `CASE`-shaped calculations become Omni `calculations`; a calculation referencing `pivot_where`, `offset`, or another calculation is `unsupported_calc`.
4. **Visualisation.** Map the Looker `type` to `chartType` and `visType` through `content_mapping.md`, with the chart spec nested under `visConfig.visConfig.config` and `prefersChart: true`. A pivoted bar becomes a stacked bar with the pivot dimension in `query.pivots`. A type with no mapping row becomes `chartType: table` and the tile is flagged `fidelity: table_fallback`, never skipped.
5. **Text and markdown tiles.** Plain markdown becomes an `inline-text` content item in `containers`. Markdown containing Liquid (`{{ }}` or `{% %}`) is skipped with reason `liquid`; Omni's Mustache namespaces differ and the rewrite is a hand job, listed in the report.
6. **Query collection.** Every tile query carries the full required set: `table`, `fields`, `join_paths_from_topic_name` (the topic name), `limit`, `sorts`, `filters`, `pivots`, `calculations`, `column_totals`, `row_totals`, `fill_fields`, `userEditedSQL`. No `modelId` in a tile query.

### Step 4: Map controls and layout

Dashboard filters become `controls.data` entries with `config.type` by filter kind (`date`, `string`, `number`, `boolean`). Each element's `listen` map becomes the control's `map`: tile keys the filter applies to, with a field remap where the Looker filter listened on a different field. A tile the filter did not listen to is excluded with `{ "<tileKey>": false }`.

The layout becomes a full `containers` tree from the Looker element positions (row, column, width, height on the 24-column grid, scaled to Omni's grid per `content_mapping.md`). Auto-layout places only the first tile, so the tree is authored in full for every tile and every text item.

### Step 5: Write the plan

`migration/omni_content/<batch_id>/plan.json`:

```json
{
  "batch_id": "b05",
  "model_batch": "b01",
  "branch_id": "<bi_migration.omni_branch>",
  "dashboards": [
    {
      "source_id": "42", "source_type": "dashboard", "title": "Store Performance", "folder": "Retail",
      "ruling": "parity", "collision": false,
      "body": { "queryPresentations": {"data": {}, "order": []}, "controls": {"data": {}, "order": []}, "containers": [], "settings": {} },
      "tiles_planned": 9,
      "skipped": [
        {"element_id": "7", "title": "Notes", "reason": "liquid", "detail": "{{ _filters['orders.created_date'] }} in markdown"},
        {"element_id": "9", "title": "Margin %", "reason": "unmapped_field", "detail": "orders.margin_pct not on branch (needs_human nh-014)"}
      ],
      "fidelity": [{"element_id": "3", "note": "table_fallback: looker_waterfall has no Omni chartType"}]
    }
  ]
}
```

The plan is complete when every in-scope dashboard has either a body or a parked ruling, and every skipped tile has a reason from the closed set `text_tile`, `liquid`, `unsupported_calc`, `unmapped_field`, `unmapped_filter`. Write `manifest.csv` with one row per dashboard, `state: planned`.

Update `omni_content.md` and status.md (Step 7), then output:

```
Plan written for batch <batch_id>: <N> dashboards, <N> tiles planned, <N> skipped.
Nothing has been written to Omni. Next:
/wire:omni-content-validate $ARGUMENTS --batch <batch_id>
then /wire:omni-content-generate $ARGUMENTS --batch <batch_id> --write
```

Stop here unless `--write` was passed.

### Step 6: Write step (`--write`)

Refuse unless `artifacts.omni_content.plan_validated` lists this batch and `omni_model review: approved`. For each dashboard with `collision: false` and a body:

```bash
omni documents v2-create <bi_migration.omni_model_id> "<title>" --body "$(cat migration/omni_content/<batch_id>/bodies/<source_id>.json)"
```

The body is one JSON object with nested slices, never stringified slices. Capture the returned `identifier`; read it back with `omni documents v2-get <identifier>` and confirm the tile count equals `tiles_planned` and every control is present. Move the document to the plan's folder with `omni documents move`. Record `target_identifier`, `target_url` and `state: created` in `manifest.csv`. A create that fails records `state: failed` with the error text and continues with the next dashboard; it does not retry blindly.

Omni's `omni_dashboard_builder.py` may be used as the write mechanism instead of the CLI call above when the engagement has it installed (see `wire/bi_pairs/looker_to_omni/tooling.md`); the plan body is the input either way, and the read-back check is the same.

Advance register rows: the dashboard row (`object_type: dashboard`) and its tile rows (`object_type: tile`) to `state: migrated`, skipped tiles to `state: deferred` with the reason in `notes`.

### Step 7: Update the summary and status

`migration/omni_content/omni_content.md`:

```markdown
## Batch summary

| Batch | Dashboards planned | Created | Tiles planned | Skipped: text | liquid | calc | field | filter | Table fallbacks |
|---|---|---|---|---|---|---|---|---|---|
| b05 | 6 | 6 | 47 | 3 | 2 | 1 | 2 | 0 | 4 |

## Hand-finish list
| Dashboard | Element | Reason | What to do in Omni |
```

```yaml
artifacts:
  omni_content:
    generate: complete          # complete only when every content batch has state created for all its dashboards
    file: migration/omni_content/omni_content.md
    generated_date: "{{TODAY}}"
    batches_total: N
    batches_complete: [b05]
    plan_validated: [b05]       # written by omni-content-validate
    dashboards_planned: N
    dashboards_created: N
    tiles_skipped: N
```

### Step 8: Output next command

After a write:
```
Batch <batch_id> created in Omni: <N> documents. Hand-finish list: <N> items.
Next: /wire:omni-content-validate $ARGUMENTS --batch <batch_id>   (post-write checks)
then /wire:bi-equivalency-validate $ARGUMENTS --batch <batch_id>
```

## Under the release director model

This command is one **content batch** lane. The brief owns `migration/omni_content/<batch_id>/` and its state file, and carries no warehouse budget line. Each dashboard is one item for the resume contract: a killed lane resumes at the first dashboard with no `state` in the manifest. The lane reports once per step (plan written; write complete) with the skipped and hand-finish counts, and parks the collision and redesign rulings it cannot make.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/plan.json`
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/bodies/<source_id>.json` (one per dashboard)
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/source/<dashboard_id>.json` (raw Looker definitions)
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/manifest.csv`
- `.wire/releases/$ARGUMENTS/migration/omni_content/omni_content.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact_id, `Omni Content` as artifact_name, and the `file` value from `artifacts.omni_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_content` as artifact, `generate` as action.

Execute the complete workflow as specified above.
