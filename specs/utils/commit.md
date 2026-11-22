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
description: Stage and commit generated or validated Wire artifacts to git
argument-hint: <release-folder> <artifact> <action>

---

# Auto-Commit Utility

## Purpose

Stage the files produced or updated by a generate or validate command and create a git commit. Called at the end of every migration generate and validate spec, after docstore_sync. Does NOT push — push remains a deliberate user action.

## Usage

```bash
/wire:utils-commit 20260616_acme_migration dbt_audit generate
```

Typically invoked automatically by generate and validate specs. Inputs are passed by the calling spec:

| Input | Description | Example |
|-------|-------------|---------|
| `release_folder` | Release folder path under `.wire/releases/` | `20260616_acme_migration` |
| `artifact` | Artifact machine key | `dbt_audit` |
| `action` | Lifecycle step | `generate` or `validate` |

## Prerequisites

- Working directory must be inside a git repository
- Files must already have been written to disk by the calling spec

---

## Workflow

### Step 1: Check git availability

Run:
```bash
git rev-parse --is-inside-work-tree 2>/dev/null
```

If the command fails or returns empty, **exit silently** — the calling spec continues without error. Auto-commit is best-effort; not having git should never block a generate or validate run.

### Step 2: Stage the release folder changes

Stage all changes under the release folder and the root-level `status.md`:

```bash
git add .wire/releases/$RELEASE_FOLDER/
```

This captures:
- Newly created artifact files (generate)
- Updated `status.md` (generate and validate)
- Any CSV or supplementary files written alongside the primary artifact

If `git add` fails (e.g. permission error), log a brief note and exit:
```
Note: Auto-commit skipped — could not stage files under .wire/releases/$RELEASE_FOLDER/.
```

### Step 3: Check whether there is anything to commit

```bash
git diff --cached --quiet
```

If the exit code is `0` (nothing staged), exit silently — no commit needed. This avoids empty commits when a spec is re-run without changes.

### Step 4: Create the commit

Format the commit message as:

```
[artifact]: [action] [release_folder]
```

Examples:
- `dbt_audit: generate 20260616_acme_migration`
- `ingestion_audit: validate 20260616_acme_migration`
- `migration_strategy: generate 20260616_acme_migration`

Run:
```bash
git commit -m "[artifact]: [action] [release_folder]"
```

On success, output a single confirmation line:
```
✓ Committed: [artifact] [action] — [release_folder]
```

On failure (e.g. pre-commit hook blocks, no git identity configured), output:
```
Note: Auto-commit failed for [artifact] [action]. Files are staged — run `git commit` manually.
```

Do not retry. The calling spec continues regardless.

---

## Rules

- **Never push** — only commit. Push is always a user decision.
- **Never amend** — always create a new commit. Amending can corrupt prior work.
- **Never force** or bypass hooks (`--no-verify`). If a pre-commit hook fails, report it and leave files staged.
- **Idempotent** — running twice produces at most one additional commit (Step 3 guards against empty commits).

## Output

This utility:
- Stages all changes under `.wire/releases/<release_folder>/`
- Creates a single commit with a standard message if staged changes exist
- Outputs one confirmation line on success
- Fails gracefully and silently if git is unavailable
- Never blocks the calling spec
