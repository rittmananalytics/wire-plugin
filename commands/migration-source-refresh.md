---
description: Pull a fresh local snapshot of a registered migration source
argument-hint: <release-folder> <source_type>
---

# Pull a fresh local snapshot of a registered migration source

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

## Workflow Specification

---
description: Refresh the local snapshot of one or all registered migration source repositories
argument-hint: <release-folder> [source_type]
---

# Migration Source — Refresh

## Purpose

Pulls an up-to-date local copy of one or all registered source repositories into their respective `local_snapshot_path` directories. All Wire audit and migration commands read from these snapshots rather than live repos — so a snapshot must exist before running any audit or migration command.

Re-run whenever the source repo has changed and you need Wire to pick up the latest files.

Note: Wire cannot run shell commands autonomously. This spec instructs the AI assistant to issue Bash tool calls to run git, rsync, and related commands in sequence.

## Arguments

- `<release-folder>` — required. The release folder name (e.g. `04-lift-and-shift-pilot`).
- `[source_type]` — optional. One of `dbt`, `ingestion`, `reverse_etl`, `orchestration`, `security`. If omitted, refresh **all** types present under `migration_sources` in `status.md`.

## Prerequisites

- At least one entry present under `migration_sources` in `.wire/releases/<release-folder>/status.md`
- Register sources first with `/wire:migration-source-register <release> <source_type> <github_url>`

---

## Workflow

### Step 1: Parse arguments and read status.md

Extract `release_folder` (first token) and `source_type` (second token, may be absent) from `$ARGUMENTS`.

Read `.wire/releases/<release_folder>/status.md`. If the file is missing: `[wire] Release folder not found.`

**If `source_type` is provided**: confirm it exists under `migration_sources` in status.md. If not:
```
[wire] No "<source_type>" source registered. Run /wire:migration-source-register <release> <source_type> <github_url> first.
```

**If `source_type` is omitted**: read all keys from `migration_sources`. If the block is absent or empty:
```
[wire] No sources registered yet. Run /wire:migration-source-register first.
```

Collect the list of source types to refresh (one type if specified; all registered types if not).

### Step 2: For each source type — refresh in sequence

Repeat Steps 2a–2d for each type in the refresh list.

#### Step 2a: Read the source entry

From `migration_sources.<source_type>`, extract:
- `git_repo`
- `branch`
- `subfolder` (may be empty string)
- `local_snapshot_path`
- `last_refreshed`

Show the current state:
```
[wire] Refreshing <source_type> source…

  git_repo:    <git_repo>
  branch:      <branch>
  subfolder:   <subfolder or "(repo root)">
  snapshot:    <local_snapshot_path>
  last_refreshed: <last_refreshed or "never">
```

#### Step 2b: Execute the refresh

Determine whether `git_repo` is a remote URL (starts with `https://`, `git@`, or `ssh://`) or a local path (starts with `/`, `~`, `./`, `../`).

---

**Remote URL, with subfolder** (`subfolder` is non-empty):

Clone to a temporary directory alongside `local_snapshot_path`, then extract just the subfolder:

```bash
TMP_DIR="<local_snapshot_path>_tmp"
rm -rf "$TMP_DIR"
git clone --depth=1 --branch <branch> <git_repo> "$TMP_DIR"
mkdir -p "<local_snapshot_path>"
rsync -av --delete --exclude='.git' "$TMP_DIR/<subfolder>/" "<local_snapshot_path>/"
rm -rf "$TMP_DIR"
```

If `--branch <branch>` fails, retry without it (picks the default branch) and warn:
```
[wire] Warning: branch "<branch>" not found. Cloned the default branch instead.
Update migration_sources.<source_type>.branch in status.md if this is wrong.
```

---

**Remote URL, no subfolder** (`subfolder` is empty or `""`):

If snapshot directory already exists, update in place:
```bash
git -C "<local_snapshot_path>" fetch origin
git -C "<local_snapshot_path>" checkout origin/<branch> -- .
```

If that fails, fall back to a full re-clone:
```bash
rm -rf "<local_snapshot_path>"
git clone --depth=1 --branch <branch> <git_repo> "<local_snapshot_path>"
```

---

**Local path, same as snapshot path**: no copy needed — proceed to Step 2c.

**Local path, different snapshot path**:
```bash
mkdir -p "<local_snapshot_path>"
rsync -av --exclude='.git' "<git_repo>/." "<local_snapshot_path>/"
```

---

#### Step 2c: Count and classify refreshed files

After the copy completes, count files by type appropriate to the source:

| `source_type` | Count targets |
|---|---|
| `dbt` | `*.sql` and `*.yml` / `*.yaml` |
| `ingestion` | `*.json`, `*.yaml`, `*.py` |
| `reverse_etl` | `*.yaml`, `*.json` |
| `orchestration` | `*.py`, `*.yaml` |
| `security` | `*.yaml`, `*.tf` |

Run Bash tool calls to count files:
```bash
find "<local_snapshot_path>" -name "*.sql" 2>/dev/null | wc -l | tr -d ' '
find "<local_snapshot_path>" -name "*.yml" -o -name "*.yaml" 2>/dev/null | wc -l | tr -d ' '
# etc.
```

For `dbt`, also group `.sql` files by immediate subdirectory (to show staging/intermediate/marts breakdown):
```bash
find "<local_snapshot_path>" -name "*.sql" 2>/dev/null | awk -F/ '{print $(NF-1)}' | sort | uniq -c | sort -rn
```

Print the file summary:
```
[wire] <source_type> snapshot refreshed.

  Files found:
    *.sql:   N   (dbt only)
    *.yml:   N
    *.py:    N   (if applicable)
    *.tf:    N   (security only)

  By subdirectory (dbt only):
    staging:       N
    intermediate:  N
    marts:         N
    (other dirs as found)
```

If no relevant files are found, warn:
```
[wire] Warning: no expected files found under "<local_snapshot_path>".
Check that the subfolder and branch are correct in status.md.
```

#### Step 2d: Update status.md

Set `migration_sources.<source_type>.last_refreshed` to today's ISO date (YYYY-MM-DD).
Leave all other fields unchanged.

### Step 3: Output summary

After all types have been refreshed, print a summary table:

```
[wire] Refresh complete.

  Source type     Snapshot path                                  Files    Last refreshed
  ─────────────   ────────────────────────────────────────────   ──────   ──────────────
  dbt             .wire/releases/.../source_snapshot/dbt/       N .sql   YYYY-MM-DD
  orchestration   .wire/releases/.../source_snapshot/orch/      N .py    YYYY-MM-DD

Next steps:
```

Then print the appropriate next-step hint for each refreshed source type:

| `source_type` | Next step |
|---|---|
| `dbt` | `/wire:dbt-audit-generate <release>` |
| `ingestion` | `/wire:ingestion-audit-generate <release>` |
| `reverse_etl` | `/wire:reverse-etl-audit-generate <release>` |
| `orchestration` | `/wire:orchestration-audit-generate <release>` |
| `security` | `/wire:security-audit-generate <release>` |

## Output Files

- Local snapshot(s) at `migration_sources.<type>.local_snapshot_path` (created or updated on disk)
- Updated `.wire/releases/<release>/status.md` (`migration_sources.<type>.last_refreshed` for each refreshed type)

## Post-Execution Hooks

After updating `status.md`:

1. **Execution log** — Append one row per refreshed type to `.wire/releases/<release>/execution_log.md` following `specs/utils/execution_log.md`. Result: `complete`. Detail: `<source_type> snapshot refreshed — N files at <local_snapshot_path>`.

No Jira sync, no document store sync, and no auto-commit.

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

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
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
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
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

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
