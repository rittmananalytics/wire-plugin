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

**Client template and review rules (wire#380)**: If `.wire/engagement/review_profile.yml` names a `pr_template` (schema in `wire/schemas/review-profile-schema.md`), or the repo has its own PR template, use the client's headings and put the sections above under them; never drop a client heading. Draft the body in the profile's `drafts_folder` (default `.wire/local/pr_drafts/`, which must be git-ignored). When rule findings or ticket requirements are known, add the two tables `wire/scripts/review_rules.py` writes: rule findings with dispositions (never blocking) and the requirements table, with any `not met` requirement raised as a question. When `/wire:utils-dev-test-evidence` has run on this branch, add its verdict table.

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
- [ ] Work done outside Wire commands reconciled via /wire:status-sync
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
