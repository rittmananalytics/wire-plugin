---
description: Ensure a branch-per-artifact exists and, on validate/review, commit and open or update its PR (composes utils-commit and utils-pr-create)
argument-hint: <release-folder> <artifact-id> <action>
---

# Ensure a branch-per-artifact exists and, on validate/review, commit and open or update its PR (composes utils-commit and utils-pr-create)

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
description: Ensure a branch-per-artifact exists and, on validate/review, commit and open or update its PR
argument-hint: <release-folder> <artifact-id> <action>
---

# Git Workflow Utility

## Purpose

Give each artifact's current unit of work a dedicated branch, and keep that branch's commit and PR in sync as the artifact moves through generate → validate → review. Composes the existing `wire/specs/utils/commit.md` (staging + committing) and `wire/specs/utils/pr_create.md` (PR body drafting + creation) rather than duplicating their logic — this spec only adds the branch-per-artifact layer around them.

This closes the largest of the three manual-prompt clusters identified in [wire#113](https://github.com/rittmananalytics/wire/issues/113): 81 instances on a real client migration where branch creation, commit sequencing, and PR updates were done by hand in chat because no command existed for them.

## Usage

```bash
/wire:utils-git-workflow 20260616_acme_migration dbt_audit validate
```

| Input | Description | Example |
|-------|-------------|---------|
| `release_folder` | Release folder path under `.wire/releases/` | `20260616_acme_migration` |
| `artifact_id` | Artifact machine key | `dbt_audit` |
| `action` | Lifecycle step | `generate`, `validate`, or `review` |
| `base_branch` (optional) | Branch the artifact branch is created from and the PR targets. If omitted, resolve per Step 2. | `main` |

**Not automatically wired.** This spec is invoked deliberately by a caller — a generate/validate/review spec adds a step to its own tail: "Follow `wire/specs/utils/git_workflow.md` with `release_folder: [X]`, `artifact_id: [Y]`, `action: [generate|validate|review]`." It is not called automatically from any existing generate/validate/review spec by this change.

## Prerequisites

- Working directory must be inside a git repository
- For the commit/PR steps: same prerequisites as `commit.md` and `pr_create.md` (files already written to disk; `gh` CLI installed and authenticated for the PR step)

---

## Workflow

### Step 1: Check git availability

```bash
git rev-parse --is-inside-work-tree 2>/dev/null
```

If the command fails or returns empty, **exit silently** — the calling spec continues without error, exactly as `commit.md` Step 1 does. Branch management is best-effort; not having git should never block a generate, validate, or review run.

### Step 2: Resolve the base branch

Priority order:

1. If `base_branch` was passed as an explicit input, use it.
2. Else, if `status.md` frontmatter has a `client_repo_branch` (set by `wire/specs/new.md` Step 3 for dedicated-delivery-repo engagements), use it.
3. Else, detect the repo's default branch:
   ```bash
   git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
   ```
   If that returns empty (no remote, or HEAD ref not set), fall back to `main` if the branch exists locally, else `master`.

This mirrors the naming Step 8 of `wire/specs/new.md` already treats as the engagement's home branch (`main`/`master`, or `client_repo_branch` in dedicated-delivery mode) — this spec does not introduce a second, competing notion of "default branch."

### Step 3: Ensure the artifact branch exists

Compute the artifact branch name:

```
[release_folder]/[artifact_id]
```

Example: `20260616_acme_migration/dbt_audit`.

**Process**:
1. Check if the branch already exists locally:
   ```bash
   git rev-parse --verify --quiet [release_folder]/[artifact_id]
   ```
2. If it exists locally, check it out:
   ```bash
   git checkout [release_folder]/[artifact_id]
   ```
3. If it doesn't exist locally, check if it exists on the remote:
   ```bash
   git ls-remote --heads origin [release_folder]/[artifact_id]
   ```
   If found, check it out and track it:
   ```bash
   git checkout -b [release_folder]/[artifact_id] origin/[release_folder]/[artifact_id]
   ```
4. If it exists neither locally nor on the remote, create it from the resolved base branch:
   ```bash
   git checkout [base_branch]
   git pull --ff-only 2>/dev/null || true
   git checkout -b [release_folder]/[artifact_id]
   ```
   The `git pull` is best-effort — if it fails (no remote tracking, offline), proceed with the local base branch as-is rather than blocking.

If any `git checkout` in this step fails (e.g. uncommitted changes would be overwritten), stop and output:
```
Note: Could not switch to branch [release_folder]/[artifact_id] — [git's error message]. Resolve manually, then re-run.
```
Do not proceed to Step 4 in that case.

### Step 4: Act on `action`

**If `action` is `generate`**: Stop here. The branch now exists and is checked out; the calling spec continues with its own generation work. No commit or PR is created at generate time — there is nothing to commit yet, and the artifact isn't ready for review.

**If `action` is `validate` or `review`**: Continue to Step 5.

### Step 5: Commit the artifact's current state

Invoke `wire/specs/utils/commit.md` with the same parameters this spec received:

```
Follow wire/specs/utils/commit.md with release_folder: [release_folder], artifact: [artifact_id], action: [action]
```

Use `commit.md` exactly as documented — it stages `.wire/releases/[release_folder]/`, skips silently if there's nothing to commit, and never pushes or amends. Do not reimplement its staging or commit-message logic here.

### Step 6: Open or update the PR

Invoke `wire/specs/utils/pr_create.md` with the release folder:

```
Follow wire/specs/utils/pr_create.md with release-folder: [release_folder]
```

Use `pr_create.md` exactly as documented — it reads `execution_log.md` and `status.md` to draft the PR body, checks for an existing PR on the current branch via `gh pr view` and offers to update it rather than duplicate, and confirms with the user before creating. Do not reimplement its PR-body drafting or existing-PR-detection logic here.

**Known constraint inherited from `pr_create.md`**: as documented today, `pr_create.md` always compares against and opens PRs against `main` (`git log main..HEAD`, `gh pr create --base main`). If the resolved `base_branch` for this artifact branch is not `main` (e.g. a dedicated-delivery-repo engagement using `client_repo_branch`), the PR created by Step 6 will still target `main`, not the artifact's actual base branch. This spec composes `pr_create.md` unmodified per scope — extending it to accept a `--base` parameter is a reasonable follow-up but is out of scope here. Flag this to the user in the confirmation step if `base_branch != main`:
```
Note: this PR will target main (pr_create.md's fixed base), not [base_branch].
```

### Step 7: Output

On completion, output a single summary line:
```
✓ Branch [release_folder]/[artifact_id] — [action] — commit: [committed|nothing to commit], PR: [created <url> | updated <url> | skipped]
```

---

## Rules

- **Never push directly** — `commit.md` never pushes; `pr_create.md`'s `gh pr create` is the only thing that touches the remote, and only after explicit user confirmation.
- **One branch per artifact per release** — branch name is always `[release_folder]/[artifact_id]`, matching the composite key already used for `status.md`'s `artifacts.[artifact]` entries and Jira's per-artifact Task/Sub-task naming.
- **Idempotent branch creation** — re-running against an existing branch checks it out rather than recreating it.
- **Never reimplement commit or PR logic** — always delegate to `commit.md` and `pr_create.md`.
- **generate never touches history** — only `validate` and `review` reach the commit/PR steps.

## Edge Cases

### Branch exists but has diverged from base

Do not attempt to rebase or merge automatically. Check it out as-is and let `commit.md` / `pr_create.md` proceed; divergence resolution is a human decision.

### Uncommitted local changes on a different branch when this spec runs

`git checkout` will refuse to switch branches if it would overwrite local changes. Surface git's own error message per Step 3 and stop — do not stash or discard automatically.

### `gh` CLI not installed or not authenticated

`pr_create.md` already handles this (its own "gh CLI not installed" edge case). This spec's Step 6 surfaces whatever `pr_create.md` reports.

### Called with `action: review` before any `validate` has run

Proceed anyway — Step 5 (`commit.md`) is idempotent and a no-op if there's nothing new to stage; Step 6 (`pr_create.md`) will report "no commits on this branch that aren't already on main" per its own edge case if the branch truly has no new commits yet.

## Output

This utility:
- Ensures a `[release_folder]/[artifact_id]` branch exists, created from the resolved base branch if new
- Checks out that branch
- On `validate` or `review`, delegates to `commit.md` to commit the artifact's current state, then to `pr_create.md` to open or update the PR
- On `generate`, only ensures the branch — no commit or PR
- Fails gracefully and silently if git is unavailable, matching `commit.md`'s behaviour
- Is explicitly invocable only — no existing generate/validate/review spec calls it automatically as part of this change

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
