<img src="wire/docs/images/wire_logo_transparent.png" alt="Wire Framework" width="220">

# Droughty in Wire — Guide for Existing Droughty Users

**Version**: 3.8.0 | Wire Framework by Rittman Analytics

---

## Contents

1. [What Droughty Is](#1-what-droughty-is)
2. [What Wire Is](#2-what-wire-is)
3. [Why They Work Together](#3-why-they-work-together)
4. [How Droughty-in-Wire Maps to Standalone Droughty](#4-how-droughty-in-wire-maps-to-standalone-droughty)
5. [Installation and Version Management](#5-installation-and-version-management)
6. [Configuration: profile.yaml and droughty_project.yaml](#6-configuration-profileyaml-and-droughty_projectyaml)
7. [Walkthrough: Droughty Release (Discovery / Audit Mode)](#7-walkthrough-droughty-release-discovery--audit-mode)
8. [Walkthrough: Post-dbt Mode](#8-walkthrough-post-dbt-mode)
9. [Using Droughty Within Other Wire Release Types](#9-using-droughty-within-other-wire-release-types)
10. [LookML Conventions](#10-lookml-conventions)
11. [Artefact Structure](#11-artefact-structure)
12. [Reference: Command Mapping](#12-reference-command-mapping)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What Droughty Is

Droughty is a schema-introspection toolkit for data warehouses. It reads the live warehouse and generates:

- **DBML** entity-relationship diagrams (`droughty dbml`)
- **AI field descriptions** for all columns (`droughty docs`)
- **LangGraph data quality reports** (`droughty qa`)
- **dbt schema tests** pattern-matched from deployed tables (`droughty dbt`)
- **Staging SQL and `sources.yml`** for BigQuery source datasets (`droughty stage`)
- **Base LookML views** from deployed dbt tables (`droughty lookml`)

It is bottom-up and schema-driven. Rather than starting from a spec and building down to the warehouse, Droughty starts from the warehouse itself and works upward toward documentation, tests, and a semantic layer.

---

## 2. What Wire Is

Wire is a delivery framework for data platform engagements. It encodes a full project lifecycle — discovery, design, development, testing, deployment, enablement — as a set of Claude Code slash commands (`/wire:*`). A consultant runs `/wire:new` to set up an engagement, then works through `/wire:*-generate`, `/wire:*-validate`, and `/wire:*-review` commands to produce and approve each deliverable.

You do not need to know much about Wire to use Droughty through it. The relevant point is that Wire gives each engagement a structured folder, a status file, and a command interface that handles the orchestration, credential management, and artefact routing you would otherwise do by hand.

---

## 3. Why They Work Together

Standalone Droughty is powerful but requires some setup overhead: writing `profile.yaml`, pointing `droughty_project.yaml` output paths at the right places, knowing which command to run first, and deciding where to put the results. Across multiple client engagements this gets repetitive.

Wire eliminates that overhead. `/wire:droughty-setup` derives credentials from the engagement context and MCP config, writes `profile.yaml` and `droughty_project.yaml` automatically, and routes all output to a structured artefact directory. The remaining `/wire:droughty-*` commands wrap the Droughty CLI with Wire's progress tracking, status file updates, and conditional logic (skip completed steps, prompt before overwriting, handle BigQuery-vs-Snowflake differences).

For Droughty users the result is: same CLI under the hood, less setup friction, and artefacts that slot directly into the broader engagement workflow rather than sitting in an ad-hoc folder.

---

## 4. How Droughty-in-Wire Maps to Standalone Droughty

This is the key table for existing Droughty users. Each `/wire:droughty-*` command corresponds to either a direct Droughty CLI call or a Wire-level step that uses warehouse queries instead.

| Wire command | Droughty CLI equivalent | Notes |
|---|---|---|
| `/wire:droughty-setup` | `pip install droughty==<version>`; write `profile.yaml`; write `droughty_project.yaml` | Wire-managed. Derives credentials from MCP config where available. Uses pinned version, not latest. |
| `/wire:droughty-introspect` | *(no CLI equivalent)* | Wire-only step. Queries `INFORMATION_SCHEMA` directly to produce a schema inventory report. There is no `droughty introspect` CLI command. |
| `/wire:droughty-dbml` | `droughty dbml --profile-dir ~/.droughty --project-dir .` | Direct CLI call. Output directed to Wire artefact directory via `droughty_project.yaml`. |
| `/wire:droughty-docs` | `droughty docs --profile-dir ~/.droughty --project-dir .` | Direct CLI call. Requires OpenAI API key in `profile.yaml`. Wire scopes large schemas before running. |
| `/wire:droughty-qa` | `droughty qa --profile-dir ~/.droughty --project-dir .` | Direct CLI call. Requires OpenAI key. Wire documents the non-determinism and prompts for review before using results with clients. |
| `/wire:droughty-stage` | `droughty stage -p <project> -d <dataset>` | Direct CLI call. BigQuery only. Wire handles merge/overwrite/diff against existing `sources.yml`. |
| `/wire:droughty-dbt-tests` | `droughty dbt --profile-dir ~/.droughty --project-dir .` | Direct CLI call. Wire confirms dbt is deployed before running and merges with existing `schema.yml` (Wire tests take priority). |
| `/wire:droughty-lookml` | `droughty lookml --profile-dir ~/.droughty --project-dir .` | Direct CLI call. Wire confirms dbt is deployed, creates `views/generated/` and `views/extended/`, warns before overwriting manually-authored files. |
| `/wire:droughty-generate` | Run all of the above in sequence | Wire orchestrator. Shows a plan, skips completed steps, and surfaces which mode (discovery or post-dbt) applies. |

### Key differences from standalone usage

**Profile management.** Standalone Droughty requires you to write `~/.droughty/profile.yaml` manually before any CLI command runs. `/wire:droughty-setup` does this for you, prompting only for information it cannot derive from the engagement context. The profile name matches the engagement name.

**Version pinning.** `pip install droughty` installs the latest. Wire installs a pinned version from `wire/droughty/pinned_version.txt` — currently `0.20.1`. This keeps all consultants on an engagement on the same version regardless of when they run setup. See [section 5](#5-installation-and-version-management) for how to update the pin.

**Output paths.** Standalone Droughty writes to wherever `droughty_project.yaml` says. Wire sets those paths to `.wire/releases/<release>/artifacts/droughty/` so artefacts are part of the engagement record and available to later Wire commands (problem definition, requirements, semantic layer).

**`droughty introspect` does not exist.** Wire adds a schema inventory step that queries `INFORMATION_SCHEMA` directly. If you are used to scripting this yourself with SQL, `/wire:droughty-introspect` replaces that.

**Conditional logic.** Wire skips commands that are not applicable (e.g. `droughty stage` on Snowflake), merges rather than overwrites where safe, and prompts before any destructive action. Standalone Droughty leaves these decisions to you.

---

## 5. Installation and Version Management

### How Wire installs Droughty

Running `/wire:droughty-setup <release>` installs Droughty at the pinned version:

```bash
pip install "droughty==0.20.1"
```

Python 3.9–3.12.3 is required. If the wrong Python version is on `PATH`, setup fails with a clear error.

If Droughty is already installed at the correct version, setup skips the pip step.

### Checking the pinned version

```bash
cat wire/droughty/pinned_version.txt   # in the Wire repo
```

Or from an installed plugin:

```bash
cat ~/.claude/plugins/wire/droughty/pinned_version.txt
```

### Updating the pin (Wire repo owner)

When a new Droughty version is published to PyPI, update the pin with:

```bash
bash wire/droughty/refresh_version.sh
# or commit the update automatically:
bash wire/droughty/refresh_version.sh --commit
```

The script queries the PyPI JSON API, updates `pinned_version.txt`, and prints a confirmation. Consultants pull the updated repo and re-run `/wire:droughty-setup --force` to install the new version.

### Forcing a re-install

```
/wire:droughty-setup <release> --force
```

Use this after a version refresh, after a credential change, or if setup completed with a warning and you want to re-run it cleanly.

---

## 6. Configuration: profile.yaml and droughty_project.yaml

These are the same two files standalone Droughty uses. Wire generates both; you do not need to write them by hand.

### `~/.droughty/profile.yaml`

Not committed to git. Wire writes or appends to this file during setup. One profile per engagement, keyed by engagement name.

**BigQuery profile (generated by Wire):**
```yaml
acme_analytics:
  type: bigquery
  project: acme-analytics-prod
  dataset: analytics
  schemas:
    - analytics
    - staging
    - raw
  openai_api_key: sk-...   # only if provided during setup
```

**Snowflake profile (generated by Wire):**
```yaml
acme_analytics:
  type: snowflake
  account: xy12345.us-east-1
  username: analyst
  password: secret
  warehouse: COMPUTE_WH
  database: ANALYTICS
  schema: PUBLIC
  role: ANALYST
  schemas:
    - PUBLIC
    - STAGING
  openai_api_key: sk-...
```

To edit credentials after setup, either edit `~/.droughty/profile.yaml` directly or re-run `/wire:droughty-setup --force`.

### `droughty_project.yaml`

Committed to git. Wire writes this at the git root with output paths pointing to the Wire artefact directory.

```yaml
profile_name: acme_analytics

dbml_path: .wire/releases/01-discovery/artifacts/droughty/
field_description_path: .wire/releases/01-discovery/artifacts/droughty/field_descriptions/
dbt_path: ./models/
stage_path: ./models/staging/
lookml_path: ./lookml/views/generated/
```

If you are running Droughty commands directly (not via Wire commands), these paths determine where output lands. Wire reads them back to locate artefacts when passing context to later commands.

---

## 7. Walkthrough: Droughty Release (Discovery / Audit Mode)

This is the primary use case if you are already using Droughty for warehouse audits. It maps directly to what you do standalone, with Wire handling the scaffolding.

### Create the engagement

```
/wire:new
```

Select **droughty** as the release type. Wire asks two follow-up questions: warehouse (BigQuery or Snowflake) and context (discovery/audit or post-dbt). Select **discovery/audit**.

This creates:
```
.wire/
  engagement/
    context.md
  releases/
    01-discovery/
      status.md
      artifacts/
        droughty/
          field_descriptions/
```

### Set up Droughty

```
/wire:droughty-setup 01-discovery
```

Wire prompts for credentials, writes `profile.yaml` and `droughty_project.yaml`, and verifies connectivity. This replaces the manual `pip install` + `profile.yaml` authoring you would do standalone.

### Get a schema inventory

```
/wire:droughty-introspect 01-discovery
```

This is a Wire-only step — it queries `INFORMATION_SCHEMA` and produces `schema_inventory.md` with table counts, column counts, approximate row counts, and PK/FK coverage signals. Use it to scope the rest of the phase and identify which schemas need attention before running the slower, more expensive commands.

Equivalent standalone approach: write and run your own `INFORMATION_SCHEMA` query.

### Generate the DBML diagram

```
/wire:droughty-dbml 01-discovery
```

Calls `droughty dbml --profile-dir ~/.droughty --project-dir .` and stores the `.dbml` file in the artefact directory. Identical to what you do standalone — Wire just routes the output.

Render the DBML in dbdiagram.io, DataGrip, or any DBML-compatible viewer.

### Generate field descriptions

```
/wire:droughty-docs 01-discovery
```

Calls `droughty docs --profile-dir ~/.droughty --project-dir .`. Requires `openai_api_key` in `profile.yaml`. Wire scans the schema inventory to check scale — if more than 200 tables are in scope it warns and asks for confirmation before proceeding. Budget ~$0.50–2 in OpenAI tokens per 100 tables depending on column count.

### Run the data quality agent

```
/wire:droughty-qa 01-discovery
```

Calls `droughty qa --profile-dir ~/.droughty --project-dir .`. As with standalone Droughty, this is non-deterministic — the LangGraph agent chooses which queries to run and may surface different issues on different runs. Wire documents this explicitly and asks you to review all QA output before presenting it to a client.

Large schemas (100+ tables) can take 20–30 minutes. Narrowing the `schemas:` list in `profile.yaml` is the most effective way to scope the run.

### Or run everything at once

```
/wire:droughty-generate 01-discovery
```

Wire shows the planned sequence, skips completed steps, and runs each command in order. If any step fails it stops and shows the error — partial progress is tracked in `status.md` so you can resume from where you left off.

### Feed artefacts into the engagement

Droughty artefacts in `.wire/releases/01-discovery/artifacts/droughty/` are available to subsequent Wire commands as evidence. The two most immediate are:

```
/wire:problem-definition-generate 01-discovery
```

This reads `schema_inventory.md`, the DBML diagram, and the QA report to draft a problem definition document — turning the Droughty audit output into a structured client deliverable. If you have been doing this synthesis manually after a Droughty run, this is the step that automates it.

```
/wire:requirements-generate 01-discovery
```

The requirements generator also reads the schema inventory to seed the data landscape section of the requirements document.

---

## 8. Walkthrough: Post-dbt Mode

Use this when dbt models are already deployed and the goal is to generate a base semantic layer from them. This is the mode you would use at the end of a `full_platform` or `dbt_development` engagement, or as an add-on phase to any standard Wire delivery.

### Confirm dbt is deployed

Before running any post-dbt Droughty command, confirm `dbt run` has completed successfully and the models are in the warehouse. Wire prompts for this confirmation before each command — it will not proceed if you indicate dbt is not deployed.

### Generate staging SQL and sources.yml (BigQuery)

```
/wire:droughty-stage 01-development
```

Calls `droughty stage -p <project> -d <dataset>` and writes staging SQL and `sources.yml` to `models/staging/`. If `sources.yml` already exists, Wire presents three options: merge new entries only, overwrite entirely, or show a diff. Wire-authored entries take priority in a merge.

This step has no Snowflake equivalent — `droughty stage` is BigQuery-only.

### Generate dbt schema tests

```
/wire:droughty-dbt-tests 01-development
```

Calls `droughty dbt --profile-dir ~/.droughty --project-dir .` and writes pattern-based schema tests to `schema.yml`. If `schema.yml` already exists, Wire merges new tests in. Tests already written by Wire (from `/wire:data_quality-generate`) are preserved.

### Generate base LookML views

```
/wire:droughty-lookml 01-development
```

Calls `droughty lookml --profile-dir ~/.droughty --project-dir .` and writes base views to `lookml/views/generated/`. Wire creates `lookml/views/extended/` alongside it for business-logic extensions.

**Critical convention:** never edit files in `views/generated/` by hand. Each re-run of `/wire:droughty-lookml` regenerates them. All customisation goes in `views/extended/` using LookML refinements — see [section 10](#10-lookml-conventions).

### Extend with the Wire semantic layer

```
/wire:semantic_layer-generate 01-development
```

This is where Wire takes over from Droughty. It reads the generated base views and produces explores, measures, and business-logic dimensions in `views/extended/`. The Droughty-generated views are the foundation; the Wire semantic layer is what gets built on top.

---

## 9. Using Droughty Within Other Wire Release Types

Droughty is not limited to the `droughty` release type. It can be added as a phase to any Wire engagement.

### Within a full_platform release

The `full_platform` release type takes a client from requirements through to production dashboards. Droughty fits in two places:

**Early — after requirements, before design:**

Use discovery mode to map the existing source data landscape before designing the data model. This grounds the conceptual model in what is actually in the warehouse rather than what the client says is there.

```
... /wire:requirements-review
/wire:droughty-setup 01-full-platform
/wire:droughty-introspect 01-full-platform
/wire:droughty-dbml 01-full-platform
→ feed schema_inventory.md into /wire:conceptual_model-generate ...
```

**Late — after dbt deployment, before semantic layer:**

Use post-dbt mode to generate the base LookML scaffold before Wire builds the semantic layer on top.

```
... /wire:dbt-validate
/wire:droughty-setup 01-full-platform   (if not already done)
/wire:droughty-dbt-tests 01-full-platform
/wire:droughty-lookml 01-full-platform
→ /wire:semantic_layer-generate 01-full-platform ...
```

### Within a dbt_development release

Same late-phase pattern as `full_platform`. After dbt models are deployed and validated, Droughty generates the test layer and base LookML, and Wire builds the semantic layer on top.

```
/wire:dbt-generate 01-dbt
/wire:dbt-validate 01-dbt
/wire:dbt-review 01-dbt
↓ dbt run (deploy to warehouse)
/wire:droughty-setup 01-dbt
/wire:droughty-dbt-tests 01-dbt
/wire:droughty-stage 01-dbt       ← BigQuery only
/wire:droughty-lookml 01-dbt
/wire:droughty-docs 01-dbt        ← optional: AI descriptions post-deploy
/wire:droughty-qa 01-dbt          ← optional: QA on deployed tables
/wire:semantic_layer-generate 01-dbt
```

### Within a platform_migration release

Droughty discovery mode is particularly useful during migration audits. The DBML diagram produced by `/wire:droughty-dbml` complements the Wire db-object audit by showing entity relationships, not just table inventory.

```
/wire:db-object-audit-generate 01-migration
/wire:droughty-setup 01-migration
/wire:droughty-introspect 01-migration
/wire:droughty-dbml 01-migration
→ DBML available as context for /wire:migration-strategy-generate
```

The `schema_inventory.md` from `/wire:droughty-introspect` feeds directly into `/wire:migration-inventory-generate` as additional evidence.

### Adding Droughty to an existing engagement

If you are mid-engagement and want to add a Droughty phase, run setup first to create the configuration:

```
/wire:droughty-setup <existing-release-folder>
```

Wire detects that a status.md already exists and adds the `droughty.*` status blocks without touching anything else.

---

## 10. LookML Conventions

This section is relevant if you use `droughty lookml` / `/wire:droughty-lookml`.

Wire enforces a two-directory convention inside your LookML project:

```
lookml/
├── views/
│   ├── generated/      ← Droughty output — auto-regenerated, never hand-edit
│   │   ├── orders.view.lkml
│   │   └── customers.view.lkml
│   └── extended/       ← Wire extensions — all business logic lives here
│       ├── orders_extended.view.lkml
│       └── explores.model.lkml
```

**`views/generated/`** is overwritten on every `/wire:droughty-lookml` run. Treat it as a build artefact, not source code. Do not commit hand-edits to these files — they will be lost.

**`views/extended/`** is where you put everything that is not Droughty output: explores, measures, derived dimensions, refined labels. Use LookML refinements (`view: +<name>`) to extend base views without touching the generated files:

```lookml
# views/extended/orders_extended.view.lkml

view: +orders {
  measure: total_order_value {
    type: sum
    sql: ${order_total} ;;
    value_format_name: usd
  }

  dimension: order_value_band {
    type: string
    sql: CASE
           WHEN ${order_total} < 100 THEN 'low'
           WHEN ${order_total} < 500 THEN 'medium'
           ELSE 'high'
         END ;;
  }
}
```

When the semantic layer phase runs (`/wire:semantic_layer-generate`), Wire reads the base views in `views/generated/` and writes explores and measures to `views/extended/`. Both directories should be committed to git.

---

## 11. Artefact Structure

All Droughty output lands inside the Wire engagement directory. A complete Droughty run produces:

```
.wire/
  releases/
    01-discovery/
      status.md                          ← tracks completion of each step
      artifacts/
        droughty/
          schema_inventory.md            ← /wire:droughty-introspect
          <schema>.dbml                  ← /wire:droughty-dbml
          qa_report.md                   ← /wire:droughty-qa
          field_descriptions/
            <schema>_<table>.md          ← /wire:droughty-docs (one file per table)

models/
  staging/
    stg_<table>.sql                      ← /wire:droughty-stage (BigQuery)
    sources.yml                          ← /wire:droughty-stage (BigQuery)
  schema.yml                             ← /wire:droughty-dbt-tests (merged)

lookml/
  views/
    generated/
      <table>.view.lkml                  ← /wire:droughty-lookml
    extended/                            ← Wire semantic layer phase
```

The `droughty_project.yaml` at the git root controls these paths. If you move the release folder, update `droughty_project.yaml` to match.

---

## 12. Reference: Command Mapping

Quick reference for Droughty CLI users.

| What you do standalone | Wire equivalent |
|---|---|
| `pip install "droughty==x.y.z"` | `/wire:droughty-setup <release>` |
| Write `~/.droughty/profile.yaml` | `/wire:droughty-setup <release>` |
| Write `droughty_project.yaml` | `/wire:droughty-setup <release>` |
| Custom `INFORMATION_SCHEMA` queries | `/wire:droughty-introspect <release>` |
| `droughty dbml --profile-dir ~/.droughty --project-dir .` | `/wire:droughty-dbml <release>` |
| `droughty docs --profile-dir ~/.droughty --project-dir .` | `/wire:droughty-docs <release>` |
| `droughty qa --profile-dir ~/.droughty --project-dir .` | `/wire:droughty-qa <release>` |
| `droughty stage -p <project> -d <dataset>` | `/wire:droughty-stage <release>` |
| `droughty dbt --profile-dir ~/.droughty --project-dir .` | `/wire:droughty-dbt-tests <release>` |
| `droughty lookml --profile-dir ~/.droughty --project-dir .` | `/wire:droughty-lookml <release>` |
| Run all of the above in sequence | `/wire:droughty-generate <release>` |

### Flags

| Standalone pattern | Wire equivalent |
|---|---|
| Re-run setup after credential change | `/wire:droughty-setup <release> --force` |
| Force a specific mode in generate | `/wire:droughty-generate <release> --mode discovery` |
| Force post-dbt mode | `/wire:droughty-generate <release> --mode post-dbt` |
| Run full sequence | `/wire:droughty-generate <release> --mode full` |

---

## 13. Troubleshooting

**`droughty: command not found` after setup**

Setup ran but Droughty is not on `PATH`. Check that the pip install target is on your `PATH`:

```bash
pip show droughty
which droughty
```

Python version must be 3.9–3.12.3. If you have multiple Python versions, check which `pip` is running:

```bash
python3 --version
pip3 --version
```

Re-run `/wire:droughty-setup --force` after resolving.

**`profile.yaml not found` or `profile not found: <name>`**

The profile name Wire uses is derived from the engagement name in `context.md`. If `~/.droughty/profile.yaml` was written to a different location or the engagement name contains unexpected characters, setup may have produced an unexpected profile key.

Check:
```bash
cat ~/.droughty/profile.yaml
cat .wire/engagement/context.md | grep engagement_name
```

The `profile_name` in `droughty_project.yaml` must match the key in `profile.yaml`.

**`No tables found in schemas`**

Droughty connected to the warehouse but found no tables. The most common cause is a mismatch between the schema names in `profile.yaml` and the actual schema names in the warehouse. BigQuery schema names are case-sensitive.

Check what schemas actually exist:
```sql
-- BigQuery
SELECT schema_name FROM [project].INFORMATION_SCHEMA.SCHEMATA;

-- Snowflake
SHOW SCHEMAS IN DATABASE [database];
```

Update `profile.yaml` to match, then re-run.

**`droughty qa` times out or takes too long**

The QA agent runs live warehouse queries chosen by LangGraph. Large schemas (100+ tables) are slow. Narrow scope by reducing the `schemas:` list in `profile.yaml` to the most relevant schemas for the current engagement phase. Re-run `/wire:droughty-setup --force` after updating `profile.yaml`.

**OpenAI API errors**

Required for `/wire:droughty-docs` and `/wire:droughty-qa`. Check:
- `openai_api_key` is set correctly in `~/.droughty/profile.yaml`
- The key has billing enabled and has not hit its rate limit
- The key is not a project-scoped key with model restrictions

**`views/generated/` hand-edits were lost**

Expected behaviour — Wire regenerates this directory on each `/wire:droughty-lookml` run. Move customisations to `views/extended/` using LookML refinements before re-running.

**Merge conflict in `sources.yml` or `schema.yml`**

Wire prompts before any merge. If you chose overwrite and lost Wire-authored entries, restore from git:

```bash
git diff HEAD -- models/sources.yml
git checkout HEAD -- models/sources.yml
```

Then re-run the command and choose merge.

---

*For the full Wire Framework user guide including all release types, see [USER_GUIDE.md](USER_GUIDE.md). For Wire installation and setup, see [README.md](README.md).*
