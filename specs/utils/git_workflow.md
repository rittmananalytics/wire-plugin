---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
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
