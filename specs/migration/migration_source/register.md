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
description: Register a source repository for a given migration source type
argument-hint: <release-folder> <source_type> <github_url>

---

# Migration Source — Register

## Purpose

Registers the git location of one source system in `status.md` under `migration_sources.<type>`. Multiple source types can be registered independently — each maps to a corresponding Wire audit command and is refreshed separately. Run once per source type, then run `/wire:migration-source-refresh $ARGUMENTS <source_type>` to pull a local snapshot.

**Related repos.** `related_repos:` in `.wire/engagement/context.md` (`/wire:utils-repos`, `specs/utils/repos.md`, wire#381) is the general form of this: any release can list the client's other repositories for read only lookups, per engagement rather than per release. This command is unchanged and the migration audits still read `migration_sources`. Whether the two are merged is a later decision.

## Source types

| `source_type` | Corresponding audit | Typical contents |
|---|---|---|
| `dbt` | `/wire:dbt-audit-generate` | dbt `.sql` models, schema YAML, `dbt_project.yml` |
| `ingestion` | `/wire:ingestion-audit-generate` | Fivetran / Airbyte / Coupler config files |
| `reverse_etl` | `/wire:reverse-etl-audit-generate` | Hightouch / Census git-backed sync definitions |
| `orchestration` | `/wire:orchestration-audit-generate` | Dagster assets, Airflow DAGs, dbt Cloud job YAML |
| `security` | `/wire:security-audit-generate` | IAM policies, Terraform role definitions |
| `lookml` | `/wire:looker-audit-generate` (`bi_migration`) | The client's LookML project: `.lkml` views, explores, models. The upstream of a Looker to Omni migration |
| `omni_model` | `/wire:omni-model-reverse-port` (`bi_migration`) | A git-connected Omni model repo: `.view`, `.topic`, `relationships.yaml`. The downstream of a Looker to Omni migration; Omni writes to it on `omni models commit` |

A single GitHub repo may contain multiple source types in different subfolders — register each with a separate command pointing to the appropriate subfolder URL. For example, a monorepo with Airflow DAGs at root and a dbt project at `dbt-snowflake/` would use:
```
/wire:migration-source-register <release> orchestration https://github.com/org/repo
/wire:migration-source-register <release> dbt            https://github.com/org/repo/tree/main/dbt-snowflake
```

## Arguments

- `<release-folder>` — the release folder name (e.g. `04-lift-and-shift-pilot`)
- `<source_type>` — one of `dbt`, `ingestion`, `reverse_etl`, `orchestration`, `security`
- `<github_url>` — GitHub URL pointing to the source home folder. Two forms accepted:
  - `https://github.com/{org}/{repo}` — repo root; branch defaults to `main`
  - `https://github.com/{org}/{repo}/tree/{branch}[/{subfolder}]` — specific branch and optional subfolder path

## Prerequisites

- Release folder exists with `project_type: platform_migration` or `project_type: bi_migration` in `status.md`

---

## Workflow

### Step 1: Parse and validate arguments

Extract the three arguments from `$ARGUMENTS`:

```
release_folder = first token
source_type    = second token
github_url     = third token
```

**Validate `source_type`**: must be one of `dbt`, `ingestion`, `reverse_etl`, `orchestration`, `security`, `lookml`, `omni_model`. If not, abort:
```
[wire] Unknown source type: "<value>". Must be one of: dbt, ingestion, reverse_etl, orchestration, security, lookml, omni_model.
```

**Parse `github_url`** to extract three fields:

1. Strip a trailing `.git` suffix if present.
2. Check whether the URL contains `/tree/` as a path segment.
   - **With `/tree/`**: split on `/tree/` — everything before is `git_repo_base`. The remainder is `{branch}[/{subfolder}]`. Take the first path segment as `branch`; everything after the first `/` (if any) is `subfolder`.
   - **Without `/tree/`**: `git_repo_base = github_url`, `branch = "main"` (default), `subfolder = ""`.

Examples:
```
Input:  https://github.com/acme/acme-airflow/tree/main/dbt-snowflake
→ git_repo:  https://github.com/acme/acme-airflow
→ branch:    main
→ subfolder: dbt-snowflake

Input:  https://github.com/rittmananalytics/ra_data_warehouse_production
→ git_repo:  https://github.com/rittmananalytics/ra_data_warehouse_production
→ branch:    main
→ subfolder: (empty)

Input:  https://github.com/acme/monorepo/tree/feature/new-platform/dbt/models
→ git_repo:  https://github.com/acme/monorepo
→ branch:    feature   (first segment — warn if branch contains slashes; ask user to confirm)
→ subfolder: new-platform/dbt/models
```

If the URL does not match the expected GitHub format (`https://github.com/{org}/{repo}...`), warn and ask the user to confirm the parsed values before proceeding.

### Step 2: Confirm release and check for existing registration

1. Read `.wire/releases/<release_folder>/status.md`. If it does not exist: `[wire] Release folder not found.`
2. Confirm `project_type` (or `release_type`) is `platform_migration` or `bi_migration`. `lookml` and `omni_model` are the `bi_migration` source types; the other five belong to `platform_migration`.
3. Read the `migration_sources.<source_type>` block if it already exists. If it does, show the current values and ask:
```
[wire] A "<source_type>" source is already registered:

  git_repo:             <value>
  branch:               <value>
  subfolder:            <value>
  local_snapshot_path:  <value>
  last_refreshed:       <value>

Re-register (overwrite) or cancel? [re-register / cancel]
```
If cancel, stop. If re-register, continue.

### Step 3: Set the local snapshot path

Default: `.wire/releases/<release_folder>/migration/source_snapshot/<source_type>/`

This default keeps each source type's snapshot isolated. If the user wants a custom path, they can edit `status.md` directly after registration.

### Step 4: Write the migration_sources block to status.md

Add or update the `migration_sources.<source_type>` entry in `status.md`:

```yaml
migration_sources:
  <source_type>:
    git_repo: "<git_repo_base>"
    branch: "<branch>"
    subfolder: "<subfolder>"
    local_snapshot_path: ".wire/releases/<release_folder>/migration/source_snapshot/<source_type>/"
    last_refreshed: null
    last_commit: null          # recorded by migration-source-refresh; the commit the snapshot was taken from
```

The `migration_sources` block is a map — each type is a separate key. Preserve any already-registered source types when writing.

### Step 5: Output summary

```
[wire] <source_type> source registered.

  git_repo:             <git_repo_base>
  branch:               <branch>
  subfolder:            <subfolder>    (or "(repo root)" if empty)
  local_snapshot_path:  <path>
  last_refreshed:       null

Pull a local snapshot:

  /wire:migration-source-refresh <release_folder> <source_type>

View all registered sources:

  /wire:migration-source-refresh <release_folder>  (refreshes all)
```

## Output Files

- Updated `.wire/releases/<release_folder>/status.md`

## Post-Execution Hooks

1. **Execution log** — Append one row to `.wire/releases/<release_folder>/execution_log.md` following `specs/utils/execution_log.md`. Detail: `<source_type> source registered — <git_repo_base>`.

No Jira sync, no document store sync, no auto-commit.
