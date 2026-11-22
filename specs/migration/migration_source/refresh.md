---
wire_schema: "1.0"
command: utility
artifact: migration_source
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
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
- `[source_type]` — optional. One of `dbt`, `ingestion`, `reverse_etl`, `orchestration`, `security`, `lookml`, `omni_model`. If omitted, refresh **all** types present under `migration_sources` in `status.md`.

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
| `lookml` | `*.lkml`, `*.lookml` (grouped by `views/`, `models/`, `dashboards/`) |
| `omni_model` | `*.view`, `*.topic`, `relationships.yaml` |

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

Set `migration_sources.<source_type>.last_commit` to the commit the snapshot was taken from: `git -C "$TMP_DIR" rev-parse HEAD` captured before the temporary clone is removed, or `git -C "<local_snapshot_path>" rev-parse HEAD` for an in-place update, or `git -C "<local path>" rev-parse HEAD` for a local path that is a git checkout. Set it to `null` when the source is not a git repository. `looker-audit-generate` stamps this value on every catalog row as `lookml_commit`, `omni-model-generate` records it as each row's `last_migrated_commit`, and `migration-drift-generate` diffs against it, so a refresh that cannot determine the commit should say so rather than leave a stale value.
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
