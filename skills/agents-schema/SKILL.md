---
name: agents-schema
description: Publish and read warehouse metadata through dbt Labs' Agents Schema (the AGENTS schema inside Snowflake, Databricks or BigQuery, written by the agents-schema CLI from a dbt manifest, LookML, Omni, OSI, Sigma and markdown skills). Activates when the user mentions Agents Schema, agents_schema, AGENTS.ROOT, the agents-schema CLI or its GitHub workflows, warehouse-delivered skills, or asks how an AI agent should find governed context for a warehouse. Used by /wire:agents_schema-generate, -validate and -review, and for ad-hoc work against an AGENTS schema.
---

# Agents Schema

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | agents-schema | activated | Agents Schema work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## What Agents Schema is

[Agents Schema](https://github.com/dbt-labs/agents_schema) is a standard schema, named `AGENTS`, that lives inside the warehouse and holds the context an AI agent needs to query that warehouse: what the dbt models are and what their columns mean, what the semantic layer exposes, and instructions (skills) written for agents. It is closest in spirit to `INFORMATION_SCHEMA`, but extensible by provider and written for a reader that is an agent, so the content can be markdown, semi-structured, and free to change shape.

Every table sits in `AGENTS` (a dataset named `agents` on BigQuery, a schema named `AGENTS` on Snowflake, `agents` in the configured catalog on Databricks). `AGENTS.ROOT` is the entry point and the only table every consumer must know:

| Column | Meaning |
|---|---|
| `provider` | who published the row: `dbt`, `lookml`, `omni`, `osi`, `sigma`, `skills`, or a publisher's own name such as `acme` |
| `key` | unique within the provider; `overview` for the provider's own description, the unprefixed table name for a row documenting a table (`model` documents `AGENTS.DBT_MODEL`), `skill/<name>` for a skill |
| `content` | free text, usually markdown |

The delivered table families, one per source:

| Source | Tables | Read by the CLI from |
|---|---|---|
| dbt | `DBT_MODEL`, `DBT_COLUMN`, `DBT_DEPENDENCY` | `target/manifest.json` (every `resource_type: model` node) |
| Looker | `LOOKML_VIEW`, `LOOKML_DIMENSION`, `LOOKML_MEASURE`, `LOOKML_EXPLORE` | `**/*.lkml` |
| Omni | `OMNI_VIEW`, `OMNI_DIMENSION`, `OMNI_MEASURE`, `OMNI_TOPIC`, `OMNI_TOPIC_JOIN` | `**/*.view.yaml`, `**/*.topic.yaml` (an Omni Git-sync connection folder) |
| OSI | `OSI_MODEL`, `OSI_DATASET`, `OSI_FIELD`, `OSI_METRIC`, `OSI_RELATIONSHIP` | `*.osi.yaml`, validated against the OSI JSON schema first |
| Sigma | `SIGMA_DATA_MODEL`, `SIGMA_ELEMENT`, `SIGMA_COLUMN`, `SIGMA_METRIC` | `**/*.sigma.yaml` |
| Skills | `SKILL_USE` plus `skill/...` rows in `ROOT` | every `*.md` under the skills directory |

Each run of a source **replaces its own table family** (`CREATE OR REPLACE`) and upserts its own `ROOT` rows; other providers' rows are left alone. Every run also publishes one built-in skill, `(skills, skill/agents-schema-analyst)`, matched to the destination, which tells an agent how to answer a business question from the schema: discover the providers in `ROOT`, find the metric in the semantic tables, resolve the physical table, translate the formula, run it.

The full contract is `SPEC.md` in the repository; do not guess a column name, read it.

## How Wire uses it

The `agents_schema` artifact (optional on `full_platform`, `dbt_development`, `dashboard_first`, `agentic_data_stack` and `bi_migration`) publishes a release's metadata through this schema. The commands are in two halves:

- **Deterministic**: `scripts/agents_schema_plan.py` (shipped with the plugin; source at `wire/scripts/agents_schema_plan.py`) reads the manifest and the source folders and writes the GitHub workflow, `agents.yml`, the skills directory, `plan.json`, `run.sh` and `checks.sql`. Same inputs, same files. What it cannot decide is in `needs_human`.
- **Judgement**: completing the warehouse guide (business definitions, caveats), choosing which knowledge files to publish and under which provider name, and writing a `uses:` the script could not derive.

Wire pins one release tag of the upstream repository, `wire/agents_schema/pinned_version.txt` (`v0.0.11`). The workflow and `run.sh` both use it; never point a client's CI at `main`.

## Publishing

### From CI (the normal path)

The plan writes `.github/workflows/agents-schema.yml`, one job per provider calling the upstream reusable workflow, chained in the order dbt, looker, omni, osi, sigma, skills:

```yaml
jobs:
  agents-schema-dbt:
    uses: dbt-labs/agents_schema/.github/workflows/agents-schema-dbt.yml@v0.0.11
    with:
      dbt-project-dir: dbt
      dbt-profile-name: acme     # managed dbt parse, when target/manifest.json is not committed
      dbt-target: prod
    secrets:
      WAREHOUSE_CREDENTIALS: ${{ secrets.WAREHOUSE_CREDENTIALS }}
      DBT_PROFILES_YML: ${{ secrets.DBT_PROFILES_YML }}
```

Two secrets, both the client's to add in the repository settings, never written to a file:

- `WAREHOUSE_CREDENTIALS`: the destination credentials as YAML (or JSON). Snowflake: `type: snowflake`, `account`, `user`, `warehouse`, `database`, optional `role`, and `private_key_pem` (recommended) or `password`. Databricks: `type: databricks`, `host`, `http_path`, `catalog`, `token`. BigQuery: `type: bigquery`, `project_id`, optional `location`, `credentials_json` (the service-account object). The service account or role needs to create the `AGENTS` schema and create, load, query, update and delete tables in it.
- `DBT_PROFILES_YML`: the dbt `profiles.yml` text, only when the dbt job runs a managed parse because the repository does not commit `target/manifest.json`. The reusable workflow then runs `dbt deps` and `dbt parse --no-partial-parse` with the adapter inferred from the profile's `type`.

### From the dbt profile, without retyping anything

The two secrets usually already exist in `~/.dbt/profiles.yml` for the target the release builds with. `scripts/agents_schema_secrets.py` (shipped with the plugin) reads that one profile and target, builds `WAREHOUSE_CREDENTIALS` in the destination's shape and `DBT_PROFILES_YML` as that one profile and target only, and hands both to `gh secret set` on stdin; with `--publish` it also runs the release's `run.sh` with the credential in the child process's environment. It prints names, shapes and lengths, never a value:

```bash
uv run --with pyyaml python3 <plugin>/scripts/agents_schema_secrets.py --profile acme --target prod --check
uv run --with pyyaml python3 <plugin>/scripts/agents_schema_secrets.py --profile acme --target prod \
    --repo acme/warehouse --set-secrets --publish .wire/releases/<release>/dev/agents_schema/run.sh
```

`/wire:agents_schema-generate` offers this in its Step 5.5 (set and publish, set only, or leave to the repository owner) and `--set-secrets` answers without asking. Exit 3 means the profile's credential shape is not one the CLI accepts (BigQuery OAuth, Snowflake SSO, Databricks OAuth): the secrets are then the owner's to add by hand. On a client-owned repository, leaving them to the client is the usual answer unless the engagement says otherwise.

### LookML in its own repository

Looker's Git integration usually owns the LookML, in a repository of its own. The upstream Looker workflow checks out the repository that calls it, so that repository publishes itself: `--lookml-repo owner/repo[@ref]` (with `--lookml-repo-dir` for the folder inside it and `--lookml-repo-local` for a clone on this machine) makes the plan write `dev/agents_schema/lookml_repo/agents-schema-lookml.yml`, a one-job workflow pinned to the same tag that publishes `AGENTS.LOOKML_*` on every push to the ref, to commit there as `.github/workflows/agents-schema-lookml.yml` with the same `WAREHOUSE_CREDENTIALS` secret. The dbt repository's workflow then carries no looker job. Two repositories writing into one `AGENTS` schema is by design: each provider replaces only its own tables and `ROOT` rows. With a local clone, `run.sh` also publishes the LookML from this machine.

### From a laptop

```bash
export WAREHOUSE_CREDENTIALS="$(cat ~/.secrets/acme-agents-schema.yml)"   # never inside the repo
bash .wire/releases/<release>/dev/agents_schema/run.sh
# which runs, per provider:
uvx --from agents-schema==0.0.11 agents-schema dbt --project-dir dbt
uvx --from agents-schema==0.0.11 agents-schema looker --lookml-dir looker
uvx --from agents-schema==0.0.11 agents-schema skills --skills-dir agents_schema/skills --provider acme
```

`uvx` needs `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`). On an Apple-silicon Mac with an Intel Homebrew on the path, name an arm64 Python if `cryptography` tries to build from source (`uvx --python cpython-3.12-macos-aarch64-none ...`).

## Skills

A skill is a markdown file. The CLI publishes each `*.md` under `--skills-dir` as `(provider, skill/<path without .md>, content)`, and parses an optional front-matter:

```markdown
---
uses:
  schemas:
    - analytics
  tables:
    - analytics.wh_deals_fact
---

# Revenue skill

Use this skill when ...
```

Rules the CLI enforces, and `/wire:agents_schema-validate` Check 3 checks before it runs:

- `uses` holds only `schemas` and `tables`, each a list of non-empty strings; `tables` entries are schema-qualified. Anything else makes the CLI skip the `uses` (the skill is still published, with a warning on stderr and no `SKILL_USE` rows).
- The lists are additive permissions, not exclusions.
- The key is derived from the path. Wire's plan turns a colocated `models/marts/<domain>/DOMAIN_REFERENCE.md` (the `agentic_data_stack` knowledge skill) into `skill/<domain>` and derives `uses.tables` from the models in that folder; every other file keeps the CLI's own rule.
- A dbt `{% docs %}` block is not a skill. The plan skips any markdown file holding one, so a `--skills-source` pointing at `models/` does not publish documentation blocks.
- The warehouse guide the plan drafts carries two `<!-- wire: complete -->` markers, for business definitions and caveats. They are the consultant's to fill from `business_rules/register.md` and the requirements; validate fails while a marker remains.
- Nothing in a skill may hold a credential, or client-internal text the engagement brief marks confidential. Every agent with warehouse access reads it.

## Reading the schema (as a consumer)

Start from `ROOT`, always. On BigQuery the dataset and table names are lowercase; on Snowflake they are uppercase; Databricks is case-insensitive.

```sql
-- BigQuery
SELECT provider, key, content FROM `acme-data.agents.root` ORDER BY provider, key;
-- Snowflake
SELECT provider, key, content FROM AGENTS.ROOT ORDER BY provider, key;
```

Then follow the provider guidance in `content`. The lineage walk the spec gives (recursive over `DBT_DEPENDENCY` from a `source.` id) is the usual second query. dbt Labs also ships a Claude Code and Codex plugin marketplace from the same repository: `claude plugin marketplace add dbt-labs/agents_schema`, then `claude plugin install agents-schema@agents-schema`, which adds `/agents-schema:connect-warehouse` (configures and verifies `bq`, `snow` or the Databricks connector, reading `agents.yml`) and `/agents-schema:agents-schema-search` (discovers metadata through `ROOT`). The `agents.yml` the plan writes at the repository root is what those skills read: `project_id` and `location` on BigQuery, `snow_cli_connection` on Snowflake, `host`, `http_path` and `catalog` on Databricks. No token goes in it.

## Things to know before running it

- **Every `resource_type: model` node is published**, including a disabled model dbt still lists under `nodes`. The plan reports these as `disabled_models_in_manifest`; rebuild the manifest (`dbt clean`, `dbt compile`) or accept them in the review.
- **`ROOT` is shared.** Two publishers of the same provider (two dbt projects into one warehouse) overwrite each other's table family. Validate Check 9 lists every provider in `ROOT` the plan does not own; it is a decision for the release director, not a failure.
- **The `omni` source wants the connection-level folder** of an Omni Git sync (`omni/<connection name>/`), not the repository root; `--omni-dir` with a space in it is fine, the plan quotes it.
- **OSI files fail loudly.** An `*.osi.yaml` that does not match the OSI JSON schema fails the whole OSI run with the file and JSON path; nothing partial is written. Fix the file, not the run.
- **`snowflake-semantic`** (pointer rows for native Snowflake semantic views) is an experimental CLI source Wire does not plan; run it by hand if a client wants it, `agents-schema snowflake-semantic --semantic-view DB.SCHEMA.VIEW`.
- **The managed dbt parse in CI needs `--from dbt-core`.** The upstream action's default, `uvx --with <adapter> dbt parse`, resolves `dbt` to an unrelated PyPI package of that name, and dbt-core then mismatches the adapter (`ImportError: cannot import name ArtifactMixin`). The plan passes `dbt-parse-command` with `uvx --from dbt-core --with <adapter> dbt deps ... && dbt parse ... --no-partial-parse`, using the action's own `$profiles_dir`. If a hand-written workflow fails this way, that is the fix.
- **The LookML parser knows no SQL comments.** It matches braces while honouring quotes, so an apostrophe inside a `--` comment in a `sql:` block (`-- clients who haven't renewed`) opens a quote that never closes, and the whole looker publish fails with `unterminated LookML block` and no file name. The plan runs the same check first and names the files (`lookml_unparseable`); reword the comment.
- **Row counts are the contract.** `plan.json` records the model, column and dependency counts the manifest predicts; validate compares them to `AGENTS.DBT_MODEL`, `DBT_COLUMN` and `DBT_DEPENDENCY`. A difference means the publication ran from a different manifest than the plan.

## Relationship to the Wire commands

| Command | What it does with this skill |
|---|---|
| `/wire:agents_schema-generate <release> [--lookml-repo <owner/repo>] [--set-secrets] [--publish]` | Runs the plan over the release's sources, has the consultant complete the guide and the skill decisions, offers to set the repository secrets from the dbt profile, publishes from this machine with `--publish` or leaves it to the workflow |
| `/wire:agents_schema-validate <release>` | Ten checks: pinned workflow and files, sources unchanged, skills well formed and finished, no credentials, `ROOT` overview rows, row counts, skill rows, no stale models, other publishers listed, `agents.yml` settings |
| `/wire:agents_schema-review <release>` | Presents what an agent will now be told about the warehouse for sign-off |
| `/wire:ads_knowledge-skill-generate <release>` | Writes the `DOMAIN_REFERENCE.md` files the skills provider publishes on an `agentic_data_stack` release |
| `/wire:dbt-generate <release>` | The models and `schema.yml` descriptions the dbt provider publishes; a missing description is fixed there, not in `AGENTS` |
