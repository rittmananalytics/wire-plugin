---
description: Translate a batch of LookML views and explores, or Tableau or Metabase content (experimental), to Omni views and topics on the model branch (deterministic converter plus agent judgement)
argument-hint: <release-folder> [--batch N | --all]
---

# Translate a batch of LookML views and explores, or Tableau or Metabase content (experimental), to Omni views and topics on the model branch (deterministic converter plus agent judgement)

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
    'command': 'omni-model-generate',
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
artifact: omni_model
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
      description: "--batch <id> translates one model batch (default: the next incomplete model batch); --all translates every incomplete model batch in order"
produces:
  - type: document
    path: "migration/omni_model/omni_model.md"
    description: "Batch summary: per batch, views and topics emitted, needs_human items open, branch commit"
  - type: report
    path: "migration/omni_model/<batch_id>/needs_human.json"
    description: "Converter report for the batch: every construct the script did not emit, with its class, reason and the plan ruling applied"
  - type: document
    path: "migration/omni_model/<batch_id>/relationships.yaml"
    description: "Emitted Omni relationships for the batch (alongside <SCHEMA>/<table>.view and <topic>.topic files in the same directory)"
preconditions:
  - artifact: omni_target_setup
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: Translate one batch of LookML views and explores into Omni views and topics on the model branch; the deterministic converter writes the mechanical YAML, and every construct it cannot emit becomes a needs_human item
argument-hint: <release-folder> [--batch <id> | --all]
---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_model` and `artifact_file_path: migration/omni_model/omni_model.md` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Looker: READ ONLY. This command reads the LookML repository at
  bi_migration.lookml_repo_path. It never writes to the Looker instance
  or to the LookML repository.

Omni: writes go to the MODEL BRANCH named in bi_migration.omni_branch,
  never to the published model. This command never merges the branch.
  Merging is a release director ruling, executed at cutover.

Warehouse: no queries. Validation queries belong to /wire:omni-model-validate.
```

If `bi_migration.omni_branch` is null, stop: `omni_target_setup` has not created the branch. Re-run `/wire:omni-target-setup-generate $ARGUMENTS`.

---

# Omni Model: Generate

## Purpose

Translates one batch of the Looker model into the Omni model. LookML views become Omni `.view` files, explores become `.topic` files, and joins become `relationships.yaml` entries, all written to the Omni model branch through the Omni CLI.

The translation has two halves and the split is deliberate. The mechanical half is a script: `wire/scripts/lookml_to_omni.py` reads the LookML, applies the pair's translation guide (`wire/bi_pairs/looker_to_omni/translation_guide.md`) and emits Omni YAML deterministically. Same input, identical output, no model call. The agent never hand-writes YAML the script can emit; a hand-written field is a field nothing can regenerate or test. The judgement half is what the script refuses: Liquid, parameters, persisted derived tables, joins Omni cannot express, `html`. Each of those arrives as a `needs_human` item, and the agent resolves it from the plan's rulings or parks it for the release director.

Omni differs from Looker in ways the emitted YAML must respect: there is no `${TABLE}` (a plain column dimension auto-maps by its column name and only derived fields carry `sql:`, referencing other fields as `${field}` or `${view.field}`); every view that takes part in a relationship needs a `primary_key: true` dimension, or Omni fans out aggregates silently; a measure filter is an operator object (`status: { is: complete }`), never a bare value. The lint step checks all three before validate spends a CLI call.

## Prerequisites

- `omni_target_setup review: approved`: the connection is verified, the schema is refreshed on it, and `bi_migration.omni_branch` names a branch created off the published model
- `bi_migration_plan review: approved`: `migration/bi_migration_batches.csv` exists and the rulings are recorded
- Omni CLI configured against the target profile with permission to write YAML on the branch (`omni whoami whoami` succeeds)
- `lkml` available to the converter (`python3 -c "import lkml"`)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` (`bi_migration.lookml_repo_path`, `bi_migration.omni_model_id`, `bi_migration.omni_branch`)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv` (rows with `batch_kind: model`)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (rulings: PDT disposition, redesign decisions, topic architecture)
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv` (the construct classes the audit assigned)
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- The LookML repository: `migration_sources.lookml.local_snapshot_path` when registered and refreshed, otherwise `bi_migration.lookml_repo_path`
- Pair files at `wire/bi_pairs/looker_to_omni/` and, when present, engagement overrides at `.wire/engagement/bi_pair_overrides/looker_to_omni/`

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. There is no LookML to convert. The Tableau reader (`twb_to_lookml.py`) or the Metabase reader (`mb_to_lookml.py`) works out the model from the source snapshot, and `bi_to_omni.py` writes the Omni files from it directly, with Omni naming. Step 2 runs, in place of `lookml_to_omni.py`:

```bash
python3 <plugin-root>/scripts/bi_to_omni.py convert --source tableau \
  --snapshot migration/source_snapshot/tableau/ --out migration/omni_model/<batch_id>/ \
  [--workbooks <ids>] [--datasets <ids>] --prefix <plan prefix> --bind query|schema
python3 <plugin-root>/scripts/bi_to_omni.py convert --source metabase \
  --snapshot migration/source_snapshot/metabase/ --out migration/omni_model/<batch_id>/ \
  --database <id> [--dashboards <ids>] --prefix <plan prefix> --bind query|schema
```

It writes one view per table or SQL source (`<view>.query.view` by default), one `.topic` per explore the reader built, `relationships.yaml`, `documents/<slug>.json` and `documents/<slug>.plan.json` (read by `omni-content-generate`), `needs_human.json`, `parity_map.json` and `conversion_summary.json`. A dimension on a table column takes the column's name and the source caption as its label; a measure or calculation whose name would collide with a column is suffixed; a raw column that a derived field reads is declared hidden; fields that use a parameter or templated filter, and fields inside a record column, are not emitted and are listed. Step 3 works through `needs_human.json` as above. In Step 4, the model's `relationships` file is shared by every topic: read it from the branch, append the batch's entries that are not already there, and write it back; never replace it.

## Pair: looker_studio_to_omni

This pair is experimental in 4.2.2 (see `specs/migration/looker_studio_audit/generate.md`).

Looker Studio has no semantic model to convert, so there is no converter step and no `needs_human.json` from a script. For a model batch (one subject area):

- **Source of the model.** The warehouse tables named by the plan's model route: the existing modelled tables (`map`), or the linked `dbt_development` release's warehouse models (`build`, which must have passed `dbt-validate`). Never the Looker Studio data sources themselves.
- **Measures.** One Omni measure per ruled metric-catalogue group in the subject area, named by `target_name`, implementing `canonical_formula` as a ratio of totals where it is a ratio. A ruled formula is written exactly; it is not improved.
- **Joins.** Each blend in scope becomes a modelled join at a stated grain, with the join keys from `report.json` (`blends[].tree.keys`). A blend whose join type code is unconfirmed is a `needs_human` item.
- **Authoring.** The agent writes the YAML with the `omni-model-builder` skill on the release branch. Because nothing deterministic emits it, every file must pass `/wire:omni-model-lint` and `/wire:omni-model-validate` before review; the batch summary lists each measure with the catalogue group it implements.
- **needs_human.** Write the batch's open items (unconfirmed join codes, pipeline data sources not yet in the warehouse, catalogue groups still parked) to `migration/omni_model/<batch_id>/needs_human.json` in the same shape the converter uses, so review and lint read one format.


### Step 1: Resolve the batch

Before anything else: if any earlier batch is `complete`, run `/wire:omni-model-reverse-port $ARGUMENTS` (`specs/migration/omni_model/reverse_port.md`) so this batch's cross-references read what is actually on the Omni branch. If `migration_sources.lookml.last_commit` differs from `looker_audit.lookml_commit`, warn that the LookML has moved since the audit and recommend `/wire:migration-drift-generate $ARGUMENTS` before translating; do not stop.

Read `migration/bi_migration_batches.csv` and keep the rows with `batch_kind: model`. Resolve scope:

- `--batch <id>`: that batch. Accept `b01` or `1`; record the zero-padded form.
- `--all`: every model batch not yet in `artifacts.omni_model.batches_complete`, in `batch_id` order, one at a time through Steps 2 to 7.
- No flag: the lowest-numbered model batch not yet complete.

If the batch's `depends_on_batch` names a batch that is not complete, stop and name it. The batch's `object_type: view` and `object_type: explore` rows are the scope for the converter's `--views` and `--explores` arguments. A row with `ruling: drop` is excluded and its register row is set to `state: removed` with the reason in `notes`.

### Step 2: Run the converter

```bash
python3 <plugin-root>/scripts/lookml_to_omni.py \
  --lookml "<resolved LookML path: migration_sources.lookml.local_snapshot_path, else bi_migration.lookml_repo_path>" \
  --out ".wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>" \
  --views "<comma-separated view names>" \
  --explores "<comma-separated explore names>" \
  --overrides ".wire/engagement/bi_pair_overrides/looker_to_omni" \
  --report ".wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json" \
  --project "<LookML project name, as in the audit catalog's object_uri values>"
```

`<plugin-root>` is the installed Wire plugin directory (the converter ships at `scripts/lookml_to_omni.py`). The output directory follows the Omni model repo layout: `<SCHEMA>/<table>.view`, one `<explore>.topic` per explore, and one `relationships.yaml`. The `--overrides` directory is optional; when absent the canonical pair tables apply alone.

Beside the model files the converter writes its **intermediate representation**: `ir/views/<view>.json` and `ir/topics/<topic>.json`, one per LookML view and explore in the batch whether or not anything was emitted for it. Each field record carries its identity (`looker:<project>:field:<view>:<field>`, the same namespace as the audit's `object_uri`), its LookML type and SQL, the fields it references, its class (`mechanical`, `assisted`, `redesign`), whether it was emitted, the Omni body that was emitted, and every unsupported construct as a typed entry (construct, class, reason). Nothing disappears into a guess: a field the converter could not translate is still in the IR with the reason. `omni-model-review` reads the IR, not the `.view` files, to show class per field. `dependencies.jsonl` (`view` contains `field`, `field` references `field`, `topic` base_view, `topic` joins `view`, `topic` join_on `field`) is the model half of the release's dependency graph; the audit writes the content half in the same format. `conversion_summary.json` records `converter_version`, which the baseline and every evidence fingerprint carry.

The converter exits non-zero on a LookML parse failure. Do not patch the LookML to make it parse: record the file and line, exclude the view from the batch, and report it. A file that does not parse is a finding for the audit, not something to fix here.

### Step 3: Read the needs_human report

`needs_human.json` lists every construct the converter did not emit, or emitted with a flag:

```json
{
  "batch_id": "b01",
  "items": [
    {"id": "nh-001", "class": "redesign", "construct": "liquid_in_sql", "view": "orders", "field": "region_label",
     "lkml_file": "views/orders.view.lkml", "line": 41, "reason": "Liquid template in sql",
     "omni_alternative": "templated filter on the topic, or a groups dimension", "status": "open"},
    {"id": "nh-002", "class": "assisted", "construct": "derived_measure", "view": "orders", "field": "aov",
     "emitted": true, "reason": "type: number measure emitted without aggregate_type; confirm at validate", "status": "open"}
  ]
}
```

For each item, apply the plan's rulings in this order:

1. A ruling in `bi_migration_plan.md` that names the view or field (PDT disposition, redesign decision, drop) resolves the item. Record `status: resolved`, `ruling_ref` and what was done: for a PDT ruled to dbt, the view is emitted against the dbt model's table; for a PDT ruled to an Omni query view, write the query view YAML by hand in the batch directory (the one place hand-written YAML is expected, because the converter does not emit query views) and record its path on the item.
2. An `assisted` item with `emitted: true` stays `open` until validate confirms it; nothing to do here.
3. Anything else stays `open` and becomes a parked decision for the release director (`parked_decisions` in status.md, `kind: ruling`, question naming the view, field and the Omni alternative). Do not guess a redesign. A guessed redesign passes validate and returns wrong numbers in parity, which is the most expensive place to find it.

An item of class `redesign` must have no emitted counterpart in the batch directory. The lint step checks this.

### Step 4: Write the batch to the Omni branch

For every emitted file, in this order (views, then relationships, then topics, so each topic's `base_view` and joins already exist):

```bash
omni models yaml-create <bi_migration.omni_model_id> \
  --body "$(python3 -c 'import json,sys; print(json.dumps({"path": sys.argv[1], "yaml": open(sys.argv[2]).read()}))' "<SCHEMA>/<table>.view" "<local file>")" \
  --branch-id <bi_migration.omni_branch>
```

Use the exact path each time. A path that does not match an existing file creates a duplicate rather than an edit, and the duplicate is silent. After each write, read the file back:

```bash
omni models yaml-get <bi_migration.omni_model_id> --file-name "<SCHEMA>/<table>.view" --branch-id <bi_migration.omni_branch> --mode extension
```

Confirm the read-back matches the local file and that `omni models get-views` lists the view once. A second run of this command for the same batch is an edit, not a create: read first, write the same path.

Never run `omni models merge-branch` or `omni models commit` here. The branch is merged at cutover, on the release director's ruling, after parity passes.

### Step 4b: Write the batch manifest

After the write to the branch, write `migration/omni_model/<batch_id>/manifest.json`: one entry per emitted file with `path`, `emitted_sha` (SHA-256 of the file as written), `written_at`, `branch_id` and `lookml_commit` (the snapshot's `last_commit`), plus a header with `converter_version` and `ir_sha` (SHA-256 over the batch's `ir/` directory). `emitted_sha` is the `target_definition` component of every evidence fingerprint for objects in the batch. `omni-model-reverse-port` reads it to tell a client edit from a local one.

### Step 5: Update the register

For each view and explore in the batch, update its row in `migration/migration_register.csv` (object_type `view` or `topic`): `state: migrated` when its YAML is on the branch, `last_migrated_commit` set to the LookML snapshot's `last_commit` (the commit the converter read; `null` and a note when the source is not a git repository), `notes` carrying the batch id. A view whose only emission is a parked `needs_human` item is `state: deferred` with the item id in `notes`. Register writes follow the single-writer rule in `specs/migration/equivalency/verdict_schema.md`: under the release director model the orchestrating session writes the register from this lane's state file; outside it, this command writes the rows itself.

### Step 6: Write the batch summary

Append (or replace the batch's row in) `migration/omni_model/omni_model.md`:

```markdown
## Batch summary

| Batch | Views emitted | Topics emitted | Relationships | needs_human open | needs_human resolved | Branch | Written |
|---|---|---|---|---|---|---|---|
| b01 | 14 | 3 | 9 | 2 | 5 | feat/looker-to-omni | 2026-09-04 |

## needs_human (open)

| Item | Batch | View.field | Class | Reason | Parked decision |
|---|---|---|---|---|---|
| nh-001 | b01 | orders.region_label | redesign | Liquid template in sql | PD-4 |
```

Also record every construct the converter emitted with a flag (`assisted`) in a third table, so validate knows what to confirm.

### Step 7: Update status

```yaml
artifacts:
  omni_model:
    generate: complete          # complete only when every model batch is written; otherwise in_progress
    file: migration/omni_model/omni_model.md
    generated_date: "{{TODAY}}"
    batches_total: N
    batches_complete: [b01]
    views_emitted: N
    topics_emitted: N
    needs_human_open: N
    lint: not_started           # reset for the batch just written
    validate: not_started
```

`generate: complete` is set only when `batches_complete` covers every model batch in the plan. Until then it is `in_progress`, and the precondition gate on `omni_content` reads `validate`, not `generate`, so content for an early batch can start once that batch validates.

### Step 8: Output next command

```
Batch <batch_id> written to branch <bi_migration.omni_branch>.
  Views <N>, topics <N>, relationships <N>. needs_human open: <N> (parked decisions: <ids>).

Validate did not run (this artifact opts out of automatic validation because
validate calls the Omni CLI). Next:
/wire:omni-model-lint $ARGUMENTS --batch <batch_id>
/wire:omni-model-validate $ARGUMENTS --batch <batch_id>
```

## Under the release director model

This command is one **model slice** lane (`specs/utils/director_operating_model.md`). The lane brief names the batch, owns `migration/omni_model/<batch_id>/` and its state file, and carries no warehouse budget line (this command runs no queries). The lane reports once: the counts in Step 8, and the parked decisions it could not resolve. It does not write `status.md` or the register when `WIRE_INVOKED_BY=lane`; the orchestrating session does, from the lane's state file.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/<SCHEMA>/<table>.view` (one per view)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/<explore>.topic` (one per explore)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/relationships.yaml`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/ir/views/<view>.json`, `ir/topics/<topic>.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/dependencies.jsonl`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/conversion_summary.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/manifest.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/omni_model.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact_id, `Omni Model` as artifact_name, and the `file` value from `artifacts.omni_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `generate` as action.

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
