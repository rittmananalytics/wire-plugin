---
wire_schema: "1.0"
command: generate
artifact: droughty_setup
domain: droughty
release_types:
  - droughty
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Install Droughty at the pinned version and generate profile.yaml + droughty_project.yaml from Wire context
argument-hint: <release-folder>

---

# Droughty Setup Command

## Purpose

One-time setup for Droughty in a Wire engagement. Installs the pinned Droughty version, generates `profile.yaml` from Wire context (deriving credentials from MCP config where available), generates `droughty_project.yaml` with output paths aligned to Wire's artifact structure, verifies warehouse connectivity, and records setup state in `status.md`.

Run this before any other `/wire:droughty-*` command.

## Usage

```bash
/wire:droughty-setup <release-folder>
```

Pass `--force` to re-run setup even if already complete (e.g. after a version refresh or credential change).

## Prerequisites

- `.wire/engagement/context.md` exists
- BigQuery Application Default Credentials configured (`gcloud auth application-default login`) **or** Snowflake credentials available
- Python >= 3.9, < 3.12.4 on PATH
- For `droughty docs` and `droughty qa`: an OpenAI API key

## Workflow

### Step 1: Read Wire Context

1. Read `.wire/engagement/context.md` — extract `client_name`, `engagement_name`
2. Read `.wire/releases/<release>/status.md` — check `droughty.setup.status`
3. If `droughty.setup.status == complete` and `--force` was not passed:
   ```
   Droughty is already configured for this release.
   Run with --force to overwrite the existing setup.
   ```
   Stop here.

### Step 2: Locate Pinned Version

1. Check for `wire/droughty/pinned_version.txt` in the repo root (dev mode)
2. If not found, check `~/.claude/plugins/wire/droughty/pinned_version.txt` (plugin mode)
3. If neither found, default to the latest published version and warn:
   ```
   ⚠️  pinned_version.txt not found — installing latest Droughty. Pin a version by creating wire/droughty/pinned_version.txt.
   ```

Read `PINNED_VERSION` from the file.

### Step 3: Install Droughty

Check if the correct version is already installed:
```bash
pip show droughty 2>/dev/null | grep "^Version:" | awk '{print $2}'
```

If not installed or wrong version:
```bash
pip install "droughty==[PINNED_VERSION]"
```

If the install fails, surface the error verbatim and stop. Common causes:
- Python version outside 3.9–3.12.3 range
- No internet access or pip not available

### Step 4: Determine Warehouse Type

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Which warehouse should Droughty connect to?",
    "header": "Warehouse",
    "options": [
      {"label": "BigQuery", "description": "Google BigQuery — uses Application Default Credentials or a service account key"},
      {"label": "Snowflake", "description": "Snowflake — requires account ID, username, password, and warehouse name"}
    ],
    "multiSelect": false
  }]
}
```

Store `warehouse_type` as `bigquery` or `snowflake`.

### Step 5: Generate profile.yaml

Profile name: `[engagement_name]` (snake_case, from `context.md`).

Check whether `~/.droughty/profile.yaml` already exists with a profile of that name. If it does, ask:
```
A Droughty profile named '[engagement_name]' already exists. Overwrite it? (yes/no)
```

**For BigQuery:**

Check for existing ADC:
```bash
gcloud auth application-default print-access-token 2>/dev/null | head -c 10
```

If ADC is present, note it in the output. Ask directly in chat (one at a time):

1. "GCP project ID (e.g. `acme-analytics-prod`):"
2. "Default dataset name (e.g. `analytics`):"
3. "Which datasets/schemas should Droughty scan? List all that are in scope, comma-separated (e.g. `analytics,staging,raw`):"
4. "OpenAI API key? (required for `/wire:droughty-docs` and `/wire:droughty-qa` — press Enter to skip for now):"

Write `~/.droughty/profile.yaml` (append or create):

```yaml
[engagement_name]:
  type: bigquery
  project: [gcp_project_id]
  dataset: [dataset]
  schemas:
    - [schema1]
    - [schema2]
  openai_api_key: [openai_key]   # present only if provided
```

**For Snowflake:**

Ask directly in chat (one at a time):

1. "Snowflake account identifier (e.g. `xy12345.us-east-1`):"
2. "Username:"
3. "Password:"
4. "Virtual warehouse name (e.g. `COMPUTE_WH`):"
5. "Database name:"
6. "Default schema:"
7. "Role (e.g. `ANALYST` — press Enter to use default role):"
8. "Which schemas should Droughty scan? Comma-separated (e.g. `PUBLIC,STAGING`):"
9. "OpenAI API key? (required for `/wire:droughty-docs` and `/wire:droughty-qa` — press Enter to skip):"

Write `~/.droughty/profile.yaml`:

```yaml
[engagement_name]:
  type: snowflake
  account: [account_id]
  username: [username]
  password: [password]
  warehouse: [warehouse_name]
  database: [database]
  schema: [schema]
  role: [role]   # omit if not provided
  schemas:
    - [schema1]
    - [schema2]
  openai_api_key: [openai_key]   # present only if provided
```

### Step 6: Generate droughty_project.yaml

Ask in chat:

```
Where is your LookML project directory? (e.g. ./lookml — press Enter to skip if not using Looker)
```

```
Where is your dbt project directory? (default: ./ — press Enter for default)
```

Store `lookml_project_path` (or null) and `dbt_project_path`.

Create artifact directories:
```bash
mkdir -p .wire/releases/[release]/artifacts/droughty
mkdir -p .wire/releases/[release]/artifacts/droughty/field_descriptions
```

Write `droughty_project.yaml` at the git root:

```yaml
profile_name: [engagement_name]

# Output paths — Wire artifact structure
dbml_path: .wire/releases/[release]/artifacts/droughty/
field_description_path: .wire/releases/[release]/artifacts/droughty/field_descriptions/

# dbt output (if dbt project present)
dbt_path: [dbt_project_path]/models/
stage_path: [dbt_project_path]/models/staging/

# LookML output (if LookML project present)
# Droughty-generated base views land in views/generated/
# Wire-extended explores and refinements go in views/extended/
lookml_path: [lookml_project_path]/views/generated/
```

If `lookml_project_path` is null, omit the `lookml_path` line.

### Step 6.5: dbt Documentation and Test Settings with Droughty

A dbt project that uses droughty sets `required_docs: false` in the warehouse `+meta` block of `dbt_project.yml`, and keeps `required_tests` on:

```yaml
models:
  <project_name>:
    warehouse:
      +meta:
        required_docs: false
        required_tests: {"unique": 1, "not_null": 1}
```

Reasons: droughty writes no model descriptions, and it rewrites `models/droughty_schema.yml` on every run, so `required_docs` (from `dbt_meta_testing`) would fail on every warehouse model. The project meets the documentation rule through doc blocks in `models/field_descriptions.md`, which droughty writes into the column descriptions of `droughty_schema.yml`. `required_tests` is not affected.

- **New dbt project**: set the block above.
- **Existing dbt project**: if `dbt_project.yml` sets `required_docs: true`, report the change as a suggestion. Do not apply it.

droughty does not generate the `_sources.yml` files under `models/staging/`. Those are written by hand (see `/wire:droughty-stage`).

### Step 7: Verify Connectivity

Run a lightweight test to confirm warehouse access:

```bash
droughty dbml --profile-dir ~/.droughty --project-dir . 2>&1 | head -20
```

Interpret the result:
- If it produces output or a file, connectivity is confirmed. Extract table count from output if available.
- If it fails with an authentication error, surface the error and suggest credential fixes.
- If it connects but finds no tables, warn:
  ```
  ⚠️  Connected to [warehouse] but found no tables in: [schemas]

  If dbt models have not been deployed yet, run dbt first, then re-run this command.
  Check that the schemas listed in profile.yaml match what is in the warehouse.
  ```
  Do not treat this as a failure — setup is still complete.

### Step 8: Update status.md

Update in `.wire/releases/[release]/status.md`:

```yaml
droughty:
  setup:
    status: complete
    pinned_version: "[PINNED_VERSION]"
    warehouse: "[bigquery|snowflake]"
    profile_name: "[engagement_name]"
    schemas: [[list of schemas]]
    lookml_output_path: "[lookml_project_path]/views/generated/"   # or null
    dbt_project_path: "[dbt_project_path]"
    completed_date: "[today]"
```

### Step 9: Confirm and Guide Next Steps

```
## Droughty Setup Complete ✅

**Version**: [PINNED_VERSION]
**Warehouse**: [warehouse_type]
**Profile**: [engagement_name]
**Schemas in scope**: [comma-separated list]
**Artifact output**: .wire/releases/[release]/artifacts/droughty/

### Next Steps

Discovery commands (any warehouse, any time):

  /wire:droughty-introspect [release]   — Schema inventory report (tables, columns, PK/FK coverage)
  /wire:droughty-dbml [release]         — DBML entity-relationship diagram
  /wire:droughty-docs [release]         — AI-generated field descriptions
  /wire:droughty-qa [release]           — Data quality validation report

Post-dbt deploy commands (run after dbt models are deployed):

  /wire:droughty-dbt-tests [release]    — Pattern-based schema tests for deployed tables
  /wire:droughty-stage [release]        — Staging SQL + sources.yml (BigQuery)
  /wire:droughty-lookml [release]       — Base LookML views from dbt-created tables

Or run everything in sequence:
  /wire:droughty-generate [release]
```

## Refreshing the Pinned Version

Wire repo owners can update the pin to the latest published Droughty release with the bundled refresh script:

```bash
bash wire/droughty/refresh_version.sh
# or, to also commit the change automatically:
bash wire/droughty/refresh_version.sh --commit
```

The script queries PyPI, updates `wire/droughty/pinned_version.txt`, and prints the commit command. Once pushed, all subsequent `/wire:droughty-setup` runs install the new version.

Consultants on existing engagements should re-run `/wire:droughty-setup --force` after pulling the updated repo.

## Output

This command creates or updates:
- `~/.droughty/profile.yaml` (warehouse credentials — not committed to git)
- `droughty_project.yaml` at the git root
- `.wire/releases/[release]/artifacts/droughty/` artifact directory
- `droughty.setup` block in `.wire/releases/[release]/status.md`
