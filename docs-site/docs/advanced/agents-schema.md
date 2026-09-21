---
sidebar_position: 17
title: "Agents Schema"
---

# Agents Schema

**Since v4.0.0.** [Agents Schema](https://github.com/dbt-labs/agents_schema) is dbt Labs' standard for putting the context an AI agent needs to query a warehouse **inside that warehouse**, in a schema named `AGENTS`. One table, `AGENTS.ROOT`, lists which providers have published metadata and how to read their tables. The provider tables hold what the dbt manifest says about every model, column and dependency (`AGENTS.DBT_MODEL`, `AGENTS.DBT_COLUMN`, `AGENTS.DBT_DEPENDENCY`), what the semantic layer exposes (`AGENTS.LOOKML_*`, `AGENTS.OMNI_*`, `AGENTS.OSI_*`, `AGENTS.SIGMA_*`), and skills: markdown instructions for agents, stored as rows whose key starts with `skill/`. Anything that already runs SQL against the warehouse, Claude Code, Cursor, a notebook or an internal agent, reads that context with a `SELECT`, starting from `ROOT`, instead of guessing from `INFORMATION_SCHEMA` or a wiki.

Wire adds one optional artifact, `agents_schema`, to five release types. It publishes a release's metadata through this schema and keeps it current from the client's CI.

| Release type | Phase | Runs after | Providers it usually publishes |
|---|---|---|---|
| `full_platform` | development | `dbt` validate PASS; `semantic_layer` validate PASS (advisory) | dbt, looker, skills |
| `dbt_development` | development | `dbt` validate PASS; `semantic_layer` (advisory) | dbt, skills |
| `dashboard_first` | build | `dbt` validate PASS; `semantic_layer` (advisory) | dbt, looker, skills |
| `agentic_data_stack` | implementation | `canonical_models` validate PASS; `knowledge_skill` and `lookml_views` (advisory) | dbt, looker, skills (the `DOMAIN_REFERENCE.md` files) |
| `bi_migration` | model | `omni_model` validate PASS | omni |

The advisory gates say what they mean: a dbt-only publication before the semantic layer exists is a legitimate choice, so the gate warns, takes a reason and records an `advisory_skip` rather than blocking.

## What the command produces

`/wire:agents_schema-generate <release>` does not write the metadata tables itself. dbt Labs' `agents-schema` command-line tool does, run by reusable GitHub workflows from the same repository, pinned to one release tag (`wire/agents_schema/pinned_version.txt`, `v0.0.11` at the time of writing). What Wire adds is the part that needs the release: knowing which sources exist and where, writing the publication so it runs on every merge, assembling the skills from knowledge the release already produced, and checking afterwards that the warehouse holds what the plan said.

The command has two halves with a fixed line between them.

**The plan is a script.** `scripts/agents_schema_plan.py` reads the dbt manifest and the source folders and writes, without an AI call and without a warehouse connection:

| File | What it is |
|---|---|
| `.github/workflows/agents-schema.yml` | One job per detected provider, calling `dbt-labs/agents_schema`'s reusable workflow for that source at the pinned tag, chained in a fixed order (dbt, looker, omni, osi, sigma, skills). Secrets are referenced, never written. Written once; `--force` rewrites it |
| `agents.yml` | The connection settings the agents-schema consumer skills read to find the warehouse: project and location on BigQuery, the Snowflake CLI connection name, the Databricks host, path and catalog. Never a credential. Written once |
| `dev/agents_schema/lookml_repo/agents-schema-lookml.yml` | With `--lookml-repo owner/repo[@ref]`, when Looker's Git integration owns the LookML in a repository of its own: a one-job workflow for that repository, pinned to the same tag, to commit there. The upstream Looker workflow checks out the repository that calls it, so the LookML repository publishes itself, and the dbt repository's workflow carries no looker job. Each provider replaces only its own tables, so two repositories writing into one `AGENTS` schema is by design |
| `agents_schema/skills/*.md` | The skills the skills provider publishes. A colocated `models/marts/<domain>/DOMAIN_REFERENCE.md` becomes `skill/<domain>` with a `uses:` front-matter listing the tables of the models in its folder; a file with its own `uses:` is copied unchanged; a dbt `{% docs %}` block is skipped. Rewritten on every run |
| `agents_schema/skills/warehouse_guide.md` | A draft skill describing the warehouse layer: one section per subject area, one row per model with its table, keys and dates, and two `wire: complete` markers where the consultant writes the business definitions and the known caveats. Written once |
| `dev/agents_schema/plan.json`, `run.sh`, `checks.sql` | The plan (providers, paths, and the row counts validate compares against the warehouse), the same publication as a local script, and the validate queries in the destination's dialect |

The same inputs always produce the same files, and a test in `wire/tests/development/` holds that to be true byte for byte. Everything the script could not decide goes to `needs_human` with a reason: a manifest that is missing, a dbt job with no way to build one in CI, disabled models dbt still lists, models with no schema, a source folder with no matching files, a skill whose `uses:` could not be derived, a draft to complete.

**The skills are judgement.** The guide's business definitions come from the business rules register (one entry per agreed rule: the definition, the column and filter that implement it, the approver) or from the requirements where no register exists; the caveats come from the dbt work. Which knowledge files to publish, under which provider name, and whether to hand-write a `uses:` the script could not derive are decisions, and each one is a row in the generation report.

The two secrets the workflow needs usually already exist, in a different shape, in the consultant's dbt profile: a BigQuery service-account key, a Snowflake password or key pair, a Databricks token. So the command offers, once, to build them from that profile and set them on the repository with `gh secret set`: set both and publish now, set both only, or leave both to the repository owner (the usual answer on a client-owned repository). A second script, `scripts/agents_schema_secrets.py`, does the derivation in memory, trims `DBT_PROFILES_YML` to the one profile and target so other clients' credentials never leave the machine, and prints names and lengths only. `--set-secrets` answers without asking; a profile whose credential shape the upstream tool cannot use (OAuth, SSO) is reported and the secrets stay the owner's to add.

With `--publish`, or the first option of that offer, the command then runs the publication from the consultant's machine with the credentials in the environment and nowhere else. Otherwise the workflow publishes on the next push to the default branch once the secrets exist (and `DBT_PROFILES_YML`, when the dbt job has to build the manifest itself).

## Validation

`/wire:agents_schema-validate <release>` runs ten checks. Four are static: the plan and its files exist and every workflow job is pinned to the one tag; the sources are still where the plan says and the manifest's model set has not moved; every skill's `uses:` is well formed and resolves to a table the manifest knows, no `{% docs %}` block slipped in, no `wire: complete` marker remains; nothing written holds a credential. Five query the warehouse with the plan's own `checks.sql`: `ROOT` holds one `overview` row per planned provider; the dbt tables hold exactly the row counts the manifest predicts and the semantic tables are not empty; every planned skill row and its `SKILL_USE` declarations are present, as is the built-in analyst skill; `AGENTS.DBT_MODEL` holds no model the manifest no longer has; any provider in `ROOT` the plan does not own is listed for the review (information, never a failure). The tenth checks `agents.yml` carries the destination's settings with no placeholder.

A warehouse check that cannot run records `unverified`, which is not a pass. A publication still pending its first CI run passes on the static checks with warnings, and the review carries the condition that the first run is confirmed before sign-off.

Generate does not auto-validate, for the same reason `dbt-generate` does not: the validate step touches the warehouse, so it is a separate command and a separate decision.

## Reviewing

`/wire:agents_schema-review <release>` presents what an agent will now be told about the warehouse, in the order an agent reads it: the `ROOT` rows, the skills under the client's provider name, then one worked example of the built-in analyst procedure. The reviewer's decisions are the ones a script could not make: the definitions and caveats written into the guide, the knowledge files published and the ones dropped, the provider name, and any other publisher already writing into `AGENTS`. On approval the next steps are the client's: merge the PR, add the secrets, run the workflow once, then re-run validate against the warehouse.

## Notes on the upstream tool (v0.0.11)

Recorded in the `agents-schema` skill so nobody rediscovers them:

- Every `resource_type: model` node in the manifest is published, including a disabled model dbt still lists under `nodes`. Rebuild the manifest or accept them in the review.
- `ROOT` is shared across publishers. Each source run replaces only its own table family and its own `ROOT` rows, so two dbt projects publishing into one warehouse overwrite each other.
- A `uses:` front-matter that is malformed is skipped silently by the CLI (the skill is still published, with no `SKILL_USE` rows). Validate Check 3 catches it first.
- The Omni source wants the connection-level folder of an Omni Git sync, not the repository root. An OSI file that fails the OSI JSON schema fails the whole OSI run, with the file and path named.
- On BigQuery the dataset and tables are lowercase (`agents.root`); on Snowflake they are uppercase (`AGENTS.ROOT`). `checks.sql` is written in the destination's form.
- dbt Labs ships a Claude Code and Codex plugin marketplace from the same repository (`claude plugin marketplace add dbt-labs/agents_schema`). Its `connect-warehouse` and `agents-schema-search` skills read the `agents.yml` the plan writes.

## Where the rules live

| What | Where |
|---|---|
| The three commands | `wire/specs/development/agents_schema/{generate,validate,review}.md` |
| The plan script | `wire/scripts/agents_schema_plan.py`, shipped in the plugin under `scripts/` |
| The secrets script | `wire/scripts/agents_schema_secrets.py`, shipped in the plugin under `scripts/`; tested by `wire/tests/development/validate_agents_schema_secrets.py` |
| The pinned upstream tag | `wire/agents_schema/pinned_version.txt` |
| The skill | `wire/skills/agents-schema/SKILL.md` |
| The graph entries | `agents_schema` in `full_platform.yaml`, `dbt_development.yaml`, `dashboard_first.yaml`, `agentic_data_stack.yaml`, `bi_migration.yaml` (optional) |
| The agent that runs it | `wire/agents/agentic-data-stack-developer/AGENT.md` |
| The test | `wire/tests/development/validate_agents_schema_plan.py` (a fixture repository round-tripped byte for byte) |

## See also

- [Agentic Data Stack](../release-types/agentic-data-stack): the release type whose knowledge skills the skills provider publishes
- [dbt Charts Boards](./dbt-charts): the other optional development artifact that lives in the dbt project
- [Wire Agents](./wire-agents) (the `agentic-data-stack-developer` agent runs the generate and validate commands)
- [Command Reference](../reference/commands)
