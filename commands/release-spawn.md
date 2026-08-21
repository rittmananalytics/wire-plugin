---
description: Create downstream delivery release folders from an approved discovery release brief
argument-hint: <discovery-release-folder>
---

# Create downstream delivery release folders from an approved discovery release brief

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
description: Create downstream delivery release folders from an approved discovery release brief
---

# Release Spawn Command

## Purpose

Reads the approved release brief and sprint plan from a completed discovery release and creates the folder structure, status files, and initial artifact scope for each planned downstream delivery release. This is the bridge from discovery to delivery.

## Inputs

**Required**:
- `$ARGUMENTS` — the discovery release folder (e.g. `01-discovery`)
- A completed discovery release with a signed-off `planning/release_brief.md`

## Workflow

### Step 1: Locate the Discovery Release

**Process**:
1. Try `.wire/releases/$ARGUMENTS/` (two-tier layout)
2. Fall back to `.wire/$ARGUMENTS/` (legacy layout)
3. Read `planning/release_brief.md` and `planning/sprint_plan.md`
4. If the release brief hasn't been reviewed and signed off, output an error:
   ```
   The release brief for [folder] must be signed off before spawning delivery releases.
   Run /wire:release-brief-review [folder] first.
   ```

### Step 2: Extract Downstream Releases

From Section 4 (Downstream Releases) of the release brief, extract the planned delivery releases. Each should have:
- Release name
- Release type (`full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement`)
- Scope summary
- Priority order

Also check the sprint plan's "Downstream Releases" section for start dates.

If the downstream releases section is empty or unclear, ask directly in chat:
```
List the delivery releases to create (name: type, one per line):
e.g.
02-data-foundation: pipeline_only
03-reporting: dashboard_extension
```

### Step 3: Confirm with User

Output the list of releases to be created:
```
I'll create the following delivery releases:

[N]  .wire/releases/02-data-foundation/  (pipeline_only)
[N]  .wire/releases/03-reporting/        (dashboard_extension)

This will create status.md and the standard folder structure for each.
Proceed? (yes/no)
```

Use `AskUserQuestion` to confirm.

### Step 4: Create Each Delivery Release

For each planned delivery release, in priority order:

1. **Determine release number**: Next available sequential number (pad to 2 digits: 01, 02, 03...)
2. **Create folder**: `.wire/releases/[NN]-[release_name]/`
3. **Create subdirectories** appropriate for the release type:
   - All types: `artifacts/`, `planning/`
   - full_platform / pipeline_only / dbt_development: `requirements/`, `design/`, `dev/`, `test/`, `deploy/`, `enablement/`
   - dashboard_extension: `requirements/`, `design/`, `dev/`, `enablement/`
   - enablement: `enablement/`
4. **Create status.md** from the discovery status template:
   - Use `TEMPLATES/discovery-status-template.md` as a base — but populate with the delivery release type's artifact scope
   - Set release type, client name, engagement name from the parent engagement context
   - Set `spawned_from: [discovery_release_folder]` in the YAML frontmatter
   - Set `created_date` to today

**Bash command for folder creation:**
```bash
mkdir -p .wire/releases/[folder]/{artifacts,planning,requirements,design,dev,test,deploy,enablement}
```

### Step 5: Add .gitkeep Files

```bash
touch .wire/releases/[folder]/requirements/.gitkeep
touch .wire/releases/[folder]/design/.gitkeep
touch .wire/releases/[folder]/dev/.gitkeep
touch .wire/releases/[folder]/test/.gitkeep
touch .wire/releases/[folder]/deploy/.gitkeep
touch .wire/releases/[folder]/enablement/.gitkeep
```

### Step 6: Update Discovery Release Status

In the discovery release's `status.md`, add to the `notes` section:
```yaml
notes:
  - "Delivery releases spawned [date]: [list of release folders]"
```

### Step 7: Output Completion Summary

```
## Delivery Releases Created ✅

The following delivery releases have been spawned from [discovery_release_folder]:

| Release | Type | Folder | Status |
|---------|------|--------|--------|
| [name] | [type] | .wire/releases/[folder]/ | Ready |
| [name] | [type] | .wire/releases/[folder]/ | Ready |

### To start work on a delivery release:

1. Start a session:
   /wire:session-start releases/[folder]

2. Generate requirements:
   /wire:requirements-generate releases/[folder]

3. Check status:
   /wire:status releases/[folder]

Note: status tracking is updated automatically only when work runs through Wire
commands. Work done conversationally (agent-assisted or by hand) must reconcile
the record before raising a PR:
   /wire:status-sync releases/[folder]

The discovery release brief and sprint plan are stored at:
.wire/releases/[discovery_folder]/planning/

Reference them when generating requirements and design artifacts for the delivery releases.
```

## Edge Cases

### Release name conflicts
If a folder with the derived name already exists, append a letter suffix (e.g. `02-data-foundation-b`).

### Unknown release type
If a downstream release has an unrecognised type, create the basic folder structure (artifacts, planning) and note "type: custom — set up artifact scope manually" in the status.md.

### Legacy layout
If the discovery release is in legacy layout (`.wire/$ARGUMENTS/` not `.wire/releases/$ARGUMENTS/`), create new releases in the same layout for consistency. Note this in the status.md.

## Output Files

For each spawned release:
- `.wire/releases/[folder]/` directory structure
- `.wire/releases/[folder]/status.md`

Updated:
- `.wire/releases/[discovery_folder]/status.md`

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
