---
wire_schema: "1.0"
command: validate
artifact: agents_schema
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
  - agentic_data_stack
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--no-warehouse records every warehouse check as unverified instead of querying the AGENTS schema"
preconditions:
  - artifact: agents_schema
    action: generate
    outcome: complete
produces:
  - type: report
    path: "dev/agents_schema_validation_report.md"
    description: "PASS/FAIL report over the ten checks"
delegates_to:
  - utils/precondition_gate
  - utils/jira_sync
description: Validate the Agents Schema publication — the workflow pinned and free of credentials, every source still where the plan says, skills with valid uses declarations and no draft markers, and the warehouse AGENTS schema holding exactly what plan.json said (providers, row counts, skill rows, no stale models)
argument-hint: <release-folder> [--no-warehouse]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# agents_schema Validation Command

## Purpose

Check that what `agents_schema-generate` planned is what the repository carries and what the warehouse holds: the workflow will publish the right sources at a pinned version with no credential in it, the skills are well formed and finished, and after a publication the `AGENTS` schema has one row per planned provider, the row counts the manifest predicts, every planned skill, and no model the manifest no longer has.

## Usage

```bash
/wire:agents_schema-validate 01-dbt-foundation
/wire:agents_schema-validate 01-dbt-foundation --no-warehouse
```

## Prerequisites

- `agents_schema.generate == complete` in `status.md` (enforced by the precondition gate)
- For the warehouse checks: read access to the destination's `AGENTS` schema through the release's usual route (the BigQuery MCP server or `bq`, the Snowflake CLI connection, the Databricks SQL connector). If none is available, every warehouse check is `unverified`, and `unverified` is not a pass.

## Workflow

### Step 1: Read what was generated

From `status.md`: `version`, `destination`, `providers`, `skill_provider`, `skills`, `workflow`, `plan`, `published`, `needs_human`, `needs_human_resolved`, `guide_complete`. From disk: `dev/agents_schema/plan.json`, `dev/agents_schema/checks.sql`, the workflow file, `agents.yml`, every file under the plan's `skills_dir`, `dev/agents_schema_generation_report.md`, and the dbt manifest the plan names. Ground truth is the files and the warehouse, not the status entry.

### Step 2: Run the checks

**Check 1 — The plan and its files exist, and the workflow is pinned.** `plan.json` parses; every path in `plan.files` and `plan.skills[].path` exists; the workflow parses as YAML; every `uses:` line names `dbt-labs/agents_schema/.github/workflows/agents-schema-<source>.yml@<tag>` with `<tag>` equal to `plan.agents_schema_version` and to `status.md` `version`; the jobs are exactly `plan.providers[].job` for the providers this repository publishes, in order, each `needs:` the one before; a provider with `source_repo` (LookML in its own repository) has no job here, and its `workflow_file` exists, parses, is pinned to the same tag and names `publish_branch` and `source_dir`.
Severity: **Critical**. A floating or mismatched tag publishes whatever the upstream repository holds on the day.

**Check 2 — The sources are still where the plan says.** For the dbt provider, the manifest exists and its `resource_type: model` node set equals `plan.providers[dbt].model_ids`; a manifest older than the newest `.sql` or `.yml` under `models/` is reported. For each file provider, the files matching its glob under `source_dir` equal `plan.providers[].files`; for a provider with `source_repo`, the check runs in `local_clone` when the plan records one and is otherwise `unverified` with the repository named (the count comes from the warehouse in Check 6). Any `lookml_unparseable` item in the plan must have a decision in the generation report (the file reworded, or the publish accepted as blocked until it is).
Severity: **Major**. A source that moved after the plan publishes something else, or nothing.

**Check 3 — Skills are well formed and finished.** Every skill file under `skills_dir`: front-matter, when present, parses as YAML and `uses` holds only `schemas` and `tables` lists of strings, every `tables` entry schema-qualified (`schema.table`), and every entry resolves to a relation in the manifest (`schema.alias_or_name`) or a schema the manifest uses; no file holds a dbt `{% docs %}` block; no `<!-- wire: complete` marker remains; the skill set equals `plan.skills[].key`, so nothing was added to the directory without a plan entry; `needs_human_resolved` equals `needs_human` and every item has a decision in the generation report.
Severity: **Major**. A malformed `uses:` is skipped silently by the CLI, and a marker publishes an unfinished skill to every agent.

**Check 4 — No credential anywhere.** The workflow refers to `WAREHOUSE_CREDENTIALS` and `DBT_PROFILES_YML` only as `${{ secrets.<NAME> }}`; no file the plan wrote (workflow, `agents.yml`, skills, `run.sh`) contains a private key, a password, a token value or a service-account JSON.
Severity: **Critical**.

**Check 5 — The warehouse holds one `overview` row per planned provider.** Run the Check 5 query from `checks.sql`: `AGENTS.ROOT` where `key = 'overview'` returns `plan.providers[].root_provider` (`dbt`, `lookml`, `omni`, `osi`, `sigma`, `skills`). Skipped and recorded as `unverified` with the reason under `--no-warehouse`, `budget.warehouse_spend: none`, or `published: pending_ci` with no run yet.
Severity: **Critical**. Missing rows mean a job did not run or wrote elsewhere.

**Check 6 — Row counts match the plan.** Run the Check 6 query: `AGENTS.DBT_MODEL`, `AGENTS.DBT_COLUMN` and `AGENTS.DBT_DEPENDENCY` counts equal the plan's `expected_rows`; each semantic-layer table the plan lists has more than zero rows; `AGENTS.SKILL_USE` for the skill provider equals the planned uses.
Severity: **Critical** for the dbt tables (the plan and the CLI read the same manifest, so any difference is a stale or partial publication); **Major** for the others.

**Check 7 — Skill rows are present.** Run the Check 7 queries: `AGENTS.ROOT` holds `(skills, skill/agents-schema-analyst)` and one row per `plan.skills[].key` under `skill_provider`; `AGENTS.SKILL_USE` rows for the provider equal the planned `(skill_key, use_kind, object_ref)` set.
Severity: **Major**.

**Check 8 — No stale models.** Run the Check 8 query: the `unique_id` set in `AGENTS.DBT_MODEL` equals `plan.providers[dbt].model_ids`. A row the manifest lacks means the publication ran from an older manifest than the plan.
Severity: **Major**.

**Check 9 — Other publishers are listed.** Run the Check 9 query: every `provider` in `AGENTS.ROOT` not in the plan is listed in the report with its row count. This is information for the review; nothing is failed on it, and nothing is deleted.
Severity: **Info**.

**Check 10 — `agents.yml` carries the destination's settings.** BigQuery: `project_id` (and `location` when the dataset is regional); Snowflake: `snow_cli_connection`; Databricks: `host`, `http_path`, `catalog`, and no `token`. A `<placeholder>` value is a failure.
Severity: **Major**. The consumer skills stop at the first query without it.

### Step 3: Write the validation report

`.wire/releases/<release>/dev/agents_schema_validation_report.md`:

```
## Agents Schema Validation: [PROJECT_NAME]

**agents_schema:** <tag> · **Destination:** <type> · **Published:** ran | pending_ci | not_run · **Warehouse checks:** PASS | FAIL | unverified (<reason>)

### Results
| # | Check | Severity | Result | Detail |
|---|---|---|---|---|
| 1 | Plan, files and pinned workflow | Critical | PASS / FAIL | tag; jobs; the LookML repository workflow where one is planned |
| 2 | Sources match the plan | Major | ... | model set diff; file diff; manifest age |
| 3 | Skills well formed and finished | Major | ... | files; uses errors; markers; needs_human |
| 4 | No credentials | Critical | ... | |
| 5 | ROOT overview rows | Critical | PASS / FAIL / unverified | providers found vs planned |
| 6 | Row counts | Critical / Major | ... | table by table |
| 7 | Skill rows | Major | ... | keys missing; uses diff |
| 8 | No stale models | Major | ... | extra unique_ids |
| 9 | Other publishers | Info | listed | providers and counts |
| 10 | agents.yml settings | Major | ... | |

### Verdict
PASS | PASS WITH WARNINGS | FAIL
```

Verdict rule: any Critical failure is **FAIL**; `unverified` on a Critical check is **FAIL** unless the reason is a recorded budget setting or `published: pending_ci`, in which case the verdict is **PASS WITH WARNINGS** and the warehouse checks stay `unverified` in `status.md`; Major failures alone are **PASS WITH WARNINGS**; Info never changes the verdict. A publication that is pending CI can pass validate on the static checks alone, and review then carries the condition that the first workflow run is confirmed before sign-off.

### Step 4: Update Status

```yaml
agents_schema:
  validate: pass | fail
  validated_date: "{{TODAY}}"
  validation_report: "dev/agents_schema_validation_report.md"
  validation_verdict: "PASS | PASS WITH WARNINGS | FAIL"
  warehouse_verified: true | false | unverified
  other_providers: []          # Check 9
  checks_failed: []            # check numbers
```

`pass` covers PASS and PASS WITH WARNINGS; `fail` is FAIL.

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` with artifact `agents_schema`, action `validate`, and the verdict.

## Edge Cases

### The publication has not run yet (`published: pending_ci`)

Checks 5 to 9 are `unverified` with that reason, the verdict is PASS WITH WARNINGS at best, and the report says the warehouse checks re-run after the first workflow run: re-run this command then. Review is allowed on the static pass but records the condition.

### The AGENTS schema does not exist

The destination has never had a publication. Checks 5 to 9 fail (not `unverified`): the plan says a publication ran or should have. Check the workflow's Actions run or the `run.sh` output in the generation report.

### The row counts differ by exactly the disabled models

`disabled_models_in_manifest` was accepted in generate; the plan's counts include them, so they match. A difference means the manifest changed between plan and publication: re-run `agents_schema-generate` so the plan and the warehouse read the same file.

## Output

The report file, the `status.md` update, and the verdict on screen, followed by:

```
Ran: /wire:agents_schema-validate <release>
Next: /wire:agents_schema-review <release>              # on PASS
      /wire:agents_schema-generate <release>            # on FAIL, after fixing the cause (--force to rewrite the workflow)
```
