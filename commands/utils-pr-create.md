---
description: Create a Wire-aware GitHub pull request pre-populated from session artifacts
argument-hint: [release-folder]
---

# Create a Wire-aware GitHub pull request pre-populated from session artifacts

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
description: Create a Wire-aware GitHub pull request pre-populated from session artifacts
argument-hint: <release-folder>
---

# PR Create Utility

## Purpose

Create a pull request for the current branch, pre-populated from Wire session artifacts. Reads `execution_log.md` and `status.md` to fill in commands run, artifact statuses, and handover notes — so the PR body reflects what actually happened in the session rather than being left blank.

## Usage

```bash
/wire:utils-pr-create [release-folder]
```

If `release-folder` is omitted, infer it from the most recently modified `.wire/releases/*/status.md` file.

## Prerequisites

- `gh` CLI must be installed and authenticated
- Current branch must have commits not yet on `main`
- `.wire/releases/[release-folder]/status.md` must exist

## Workflow

### Step 1: Establish Release Context

1. Resolve the release folder (from argument or inference above)
2. Read `.wire/releases/[release-folder]/status.md` — extract:
   - `engagement_name`, `client_name`
   - Artifact statuses (all entries under `artifacts:`)
   - Any `jira.ticket_url` or `linear.issue_url` frontmatter
3. Read `.wire/releases/[release-folder]/execution_log.md` — extract the most recent session's rows (entries since the last commit on `main` or the branch creation, whichever is later)

### Step 2: Inspect Git State

```bash
git log main..HEAD --oneline
git diff main..HEAD --name-only
```

From the diff output, identify which artifact files changed. Map changed file paths back to artifact names using the release folder layout:
- `requirements/` → `requirements`
- `design/` → `data_model` / `conceptual_model` / `pipeline_design`
- `dev/` → `dbt` / `semantic_layer` / `dashboards`
- `deploy/` → `deployment`
- `enablement/` → `training` / `documentation`
- `planning/` → `release_brief` / `sprint_plan` / `problem_definition`

### Step 3: Check for Existing PR

```bash
gh pr view --json url,state 2>/dev/null
```

If a PR already exists for this branch, offer to update its body instead of creating a new one. Ask:
```
A PR already exists for this branch: [url]
Update its body with current session data? (yes/no)
```

### Step 4: Build PR Body

Read `TEMPLATES/pr_template.md` and populate each section:

**Summary**: If the execution log has a session summary entry, use it. Otherwise, construct one sentence from the artifact names that changed and their new statuses.

**Release**: Fill in the release folder path.

**Artifacts Changed**: One row per changed artifact file. Derive the Change column from the execution log (e.g. "generated", "validated", "reviewed and approved").

**Status After Merge**: One row per artifact that has a status in `status.md`. Use the current status value.

**Issue Tracker**: If `jira.ticket_url` or `linear.issue_url` is present in `status.md` frontmatter, list those links. Otherwise leave the placeholder.

**Handover — Commands run**: List Wire commands from the execution log for this session, formatted as `/wire:command-name`.

**Handover — Next commands**: Suggest the logical next Wire commands based on the current artifact statuses. For each artifact in `in_progress` or `draft` status, suggest the next lifecycle step (`validate` after `generate`, `review` after `validate`). If all artifacts are `approved`, suggest `deployment-generate` or `session-plan` for the next release.

**Handover — Notes**: Leave blank — this requires human input. Add a comment: `<!-- Fill in decisions made, open questions, or non-obvious context -->`

**Checklist**: Leave all items unchecked — the reviewer should tick them on inspection.

### Step 5: Confirm and Create

Show the populated PR body to the user in full, then ask:
```
Ready to create PR with the above body?
Title: [derived title]
Base: main
(yes / edit title / cancel)
```

Derive the title from: `[client_name] [release_folder] — [comma-separated list of changed artifacts]`, truncated to 72 characters.

On confirmation:

```bash
gh pr create --title "[title]" --base main --body "$(cat <<'EOF'
[populated body]
EOF
)"
```

On "edit title": prompt for a new title, then create.

On "cancel": exit without creating.

### Step 6: Output

After successful creation, output:
```
PR created: [url]

Handover checklist:
- [ ] status.md reflects current artifact state
- [ ] execution_log.md has entries for all commands run this session
- [ ] No sensitive data committed

Share the PR link with your reviewer when ready.
```

## Edge Cases

### No commits ahead of main

```
No commits on this branch that aren't already on main.
Commit your changes first, then run /wire:utils-pr-create again.
```

### execution_log.md missing or empty

Populate the commands-run section with `<!-- Could not read execution_log.md — fill in manually -->` and continue.

### gh CLI not installed

```
gh CLI is not installed or not authenticated.
Install it from https://cli.github.com, run `gh auth login`, then retry.
```

### Multiple releases modified in one branch

If the diff touches files across more than one release folder, ask the user to specify which release the PR primarily relates to, then use that release's `status.md` for the Artifacts Changed and Status sections. Note the other release in the Summary.

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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
