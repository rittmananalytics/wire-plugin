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
/wire:upgrade --from-mod 01-discovery 02-data-foundation
                                         # queued by the Wire mod: these releases, in order
```

`--dry-run` prints the diff as a YAML patch and exits without writing.

`--from-mod` is how the Wire mod (Claude Code, 4.5.2 and later, wire#400)
queues this command at session start when a release's `wire_plugin_version`
is older than the plugin or absent: the arguments after the flag are the
release folders to upgrade, in that order. Step 1's question is skipped; every
other step runs as typed, including the confirmation before anything is
written, one release at a time. The mod queues it once per repository per
plugin version, only in an interactive session on the main loop, and leaves
out a release another person holds with a live claim; declining here is
recorded nowhere, and the mod does not ask again until the plugin changes.

## Prerequisites

- `.wire/` directory exists in the current repo
- The named release folder exists under `.wire/releases/`

---

## Workflow

### Step 1: Resolve the Release Folder

If a `<release-folder>` argument is provided:
1. Look for `.wire/releases/<release-folder>/status.md`
2. If not found, try `.wire/<release-folder>/status.md` (pre-v3.4 flat layout — redirect the user to `/wire:migrate` first)

If `--from-mod` is given, the arguments after it are release folders. Upgrade
each in the order given, running Steps 2 to 8 for one before starting the
next, and do not ask which release. A folder that does not exist is reported
and skipped. With `--from-mod` and no folders, say that nothing was named and
stop.

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

### Step 6f: Offer to remove the session-check hook (4.5.0, Claude Code)

The Wire mod's `prompt.compose` section now carries the session line once per
session (wire#270 D2), so the `UserPromptSubmit` hook `/wire:new` installed
before 4.5.0 (`.claude/hooks/wire-session-check.sh`, registered in
`.claude/settings.json`) prints the same line a second time. If
`.claude/settings.json` has a `UserPromptSubmit` entry whose command names
`wire-session-check.sh`, offer to remove that entry and the script; apply only
on yes. An engagement that keeps it sees the line twice and nothing worse.
Under `--dry-run`, report the removal that would be offered.

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
