---
description: Upgrade a release folder's status.md to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values
argument-hint: [release-folder] [--dry-run]
---

# Upgrade a release folder's status.md to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values

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
    'command': 'upgrade',
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
command: lifecycle
artifact: upgrade
domain: upgrade
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Upgrade a release folder's status.md and Wire files to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values
argument-hint: [release-folder]

delegates_to:
  - utils/director_operating_model
---

# Wire Upgrade Command

## Purpose

Bring an existing release folder up to date with the schema introduced by the currently installed Wire plugin. Safe to re-run at any time.

What it does:
- Reads `status.md` and detects the release type
- Compares the current status.md against the canonical template for that release type
- Adds any top-level sections and nested keys that are missing, using `not_started` / `null` defaults
- Stamps `wire_plugin_version` and `last_upgraded_at` into the frontmatter
- Reports what was added and surfaces new commands that weren't available when the release was created
- Never overwrites values that already exist

What it does not do:
- Modify artifact files (requirements.md, data_model.md, etc.)
- Re-generate any artifacts
- Change existing status values
- Alter engagement-level files (`.wire/engagement/context.md`)

## Usage

```bash
/wire:upgrade 20260210_acme_analytics   # upgrade a specific release folder
/wire:upgrade                            # auto-detect the most recently modified release
/wire:upgrade --dry-run 20260210_acme   # show what would change without modifying anything
```

`--dry-run` prints the diff as a YAML patch and exits without writing.

## Prerequisites

- `.wire/` directory exists in the current repo
- The named release folder exists under `.wire/releases/`

---

## Workflow

### Step 1: Resolve the Release Folder

If a `<release-folder>` argument is provided:
1. Look for `.wire/releases/<release-folder>/status.md`
2. If not found, try `.wire/<release-folder>/status.md` (pre-v3.4 flat layout — redirect the user to `/wire:migrate` first)

If no argument is provided:
1. Glob `.wire/releases/*/status.md`
2. Sort by `last_modified` descending — take the first result
3. Confirm with the user:
   ```
   No release folder specified. Found: <folder-name> (last modified <date>)
   Upgrade this release? (yes/no)
   ```

Set `release_folder` and `status_path`.

---

### Step 2: Read Current Status

Read and parse the YAML frontmatter of `status_path`.

Extract:
- `release_type` — the release type identifier (e.g. `full_platform`, `droughty`, `platform_migration`)
- `wire_plugin_version` — the version when this release was last upgraded (may be absent on older releases)
- `created_date`
- `project_name` / `project_id` / `client_name` for the summary header

If `release_type` is absent or unrecognised, ask:
```
What is the release type for this release? (e.g. full_platform, dbt_development, platform_migration, droughty, discovery, agentic_data_stack, custom)
```

---

### Step 3: Detect Current Plugin Version

Check in order:

1. Plugin-installed mode: `~/.claude/plugins/wire/.claude-plugin/plugin.json` — read `version`
2. Dev mode: `wire/packaging/claude-plugin/.claude-plugin/plugin.json` — read `version`
3. Fallback: set `current_version` to `"unknown"` and note that version stamping will be skipped

Store as `current_version`.

---

### Step 4: Load the Canonical Template

Map `release_type` to its template file. Resolve relative to the plugin root (plugin mode: `~/.claude/plugins/wire/`, dev mode: the repo root):

| `release_type` | Template path |
|---|---|
| `full_platform`, `dbt_development` | `wire/TEMPLATES/status-template.md` |
| `platform_migration`, `data_warehouse_migration` | `wire/TEMPLATES/migration/status_migration.md` |
| `droughty` | `wire/TEMPLATES/droughty-status-template.md` |
| `agentic_data_stack` | `wire/TEMPLATES/agentic_data_stack/status_agentic_data_stack.md` |
| `discovery`, `shape_up_discovery` | `wire/TEMPLATES/discovery-status-template.md` |
| `sop_discovery` | `wire/TEMPLATES/sop-discovery-status-template.md` |
| `custom` | `wire/TEMPLATES/custom-status-template.md` |

If the template file cannot be found, surface a clear error:
```
Template not found for release_type: <type>
Expected: <path>

If this is a custom release type, run /wire:custom-define <release-folder> to update it.
```

Read and parse the template YAML frontmatter as `template_schema`.

---

### Step 5: Compute the Schema Diff

Compare `current_status` (the release's existing YAML) against `template_schema` (the canonical template).

**Rules:**

1. **Top-level keys**: for each key present in `template_schema` but absent from `current_status`, mark it as `MISSING — add with template default`.
2. **Nested keys within existing sections**: for each key present in `template_schema[section]` but absent from `current_status[section]`, mark it as `MISSING — add with template default`. Only descend one level — do not recurse deeper into already-present structures.
3. **Never touch**: keys present in `current_status` with non-null/non-`not_started` values. Do not flag as needing update.
4. **Template placeholders**: strip `{{...}}` placeholders from template defaults — replace with `null` or `not_started` as appropriate for the field type.
5. **Jira/Linear/docstore blocks**: if the current status already has `jira: null` or `linear: null`, treat the block as intentionally configured (not missing) — do not expand it. Only add the block if it is entirely absent.

If there are no differences, skip to Step 7 (summary).

---

### Step 6: Apply the Upgrade (unless `--dry-run`)

**If `--dry-run`**:

Print the proposed YAML patch:

```
## Dry-run: changes that would be applied to .wire/releases/<folder>/status.md

### New top-level sections
droughty: (entire section — 9 keys)

### New keys within existing sections
artifacts.droughty:
  generate: not_started
  validate: not_started
  review: not_started

### Frontmatter stamps
wire_plugin_version: 3.8.2
last_upgraded_at: 2026-06-11

No files were modified. Remove --dry-run to apply.
```

**Otherwise:**

1. Parse the full `status.md` content (frontmatter + body)
2. Merge missing sections and keys into the YAML frontmatter using a recursive merge that preserves existing values
3. Add or update two frontmatter fields:
   ```yaml
   wire_plugin_version: "<current_version>"
   last_upgraded_at: "<today>"
   ```
4. Write the updated content back to `status_path`, preserving the document body (non-frontmatter content) unchanged

If the write fails, surface the error and leave the original file unchanged.

---

### Step 6a: Backfill the tenant predicate registry (v3.11.3, carve-out releases only)

Applies only when `release_type` is a migration type and `migration.scope == tenant_carveout`. Skip silently otherwise.

If `migration/tenant_predicate_registry.csv` is absent and `migration/region_tags.csv` (or `region_tags_adjudicated.csv`, preferred when present) exists, create the registry by applying the seed table in `specs/utils/tenant_predicate_registry.md` to the existing buckets — the same seed `region-tagging-generate` Step 5b would have written. Set `provenance` to `backfilled by /wire:upgrade from region_tags` and leave `verified_date` empty: a backfilled row is a seed, not a verified mechanism. Write the backfilled rows with a CSV writer under the write contract in `specs/utils/tenant_predicate_registry.md` (comma-bearing expressions double-quoted, internal quotes doubled, #200).

Under `--dry-run`, report the row count that would be created and the resulting `unresolved` count, and write nothing. Never overwrite an existing registry file, and never invent a mechanism for an item the region tags do not cover — an item with no bucket seeds `unresolved`, which is the correct answer and the one that keeps it out of an unfiltered comparison.

Report in the summary: `Registry backfilled: N rows (M unresolved — resolve via /wire:dbt-carveout-relocate-generate or a ruling at region-tagging-review).`

---

### Step 6b: Add the cross-release linkage columns to the migration register (#180, migration releases only)

Applies only when `release_type` is a migration type and `migration/migration_register.csv` exists. Skip silently otherwise.

If the register header lacks any of `parent_release`, `parent_model`, `parent_verdict_ref`, insert the missing columns between `pr_url` and `notes` (matching `TEMPLATES/migration/migration_register.csv`) with every existing row's new cells blank. Blank is the correct backfill: linkage is written by `dbt-carveout-relocate-generate` at relocate time, and inventing it retroactively would fabricate evidence references. For a carve-out release whose relocated rows predate the columns (`origin: relocate` in `notes`, blank `parent_release`), report them so the consultant can backfill from the parent register deliberately: `N relocated row(s) have no parent linkage — re-run /wire:dbt-carveout-relocate-generate for their waves, or backfill parent_release/parent_model by hand from the parent register.`

Under `--dry-run`, report the columns that would be added and the unlinked relocated-row count, and write nothing.

---

### Step 6c: Re-resolve legacy dbt-relative `bq_target` values (#201, migration releases only)

Applies only when `release_type` is a migration type and `migration/migration_register.csv` exists. Skip silently otherwise.

Registers written before #201 carry `bq_target` as a dbt-relative two-segment value (e.g. `de_source_project.orders`); from #201 it is the fully qualified physical relation (`project.dataset.table`), the form `equivalency-validate` Step 1g and `equivalency-post-merge-verify` resolve against. For every `object_type` `model` or `snapshot` row whose `bq_target` is non-blank with exactly two dot-separated segments, re-resolve the physical path from the target-side dbt manifest: parse the project that builds the translated models via `specs/utils/dbt_manifest_parse.md` (the client repo's dbt project where models have merged; else the release's delivery tree under `migration/dbt/` where it parses), look up the row's model by name, and write `<database/project>.<schema>.<alias>` (the model name only when no alias is set, dbt's own fallback).

Never overwrite a three-segment value, and never compose a path from the model name when the manifest has no node for it: leave the legacy value in place and report the row; consumers classify it `unresolved_target` until it is resolved. Rows of `object_type` `metabase_card`/`metabase_dashboard` are exempt (their `bq_target` is a connection + database reference, not a warehouse relation).

Under `--dry-run`, report the counts (rows that would be re-resolved, rows with no manifest node) and write nothing.

Report in the summary: `bq_target backfilled: N rows re-resolved from the manifest (M unresolved: re-run /wire:dbt-migration-generate for those models, or resolve by hand).`

---

### Step 6d: Add the director-model blocks (4.0.0, every release type)

Applies to every release. These blocks are additive with safe defaults, so an
existing engagement behaves exactly as it did until a director gives a
directive.

**In `.wire/releases/<folder>/status.md`:**

| Block | Added as | Notes |
|---|---|---|
| `budget:` | Not added | An absent block means the defaults (4 lanes, no warehouse restriction, stop at decisions). Writing an explicit block would claim a decision nobody made. Report in the summary that the block is available and what the defaults are. |
| `parked_decisions:` | `parked_decisions: []` | Empty list. If `agents.paused_at` holds a value, convert it to one entry: `kind: review`, `artifact` from the `<artifact>-review` value, `question` "Approve now, request changes, or park for client sign-off?", `parked_at` from `agents.last_orchestrated` if set, else today. Leave `agents.paused_at` in place — nothing gains from deleting it, and an old reader still finds it. |
| `agents.coordinator_session` | Left as `null` unless already set | A claim is written by whatever is going to dispatch, not by an upgrade. |
| Profile field | Added only where the release type declares `profile_field` and the field is absent | Write `default_profile` as the value, and say so in the summary: the release has been running on that default already, and this makes it explicit rather than implicit. Never change a profile value that is already set. |

**In `.wire/engagement/context.md`:**

| Block | Added as | Notes |
|---|---|---|
| `orchestration:` | `orchestration:\n  mode: orchestrated` | The 4.0.0 default on Claude Code. A client-side team or a regulated engagement that wants today's behaviour sets `mode: manual`; say so in the summary so the off switch is discoverable at the moment it is introduced. |

Under `--dry-run`, list the blocks that would be added and write nothing.

Report in the summary:

```
Director model (4.0.0):
  status.md      parked_decisions: [] added [+ 1 entry converted from paused_at]
                 [profile_field]: [default_profile] written (was implicit)
  context.md     orchestration.mode: orchestrated added
  budget:        not set — defaults apply (4 lanes, no warehouse restriction,
                 stop at decisions). Set it in prose and Wire will write it.
  Off switch:    set orchestration.mode: manual in context.md for today's behaviour.
```

Nothing changes for this release until a director gives a directive. The blocks
are the record's shape, not a mode being switched on.

---

### Step 6e: Extend the execution log header with the metrics columns (4.0.0, every release type)

Applies to every release that has a `.wire/releases/<folder>/execution_log.md`. Skip silently when the file is absent (`/wire:status-sync` offers to create it) or when the header already carries all nine columns.

Extend the header row and its separator row in place to the full nine-column shape defined in `specs/utils/execution_log.md`:

```markdown
| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

- A four-column header (pre-`By`/`Session`) gains all five new columns; a six-column header gains `Duration`, `Tokens`, and `Cost (USD)`.
- **Never touch existing data rows.** Old rows keep their shorter shape and render with empty trailing cells; readers parse positionally and treat a missing cell as unknown (see the utility's Legacy rows section). Backfilling a metric would fabricate a measurement — an old row is unmeasured, not free or instant.
- This is the same header extension the next command write would perform anyway; the upgrade just does it eagerly so the log renders with the new columns immediately.

Under `--dry-run`, report the header change that would be made and write nothing.

Report in the summary: `execution_log.md: header extended to 9 columns (N existing rows left unchanged; metrics recorded from the next command run).`

---

### Step 7: Surface New Commands

Based on `release_type` and the detected additions, report any commands that are now available but were not present in the installed version when the release was created. Use the following known command introductions as the reference:

| Added in | Commands | Relevant release types |
|---|---|---|
| v3.11.3 | (schema, not commands) per-item tenant predicate registry `migration/tenant_predicate_registry.csv`, read by equivalency-validate, bulk-copy, carveout-relocate and defer-build; carve-out predicate resolution ladder in `dbt-carveout-relocate-generate`; sibling-naming cross-check in region tagging | `platform_migration` with `migration.scope: tenant_carveout` — see the registry backfill in Step 6a |
| v3.11.2 | (packaging and process, no new commands) shared specs ship in both packages; `dbt-migration-batch-raise --allow-stack-depth` with stacked batches refused by default | `platform_migration`, `data_warehouse_migration` |
| v3.11.1 | (carve-out adaptation, no new commands) relocate-mode equivalency via `migration.parent_target_project`; relocate register writes + gate chain; defer-build tenant guard; residency-gated `ship_then_verify`; `utils-ci-parity --scaffold-from`; region-tagging roles rule | `platform_migration` with `migration.scope: tenant_carveout` |
| v3.11.0 | `/wire:dbt-migration-defer-build`, `/wire:dbt-migration-batch-raise`, `/wire:equivalency-post-merge-verify`, `/wire:utils-ci-parity` | `platform_migration`, `data_warehouse_migration` — the ship-and-verify pipeline beyond "migrated": cost-guarded sandbox builds, register-driven PR batches, client CI parity, post-merge production verification |
| v3.11.0 | (schema, not commands) register columns `delivery_stage`/`pr_url`; append-only verdict log `migration/migration_verdict_log.csv`; verdict taxonomy replacing pass/fail; `migration.gate_policy`/`client_repos`/`cost_controls` status keys | `platform_migration`, `data_warehouse_migration` — the upgrade adds missing keys/columns with defaults; existing `pass`/`fail` verdicts stay valid, legacy `info` reads as `pass_qualified` |
| v3.10.3 | `/wire:migration-batching-generate\|validate\|review` | `platform_migration`, `data_warehouse_migration` — domain-batch scheduling, checked against the real dependency graph; distinct from `dbt_audit`'s translation batches |
| v3.10.2 | `/wire:migration-register-generate\|validate`, `/wire:migration-drift-generate\|validate` | `platform_migration`, `data_warehouse_migration` — per-model state store and scheduled drift gate for a migration running against a moving source |
| v3.10.1 | `/wire:region-tagging-*`, `/wire:data-residency-assessment-*`, `/wire:bulk-copy-migration-*`, `/wire:logical-access-uat-*` | `platform_migration` with `migration.scope: tenant_carveout` only |
| v3.10.1 | `/wire:metabase-audit-*`, `/wire:metabase-migration-*` | `platform_migration` with `migration.reporting_tool: metabase` |
| v3.9.9 | `/wire:migration-source-register`, `/wire:migration-source-refresh`, `/wire:migration-acceptance-pack-review` | `platform_migration`, `data_warehouse_migration` |
| v3.9.7 | `/wire:mcp check [release-folder]` | all — per-server connectivity table (CONNECTED / AUTH_REQUIRED / UNAVAILABLE / NOT_CONFIGURED); run at the start of every session |
| v3.9.0 | `/wire:delegate` | all — batch dispatch to specialist local subagents for pending artifact work |
| v3.8.0 | `/wire:droughty-*` (9 commands) | all — can be added to any release as an optional phase |
| v3.8.1 | `/wire:dbt-migration-lint` | `platform_migration`, `data_warehouse_migration`, `dbt_development` |
| v3.7.x | `/wire:utils-delivery-forecast` | all |
| v3.5.x | `/wire:utils-doc-analyze`, `/wire:custom-define` | all |

Only surface commands where the release's `wire_plugin_version` (before this upgrade) is older than the version in which the command was added. If `wire_plugin_version` was absent (first upgrade), surface all commands not already reflected in the status.md structure.

Format:
```
### New commands available for this release

These commands were added since this release was created and are now available:

  /wire:droughty-setup <release-folder>     — install Droughty and configure warehouse profile
  /wire:droughty-generate <release-folder>  — run the full Droughty discovery or post-dbt phase
  /wire:dbt-migration-lint <release-folder> — pre-warehouse equivalence lint (platform_migration only)

Run /wire:help droughty for full documentation on the Droughty commands.
```

---

### Step 8: Confirm and Summarise

```
## Upgrade Complete ✅

Release: <project_name> (<release-folder>)
Type:    <release_type>
Plugin:  <wire_plugin_version_before> → <current_version>

### Changes applied

<list each added section/key, or "No schema changes needed — status.md is already current">

### New commands available
<list, or "None — all commands for this release type were available when this release was created">

### No changes made to
- Artifact files (requirements.md, data_model.md, …)
- Existing status values
- Engagement context (.wire/engagement/context.md)

Run /wire:status <release-folder> to see the updated artifact lifecycle.
```

---

## Re-running Safely

`/wire:upgrade` is idempotent. Running it twice against the same release produces no changes on the second run — all sections already exist, and the `wire_plugin_version` and `last_upgraded_at` stamps are already present. Running it after a future plugin upgrade will add any new sections introduced in that version.

## Relationship to `/wire:migrate`

`/wire:migrate` handles structural layout changes (flat → two-tier directory structure). `/wire:upgrade` handles schema changes within an already-correct layout (missing YAML keys and sections as the framework evolves). If a release folder is on the pre-v3.4 flat layout, `/wire:upgrade` will detect this and redirect:

```
This release appears to be on the pre-v3.4 flat layout.
Run /wire:migrate first, then re-run /wire:upgrade.
```

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
