---
description: Translate a batch of LookML views and explores to Omni views and topics on the model branch (deterministic converter plus agent judgement)
argument-hint: <release-folder> [--batch N 
---

# Translate a batch of LookML views and explores to Omni views and topics on the model branch (deterministic converter plus agent judgement)

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

## Workflow

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
