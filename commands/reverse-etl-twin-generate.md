---
description: Author the target-warehouse twin config per in-scope sync — additive, paused, decoy-pointed, model translated, manifest keyed on the normalised sync id
argument-hint: <release-folder> [--wave id] [--syncs a,b] [--dry-run]
---

# Author the target-warehouse twin config per in-scope sync — additive, paused, decoy-pointed, model translated, manifest keyed on the normalised sync id

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
    'command': 'reverse-etl-twin-generate',
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
command: generate
artifact: reverse_etl_twin
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
  - artifact: reverse_etl_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Author the target-warehouse twin config for each in-scope reverse-ETL sync — additive, paused, decoy-pointed, model translated, with a manifest keyed on the normalised sync id
argument-hint: <release-folder> [--wave id] [--syncs a,b] [--dry-run]

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_twin` and `artifact_file_path: migration/reverse_etl_twin_manifest.csv` before proceeding.

---

## Data Safety — Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command WRITES config files. Three things it never does:

  1. It never modifies an existing sync's config file. The existing
     source-warehouse sync is the rollback path until cutover.
  2. It never writes a live shared destination id into a twin. Decoy-mode
     twins carry decoy ids only, and the decoy must be the same destination
     type. A sync the plan's mapping marks destination_mode: dedicated is
     the one exception: its twin carries the confirmed dedicated destination
     id — a destination the plan's gate proved no existing sync writes to.
  3. It never enables or unpauses a sync. Every twin is authored paused.
     Enabling is the client's decision and is not a command's side effect.

Target warehouse: [migration.target_project]
```

If any step would modify an existing sync file, write a live shared destination id (or, on a decoy-mode sync, any production destination id), or set a twin to enabled, stop and report the conflict before writing anything.

---

# Reverse ETL Twin — Generate

## Purpose

`reverse-etl-migration-generate` produces the plan: topology, target source connection, decoy mapping, the additive first PR. Nothing then wrote the copies. On one engagement, **575 of 643 twins were written by hand**, one file at a time, across unmerged branches — the single largest cost in the reverse-ETL path and the only step in the sequence with no command behind it. Because nothing generated them, nothing validated them either: a later by-hand sweep of 621 branch copies found 22 with an upper-case `primaryKey`, each of which would have run successfully and sent nothing.

This command authors the twins. It is deliberately narrow: it writes new config files and a manifest, and it does not enable, promote, or validate. Validation is `reverse-etl-migration-validate` (the `primaryKey` casing rule and the destination-set check), equivalence is `reverse-etl-equivalency-validate`, and enabling is the client's.

## Prerequisites

- `reverse_etl_migration review: approved` — the plan this command executes against
- `migration/reverse_etl_decoy_mapping.csv` exists (`_{wave_id}.csv` under `--wave`), with a non-blank `decoy_destination_id` for every decoy-mode sync in scope (`destination_mode: dedicated` rows carry blank decoy columns by design)
- The Hightouch config repo is checked out on the working branch `reverse-etl-migration-generate` Step 3 created — twins are committed there, never to the default branch
- `topology: additive_repo` or `additive_dedicated_destination`. Under `parallel_workspace` or `in_place_repoint` there are no additive twin files to author: stop with `[wire] reverse-etl-twin-generate authors additive twin configs; topology is <topology>. Nothing to author.`

## Flags

- `--wave <id>` — restrict to the syncs `migration/migration_batching.csv` assigns to this wave, resolved identically to `reverse-etl-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Wave-labelled manifest (`migration/reverse_etl_twin_manifest_{wave_id}.csv`).
- `--syncs a,b` — author only the named syncs (original sync ids, normalised per Step 0). Mutually exclusive with `--wave`; abort if both are supplied: `[wire] --wave and --syncs cannot be combined. Pick one.`
- `--dry-run` — print the per-sync plan (source file, twin path, decoy id, approach, translated-model summary) and write nothing.
- No flag — every sync the plan carries with `include_in_migration: true` that is not already twinned.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.csv` — the sync inventory: `sync_id`, `model_*`, `destination_*`, `primaryKey` where recorded, `warehouse_objects`, `migration_approach`
- `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md` — the approved plan: topology, per-sync approach, translations recorded there
- `.wire/releases/$ARGUMENTS/migration/reverse_etl_decoy_mapping.csv` — production → decoy destination id per sync, same destination type
- The Hightouch config repo working branch — existing sync/model config files, read to mirror their shape
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` — under `migration.scope == tenant_carveout` only

## The sync id join key (Step 0)

Every artifact in the reverse-ETL path keys on the **normalised original sync id**, and this command is where that normalisation is pinned, because a twin's own filename carries a marker the audit's key does not:

1. Take the config file basename and strip the extension.
2. Strip a trailing target-warehouse marker: `-bq`, `_bq`, `-bigquery`, `_bigquery` (case-insensitive).
3. Lower-case the result.

A raw-string join between authored twins and the audit matched 6 of 609 on one engagement; the normalised join matched 575 of 643, with the residual explained (syncs classified `decommission` never get a twin). Record both the original id and the twin id in the manifest so no consumer has to re-derive the rule, and so the join to the register's `reverse_etl_sync` rows, which `migration-register-generate` seeds on the same key (wire#191), works unchanged.

## Workflow

### Step 1: Resolve scope and refuse to re-author

Resolve the sync set per **Flags**. Read any existing manifest and skip syncs already twinned unless their source config has changed since (compare the recorded source-file hash). Print the resolved list — sync id, approach, twin path, decoy id — before writing anything.

Route every sync by its `migration_approach`, per the closed vocabulary in `specs/utils/reverse_etl_approach.md`. A sync whose approach is **`decommission`** is **not twinned**: print it as skipped (`[wire] <sync>: approach decommission — no twin authored.`) and carry it to `reverse-etl-retire-generate`, which lists it on the classified-retirement ground. Twinning a sync that is being switched off is work with a negative return, and on one release that would have been 98 of them. An approach outside the closed set is an error naming the value and the sync, never a fall-through to authoring.

### Step 2: Author one twin per sync

For each in-scope sync, write a **new** config file alongside the existing one, at the same relative path with the twin id as its basename. Never open the existing file for writing.

1. **Source connection** — the target-warehouse source added by the plan's Step 3. Never the source-warehouse connection.
2. **Destination** — by the mapping row's `destination_mode`. `decoy` (the default): the `decoy_destination_id` from the mapping, whose `decoy_destination_type` must equal the sync's `production_destination_type`. A blank decoy id, or a type mismatch, is a hard stop for that sync: record it under **Not authored — decoy missing or wrong type** and continue with the rest. Do not substitute a different type, and do not fall back to the production id. `dedicated` (under `additive_dedicated_destination` only): the confirmed dedicated destination id from the mapping row — the missing-decoy reason does not apply, because a dedicated row's blank decoy columns are by design, not a defect. Pausing (item 3) is mode-independent: a dedicated twin is authored paused like any other, and no command enables it.
3. **Paused** — whatever the config format's disabled/paused representation is, the twin is authored in it. This is not a default that a later step flips: no command in Wire enables a reverse-ETL sync.
4. **Model** — by approach, from the approved plan: `repoint` carries the model SQL unchanged against the target source; `rewrite_model` carries the translated SQL the runbook recorded (do not re-derive it here — the runbook's translation is the reviewed one); `rebuild` is out of scope for this command, since a Customer Studio rebuild is not a file copy. List `rebuild` syncs as **Not authored — rebuild approach** and leave them to the runbook's rebuild steps.
5. **`primaryKey`** — carry the sync's configured key through, applying the casing rule below.
6. **Field mapping, filters, computed fields, match rules** — carried through unchanged. This command copies sync-level logic; it does not redesign it. `reverse-etl-migration`'s Step 6 review and `reverse-etl-equivalency-validate`'s changed-field hashes are what confirm it.

Under `migration.scope == tenant_carveout`, resolve the sync's tenant filter from the predicate registry exactly as models do (`specs/utils/tenant_predicate_registry.md`). A sync whose registry row is `unresolved` is **not authored** — recorded under **Not authored — unresolved predicate**, never authored unfiltered.

### Step 2a: The `primaryKey` casing rule (error severity)

On a BigQuery-source Hightouch sync, a `primaryKey` containing any upper-case character makes the sync run successfully and send **nothing**. It is the failure mode that looks exactly like success, which is why it is error severity and why it is applied at authoring time as well as in validation.

Resolve the key's correct casing from the target model's actual column list (the compiled schema, not the source config's spelling). If the target column exists in a different case, write the target's casing and record the correction in the manifest (`primary_key_corrected: true`). If the key cannot be resolved against the target's columns at all, **do not author the twin**: record it under **Not authored — primaryKey unresolvable on target** with the key and the columns that were searched. Guessing a casing here is the same defect with an extra step.

Rule id `REVERSE_ETL_PRIMARY_KEY_CASE`, evaluated here at authoring time and again by `reverse-etl-migration-validate` Check 13 over what is actually on the branch — the second pass exists because twins written by hand, before or outside this command, are exactly the population the 22 defects came from.

### Step 3: Write the twin manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_etl_twin_manifest.csv` (`_{wave_id}.csv` under `--wave`)

```
sync_id,twin_id,twin_path,source_path,source_file_sha,approach,
target_source_id,decoy_destination_id,decoy_destination_type,
destination_mode,dedicated_destination_id,
production_destination_type,primary_key,primary_key_corrected,
paused,model_translated,tenant_mechanism,authored_date,state,not_authored_reason
```

`sync_id` is the normalised original id from Step 0 — the join key to the audit, and to the register's `reverse_etl_sync` rows (wire#191). `state` is `authored | not_authored`. Every `not_authored` row carries its reason; a blank reason on a `not_authored` row is itself a defect. `destination_mode` mirrors the mapping row (`decoy | dedicated`); `dedicated_destination_id` is blank unless the mode is `dedicated`, in which case it is the id the twin points at and both decoy columns are blank.

### Step 4: Summarise and hand off

Print counts: authored, skipped (already twinned / retire approach), not authored by reason. Then:

```
Twins authored: <n> (paused; decoy destinations, or confirmed dedicated destinations for dedicated-mode syncs)
Validate them before raising anything:
/wire:reverse-etl-migration-validate $ARGUMENTS
```

Do not open a PR here. The plan's PR sequence (Step 8 of the runbook) owns that, and a twin batch that has not been through Check 13 and Check 14 is not ready to raise.

### Step 5: Update status

```yaml
artifacts:
  reverse_etl_twin:
    generate: complete
    generated_date: "{{TODAY}}"
    file: migration/reverse_etl_twin_manifest.csv   # or _{wave_id}.csv under --wave
    twins_authored: N
    twins_skipped: N
    not_authored: N
    not_authored_reasons: {decoy_missing_or_wrong_type: N, rebuild_approach: N, unresolved_predicate: N, primary_key_unresolvable: N}
    primary_key_corrections: N
    all_paused: true          # false is a defect, not a state — investigate before proceeding
    wave: "B01"               # set only when run with --wave
    waves_complete: ["B01"]   # set only when run with --wave; accumulates across runs
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_etl_twin_manifest.csv` (`_{wave_id}` suffix under `--wave`)
- New twin config files on the Hightouch config repo's working branch, alongside the existing sync configs
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_twin` as artifact, `generate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_twin` as artifact, `generate` as action.

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
