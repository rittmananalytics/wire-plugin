---
wire_schema: "1.0"
command: generate
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
      description: "--providers dbt,looker,omni,osi,sigma,skills limits the plan to the named sources (default: every source the release has); --skills-source <path> adds a markdown file or folder to publish as skills (repeatable); --provider <name> sets the publisher of the skill rows (default: the engagement slug); --lookml-repo <owner/repo[@ref]> names a separate LookML repository (with --lookml-repo-dir <path> for the folder inside it and --lookml-repo-local <clone> for a local clone), so the plan writes a workflow for that repository instead of a job here; --no-guide skips the warehouse guide draft; --set-secrets derives WAREHOUSE_CREDENTIALS and DBT_PROFILES_YML from the release's dbt profile and sets them on the repository with gh, without asking; --publish runs the publication from this machine after the plan is written (WAREHOUSE_CREDENTIALS from the environment, or derived from the dbt profile when --set-secrets is given or the offer in Step 5.5 is accepted); --no-warehouse writes the plan only and never touches the warehouse; --force rewrites the workflow, agents.yml and the guide draft where they exist; --force-workflow rewrites only the workflow, for a provider added or removed after the guide was completed"
preconditions: dynamic
auto_validate: false
produces:
  - type: document
    path: "<repo_root>/.github/workflows/agents-schema.yml"
    description: "The GitHub Actions workflow that publishes the repository's metadata into the warehouse AGENTS schema on every push to the default branch, one job per provider, pinned to one agents_schema release tag; written only if absent"
  - type: document
    path: "<repo_root>/agents.yml"
    description: "Connection settings (never credentials) the agents-schema consumer skills read to find the warehouse; written only if absent"
  - type: document
    path: "<repo_root>/agents_schema/skills/<skill>.md"
    description: "The skills the skills provider publishes as AGENTS.ROOT rows: the release's knowledge files with a derived uses: declaration, plus the warehouse guide"
  - type: document
    path: "dev/agents_schema/lookml_repo/agents-schema-lookml.yml"
    description: "When the LookML lives in a separate repository: the workflow to commit there as .github/workflows/agents-schema-lookml.yml, publishing that repository's LookML into the same AGENTS schema"
  - type: report
    path: "dev/agents_schema/plan.json"
    description: "What will be published: providers, source paths, the row counts validate compares against the warehouse, the skills and their uses, every needs_human item"
  - type: report
    path: "dev/agents_schema_generation_report.md"
    description: "What the plan proposed, what the consultant kept, changed or dropped, the guide's completed sections, and whether the publication ran"
delegates_to:
  - utils/precondition_gate
  - utils/agentic_data_stack_delegate
  - utils/stale_artifact_check
  - utils/jira_sync
  - utils/docstore_sync
description: Publish the release's metadata into the warehouse AGENTS schema (dbt Labs' Agents Schema) — a deterministic plan detects the providers the release has (dbt manifest, LookML, Omni, OSI, Sigma, knowledge skills), writes the pinned GitHub workflow, agents.yml and the skills directory, the consultant completes the warehouse guide, and the publication runs from CI or, with --publish, from this machine
argument-hint: <release-folder> [--providers <list>] [--skills-source <path>]... [--lookml-repo <owner/repo[@ref]> [--lookml-repo-dir <path>] [--lookml-repo-local <clone>]] [--provider <name>] [--no-guide] [--set-secrets] [--publish] [--no-warehouse] [--force | --force-workflow]
workload: judgment
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# agents_schema Generate Command

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below. The `agentic-data-stack-developer` agent runs this command on every release type that carries the artifact, not only `agentic_data_stack`: publishing warehouse metadata for agents is its remit whichever release built the warehouse.

## Purpose

Put the context an AI agent needs to query this warehouse **inside the warehouse**, in the standard `AGENTS` schema defined by [Agents Schema](https://github.com/dbt-labs/agents_schema): one row per dbt model, column and dependency (`AGENTS.DBT_MODEL`, `AGENTS.DBT_COLUMN`, `AGENTS.DBT_DEPENDENCY`), the semantic layer's views, fields, measures and explores or topics (`AGENTS.LOOKML_*`, `AGENTS.OMNI_*`, `AGENTS.OSI_*`, `AGENTS.SIGMA_*`), and warehouse-delivered skills (rows in `AGENTS.ROOT` whose key starts with `skill/`). Anything that already queries the warehouse, Claude Code, Cursor, a notebook, an internal agent, then reads that metadata as ordinary SQL, starting from `AGENTS.ROOT`, instead of guessing from `INFORMATION_SCHEMA` or a wiki.

Wire does not write the metadata tables itself. dbt Labs' `agents-schema` CLI does, driven by reusable GitHub workflows pinned to one release tag (`wire/agents_schema/pinned_version.txt`, `v0.0.11` as this spec is written). What Wire adds is the part that needs the release: knowing which sources exist and where, writing the publication so it runs on every merge, assembling the skills from the knowledge the release already produced, and checking afterwards that what the warehouse holds is what the plan said.

The command is in two halves, and the line between them is fixed:

1. **The plan is deterministic.** `scripts/agents_schema_plan.py` reads the dbt manifest and the source directories, decides which providers apply, and writes the workflow, `agents.yml`, the skills directory (every source knowledge file copied with a `uses:` front-matter derived from the manifest, plus a draft `warehouse_guide.md` built from the warehouse layer), `plan.json` with the counts validate will compare against the warehouse, `run.sh` for a local publication and `checks.sql` in the destination's dialect. The same inputs always give the same files. Everything it cannot decide goes to `needs_human` with a reason. Do not hand-write what it emits.
2. **The skills are judgement.** The guide draft carries two `<!-- wire: complete -->` markers, business definitions and known caveats, that only a person who has read the business rules register and the requirements can fill. Which knowledge files to publish, under which provider name, and whether a `uses:` the script could not derive should be written by hand, are decisions, and each is recorded in the generation report.

`auto_validate: false`: the validate step queries the warehouse's `AGENTS` schema, so it is a separate command and a separate decision, as `dbt-validate` is.

## Usage

```bash
/wire:agents_schema-generate 01-dbt-foundation                          # plan and write the files; publication runs from CI
/wire:agents_schema-generate 01-dbt-foundation --publish                # also run the publication from this machine
/wire:agents_schema-generate 01-dbt-foundation --set-secrets --publish  # set both repository secrets from the dbt profile, then publish
/wire:agents_schema-generate 01-dbt-foundation --lookml-repo acme/looker@production --lookml-repo-local ~/GitHub/acme-looker
/wire:agents_schema-generate 01-dbt-foundation --providers dbt,skills   # dbt and skills only, even if LookML exists
/wire:agents_schema-generate 01-dbt-foundation --skills-source docs/analyst_notes --provider acme
/wire:agents_schema-generate 01-dbt-foundation --no-warehouse           # under warehouse_spend: none
/wire:agents_schema-generate 01-dbt-foundation --force                  # rewrite the workflow, agents.yml and the guide draft
```

## Prerequisites

Enforced by the precondition gate (`preconditions: dynamic`, resolved from `wire/release-types/<project_type>.yaml`), release-type dependent:

- **`full_platform`, `dbt_development`, `dashboard_first`**: `dbt` at `validate: PASS`; `semantic_layer` at `validate: PASS` is advisory (without it the plan has no LookML provider, which is a legitimate choice and is recorded as an `advisory_skip`).
- **`dashboard_extension`**: `dashboards` at `validate: PASS`. The release builds no dbt project or semantic layer, so the plan reads the ones already in the repository.
- **`agentic_data_stack`**: `canonical_models` at `validate: PASS`; `knowledge_skill` and `lookml_views` at `validate: PASS` are advisory.
- **`bi_migration`**: `omni_model` at `validate: PASS`.

Also needed:

- `uv` on the machine, for `uvx` (the plan's `run.sh` and the reusable workflows both run the CLI through it). Step 2 checks and stops with the install line if it is missing.
- For `--publish`: the destination credentials YAML in the `WAREHOUSE_CREDENTIALS` environment variable, in the shape the [setup guide](https://github.com/dbt-labs/agents_schema/blob/main/dbt-setup.md) gives per destination, or a dbt profile Step 5.5 can derive it from. It is never written to a file in the repository.
- For `--set-secrets`, or to accept the offer in Step 5.5: `gh` authenticated with rights to set Actions secrets on the repository (`gh secret list` succeeds).

## Inputs

| Input | Where it comes from | Required |
|---|---|---|
| The dbt project | `status.md` `dbt_project_path` (or `migration.dbt_project_path`), else `dbt/`, `dbt_project/` or the repository root, whichever holds `dbt_project.yml` | when the dbt provider applies |
| `target/manifest.json` | `dbt compile` in that project (Step 3) | dbt provider |
| The LookML project | `--lookml-repo` or `agents_schema.lookml_repo` in `.wire/engagement/context.md` when the Looker project is its own repository (the usual case: Looker's Git integration owns it); else `semantic_layer.generated_files` in `status.md`, else `lookml/` or `looker/` at the repository root holding `*.lkml` | looker provider |
| The Omni connection directory | `omni_model` batches on a `bi_migration` release (`migration_sources.omni_model.path`), else a folder holding `*.view.yaml` and `*.topic.yaml` | omni provider |
| `*.osi.yaml`, `*.sigma.yaml` directories | named by `--providers` and `.wire/engagement/context.md` `agents_schema.osi_dir` / `sigma_dir`; never guessed | osi, sigma providers |
| Knowledge skills | `models/marts/<domain>/DOMAIN_REFERENCE.md` from `ads_knowledge-skill-generate` (`agentic_data_stack`); any `--skills-source` | skills provider |
| `business_rules/register.md` | `business-rules-generate` | when present: the guide's business definitions |
| The destination | `status.md` `warehouse` / `target_platform` (`bigquery`, `snowflake`, `databricks`), with the BigQuery project and location, the Snowflake CLI connection name or the Databricks host, path and catalog from `.wire/engagement/context.md` | always |
| `budget.warehouse_spend` | `status.md` | always |

## Workflow

### Step 1: Resolve the sources and the destination

1. Read `status.md` and `.wire/engagement/context.md`. Resolve the dbt project as in Inputs. Resolve each other source directory the same way; a source named by `--providers` whose directory cannot be found stops the command and names the paths checked.
1a. **LookML in its own repository.** Looker's Git integration usually owns the LookML, so a `lookml/` folder in the dbt repository is often a copy or a subset and not what Looker serves. When `--lookml-repo` or the engagement context names a repository, plan the looker provider from that repository: the upstream Looker workflow checks out the repository that calls it, so that repository publishes itself through a workflow the plan writes for it (Step 4), and the dbt repository's workflow carries no looker job. Give `--lookml-repo-local` when a clone is on this machine, so the plan can count the files and `run.sh` can publish LookML from here; without one the file count is unknown until that workflow runs. A `lookml/` folder in the dbt repository is ignored when `--lookml-repo` is given, and the report says so. Both providers replacing only their own tables is what makes two repositories writing into one `AGENTS` schema safe.
2. Resolve the destination type. Agents Schema writes to Snowflake, Databricks and BigQuery only; any other warehouse stops the command:

   ```
   Agents Schema publishes to Snowflake, Databricks and BigQuery.
   This release's warehouse is <type>. Nothing was written.
   ```

3. Resolve the skill publisher: `--provider`, else `agents_schema.provider` in the engagement context, else the engagement slug lower-cased with `[a-z0-9_]` only. Record it; the provider is the key under which every skill row lives, and changing it later leaves the old rows in place.
4. Say what will happen before it happens, in one sentence and a table: each provider with its source path, the destination, the skill sources, and whether the publication will run (`--publish`) or be left to CI.

### Step 2: Check the tooling

Run `uvx --version`. If it fails, stop:

```
uv not found. Install it, then re-run:
  curl -LsSf https://astral.sh/uv/install.sh | sh
```

Read the pinned tag from `wire/agents_schema/pinned_version.txt` (shipped default in the script). Do not pin `main`; the workflow runs in the client's CI on every merge and an unpinned reference changes under them.

### Step 3: Produce the dbt manifest

In the dbt project, `dbt deps` then `dbt compile` for `target/manifest.json`, with the release's profile and target as `dbt-validate` uses them. A manifest older than the newest model file is regenerated, never reused. The CLI publishes every `resource_type: model` node in the file, so a manifest built with a selector or from a stale `target/` publishes the wrong model set. Skip this step when the dbt provider is not in the plan.

The workflow in CI needs the same manifest. Two ways, and the plan records which: the repository commits `target/manifest.json` (rare in Wire projects), or the workflow runs a managed `dbt parse` with the `DBT_PROFILES_YML` secret and the profile and target the plan passes as `dbt-profile-name` and `dbt-target`. The plan also passes `dbt-parse-command`, pinned `uvx --from dbt-core --with <adapter> dbt deps ... && ... dbt parse ... --no-partial-parse`: the action's own default runs `uvx --with <adapter> dbt parse`, in which `dbt` resolves to an unrelated PyPI package of that name and dbt-core then mismatches the adapter (`ImportError: cannot import name ArtifactMixin`, seen on v0.0.11's first CI run). Without a profile the plan records `no_dbt_profile` and the review's next steps say what the client has to add. A project that parses only under dbt Fusion still parses under dbt-core for this purpose in every case seen so far; check the first CI run's model count against the plan (validate Check 6 does).

### Step 4: Run the plan

```bash
python3 <plugin>/scripts/agents_schema_plan.py \
  --repo-root <repo root> \
  --out .wire/releases/<release>/dev/agents_schema \
  --destination <bigquery | snowflake | databricks> \
  [--project-id <gcp project> --location <location>] [--snow-connection <name>] \
  [--databricks-host <host> --databricks-http-path <path> --databricks-catalog <catalog>] \
  [--dbt-project-dir <path> --dbt-profile <profile> --dbt-target <target>] \
  [--lookml-dir <path> | --lookml-repo <owner/repo[@ref]> [--lookml-repo-dir <path>] [--lookml-repo-local <clone>]] \
  [--omni-dir <path>] [--osi-dir <path>] [--sigma-dir <path>] \
  [--skills-source <path>]... --provider <publisher> \
  [--no-guide] [--force]
```

Pass only the sources Step 1 resolved (and `--providers` kept). The script writes, relative to the repository root:

| File | Written | Rewritten on a re-run |
|---|---|---|
| `.github/workflows/agents-schema.yml` | one job per planned provider, chained in the order dbt, looker, omni, osi, sigma, skills, every `uses:` pinned to the tag | with `--force`, or `--force-workflow` (a provider added or removed; the guide is left alone) |
| `agents.yml` | the destination's connection settings for the consumer skills (project and location; the Snowflake connection name; the Databricks host, path and catalog). Never a credential | only with `--force` |
| `dev/agents_schema/lookml_repo/agents-schema-lookml.yml` | with `--lookml-repo`: the one-job workflow for that repository, pinned to the same tag, publishing on the given ref (default `main`) from `--lookml-repo-dir`; to be committed there as `.github/workflows/agents-schema-lookml.yml` with the same `WAREHOUSE_CREDENTIALS` secret | always |
| `agents_schema/skills/<skill>.md` | every skill source copied. A colocated `DOMAIN_REFERENCE.md` becomes `skill/<domain>` with `uses.tables` derived from the models in its folder; a source with its own `uses:` is copied unchanged; a dbt `{% docs %}` block is skipped | always (they are derived) |
| `agents_schema/skills/warehouse_guide.md` | the draft guide: one section per subject area of the warehouse layer, one row per model with its table, keys and dates, and the two `wire: complete` markers | only with `--force` |
| `dev/agents_schema/plan.json`, `run.sh`, `checks.sql` | the plan, the local publication, the validate queries | always |

Read `plan.json`: `providers[]` (source, path, counts, the `AGENTS.*` tables each replaces, the workflow job; for a separate LookML repository also `source_repo`, `source_ref`, `publish_branch`, `local_clone` and `workflow_file`), `skills[]` (key, path, source, how the `uses:` came to be: `derived`, `kept` or `none`), `skipped[]`, `needs_human[]` (`no_manifest`, `no_dbt_profile`, `disabled_models_in_manifest`, `models_without_schema`, `empty_source`, `missing_source`, `lookml_repo_not_cloned`, `lookml_unparseable`, `uses_not_derived`, `duplicate_skill_key`, `draft_to_complete`, `bigquery_project_id_missing`) and `skipped_existing[]`.

A `--providers` list drops any planned provider not named; a provider named but not found is a stop, not a silent skip.

### Step 5: Complete the skills

This is the judgement half. Record every decision in the generation report as a row: `skill`, `section or field`, `plan proposed`, `kept | changed | dropped | added`, `why`.

1. **The warehouse guide.** Open `agents_schema/skills/warehouse_guide.md`. Fill **Business definitions** from `business_rules/register.md` where it exists (one entry per `agreed` rule: name, definition in plain words, the column and filter that implement it, the approver; a `disputed` or `unknown` rule is listed as such, never resolved here), else from the requirements' metric definitions. Fill **Known caveats** from the dbt work (stopped feeds, partial history, columns the models expose but nobody should use) or delete the section. Check the subject-area tables read correctly and fix a description the manifest lacks by fixing `schema.yml`, then re-running Step 3 and Step 4, not by editing the table. Remove both markers; validate fails while one remains.
2. **The knowledge files.** For each `uses_not_derived` item decide: write the `uses:` by hand (schema-qualified tables the skill may read), publish without one, or drop the file from the skills directory. For a `duplicate_skill_key`, rename one source. A skill whose body names tables its `uses:` does not list is a mismatch a reader will trip on; fix one or the other.
3. **What not to publish.** A skill is read by every agent with access to the warehouse. Nothing in `agents_schema/skills/` may hold a credential, a personal name outside the approver field, or client-internal text the engagement brief marks confidential. `skipped[]` and `needs_human[]` name what was left out; add anything you drop here to the report.
4. **Disabled models.** `disabled_models_in_manifest` means dbt still lists a disabled model under `nodes` and the CLI will publish it as a model. Either rebuild the manifest without it (usually a `dbt clean` then `dbt compile`) or accept it and say so in the report.
5. **The provider name.** Confirm it with the release director if the engagement context did not set it; it is visible in every skill row.

### Step 5.5: Offer to set the repository secrets from the dbt profile

The two secrets the workflow needs usually already exist, in a different shape, in the dbt profile the release builds with: a BigQuery service-account key (`keyfile_json` or `keyfile`), a Snowflake password or key pair, a Databricks token. Retyping them into the repository's settings is where a consultant who owns the repository loses an afternoon, and where a client-owned repository is rightly the client's job. So the command asks, once, unless a flag has already answered.

1. Skip this step, saying so in one line, when `--no-warehouse` is given, `budget.warehouse_spend` is `none`, `status.md` already records `agents_schema.secrets_set`, or `gh secret list` fails (not authenticated, or no rights on the repository).
2. Check what the profile can give:

   ```bash
   uv run --with pyyaml python3 <plugin>/scripts/agents_schema_secrets.py \
     --profiles-yml ~/.dbt/profiles.yml --profile <profile> --target <target> --check
   ```

   Exit 3 means the target's credential shape is not one the agents-schema CLI accepts (BigQuery OAuth, Snowflake SSO, Databricks OAuth). Record the reason and go to Step 6: the secrets are the repository owner's to add by hand.
3. With `--set-secrets` given, take option A below (with `--publish`) or B (without) and do not ask. Otherwise use AskUserQuestion:

   ```json
   {
     "questions": [{
       "question": "The dbt profile <profile>/<target> holds a <shape> the workflow's secrets can be built from. Set the repository secrets from it?",
       "header": "Secrets",
       "options": [
         {"label": "Set both secrets and publish now", "description": "gh secret set WAREHOUSE_CREDENTIALS and DBT_PROFILES_YML from the profile, then run the publication from this machine so validate can check the warehouse today"},
         {"label": "Set both secrets only", "description": "The workflow publishes on the next push to <branch>; nothing is written to the warehouse now"},
         {"label": "Leave both to the repository owner", "description": "Record the two secrets as the client's to add; the publication stays pending CI"}
       ],
       "multiSelect": false
     }]
   }
   ```

4. Act on the answer with the same script. With `--lookml-repo`, the same `WAREHOUSE_CREDENTIALS` is set on that repository too (`--repo <lookml owner/repo> --set-secrets --warehouse-only`; it needs no `DBT_PROFILES_YML`), so its workflow can run; without `gh` rights on it, record that the LookML repository's owner adds the secret. Option A: `--repo <owner/repo> --set-secrets --publish .wire/releases/<release>/dev/agents_schema/run.sh`. Option B: `--repo <owner/repo> --set-secrets`. Option C: nothing; record the choice. The script reads the one profile and target, builds `WAREHOUSE_CREDENTIALS` in the destination's shape and `DBT_PROFILES_YML` as that one profile and target (never the whole `profiles.yml`, which commonly holds other clients' credentials), passes both to `gh secret set` on stdin, and for option A runs `run.sh` with the credential in the child process's environment. It prints names, shapes and lengths only. Record `secrets_set: [WAREHOUSE_CREDENTIALS, DBT_PROFILES_YML]` in `status.md` and the option taken in the generation report.

On a client-owned repository, option C is the usual answer unless the engagement brief says the consultant holds the client's CI secrets; say so when asking.

### Step 6: Publish, or leave it to CI

Unless `--no-warehouse` or `budget.warehouse_spend: none`:

- **With `--publish`, or option A in Step 5.5:** run `bash .wire/releases/<release>/dev/agents_schema/run.sh` with `WAREHOUSE_CREDENTIALS` set in the environment (Step 5.5's script does this for option A; otherwise the consultant's shell provides it). On an Apple-silicon Mac set `UV_PYTHON=cpython-3.12-macos-aarch64-none` so `uvx` does not pick an Intel Python and fail building `cryptography`. It runs `uvx --from agents-schema==<version> agents-schema <source> ...` once per planned provider in order. Each run replaces that provider's table family with `CREATE OR REPLACE` and upserts its rows in `AGENTS.ROOT`, and leaves every other provider's rows alone. The write is a warehouse write; under `warehouse_spend: estimate_required` or a cap the cost governance rules of `specs/utils/director_operating_model.md` apply and the run is disclosed in the report. Record the command output (`dbt: N models, N columns, N deps`; `skills: N skills, N uses`) in the report.
- **Otherwise:** nothing runs. The workflow publishes on the next push to the default branch once the `WAREHOUSE_CREDENTIALS` secret exists (and `DBT_PROFILES_YML` where the plan says so), whether Step 5.5 set them or the repository owner does. The report says the publication is pending and `status.md` records `published: pending_ci`.

Never paste a credential into a file, a spec output or a chat; `run.sh` refuses to start without the environment variable for that reason.

### Step 7: Write the generation report

`.wire/releases/<release>/dev/agents_schema_generation_report.md`:

- the agents_schema tag, the CLI requirement (`agents-schema==<x.y.z>`), the destination and its `agents` schema
- the provider table from `plan.json`: source, path, counts, tables, job
- the skills table: key, source, `uses:` origin, and the decisions from Step 5
- every `needs_human` and `skipped` item with its decision
- the secrets: derived and set from the dbt profile (which profile and target, which shape), or left to the repository owner, or not derivable and why
- the publication: `ran from this machine` with the CLI output, or `pending CI` with the secrets the client has to add; with `--lookml-repo`, whether the LookML was published from the local clone and that the repository workflow still has to be committed there
- the files written and the files left alone (`skipped_existing`)

### Step 8: Update Status

```yaml
agents_schema:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: "{{TODAY}}"
  version: "v0.0.11"                 # the pinned agents_schema tag
  destination: bigquery | snowflake | databricks
  providers: []                      # dbt, looker, omni, osi, sigma, skills as planned
  skill_provider: "<publisher>"
  skills: []                         # skill keys
  workflow: ".github/workflows/agents-schema.yml"
  plan: "dev/agents_schema/plan.json"
  published: ran | pending_ci | not_run
  published_date: null
  secrets_set: []                    # [WAREHOUSE_CREDENTIALS, DBT_PROFILES_YML] when Step 5.5 set them
  lookml_repo: null                  # owner/repo@ref when the LookML publishes from its own repository
  lookml_repo_workflow: null         # dev/agents_schema/lookml_repo/agents-schema-lookml.yml, to commit there
  needs_human: N
  needs_human_resolved: N            # must equal needs_human before validate can pass
  guide_complete: true | false       # no wire: complete marker remains
```

Then follow `specs/utils/stale_artifact_check.md` for artifacts downstream of this one.

### Step 9: Sync to Jira and the Document Store (Optional)

Follow `specs/utils/jira_sync.md` (artifact `agents_schema`, action `generate`) and, if a document store is configured, `specs/utils/docstore_sync.md` with `artifact_id: agents_schema`, `artifact_name: Agents Schema publication`, `file_path: .wire/releases/[release_folder]/dev/agents_schema_generation_report.md`. A sync failure is logged and never blocks the command.

### Step 10: Report

```
## Agents Schema publication planned

**agents_schema:** <tag> · destination <type> (<project or account>) · schema AGENTS
**Workflow:**      .github/workflows/agents-schema.yml (N jobs) · agents.yml written | left unchanged

| Provider | Source | Counts | Tables | Job |
|---|---|---|---|---|

### Skills (provider <publisher>)
N skills: N copied with a derived uses:, N kept as authored, N without a uses: (decided), 1 warehouse guide (complete | N markers left)

### Publication
Secrets: set from the dbt profile <profile>/<target> | left to the repository owner | not derivable (<reason>)
Ran from this machine: <CLI output> | Pending CI: [add WAREHOUSE_CREDENTIALS and DBT_PROFILES_YML to the repository secrets, then] push to <branch> or run the workflow by hand

### Next steps
1. /wire:agents_schema-validate <release>
2. [with --lookml-repo] commit dev/agents_schema/lookml_repo/agents-schema-lookml.yml to <owner/repo> as .github/workflows/agents-schema-lookml.yml
3. /wire:agents_schema-review <release>
```

End with the commands that ran and the one that follows, in full (`specs/utils/director_operating_model.md` rule 7):

```
Ran: /wire:agents_schema-generate <release> [flags]
Next: /wire:agents_schema-validate <release>
```

## Edge Cases

### The release has no dbt project

`dbt_development`, `full_platform` and `dashboard_first` always have one. On `bi_migration` the plan may hold only the omni provider; that is a complete plan. On `dashboard_extension` the dbt project is the platform's existing one, found as the Inputs table says; when the repository holds only LookML, the plan may hold only the looker provider, which is also a complete plan. On any release type a plan with no provider at all stops with exit code 2 and the `needs_human` reasons; nothing is written.

### The client repository already has `.github/workflows/agents-schema.yml` or `agents.yml`

Neither is overwritten. Read the existing workflow before deciding: if it publishes the same providers from the same paths at the same or a newer pinned tag, keep it and say so; if it differs, either update it with `--force` after the client agrees, or record the difference in the report. `agents.yml` may also belong to the client's own use of the agents-schema plugin; read it first.

### Another team already publishes into `AGENTS`

`AGENTS.ROOT` is shared. Each provider's run replaces only its own table family and its own `ROOT` rows, so a second publisher of the same provider (two dbt projects, say) would overwrite the first. If validate's Check 9 later lists a provider the plan does not own, that is information, not a failure; two publishers of one provider is a decision for the release director and is recorded as such.

### A LookML file the upstream parser cannot read

The agents-schema LookML parser matches braces while honouring `'` and `"` quotes, and knows nothing of SQL `--` comments. An apostrophe inside such a comment in a `sql:` block (`-- clients who haven't renewed`) opens a quote that never closes, and the whole looker publish fails with `unterminated LookML block` and no file name. The plan runs the same check over every `*.lkml` it can see and names the files in a `lookml_unparseable` item with the line where the block opens. Reword the comment in the LookML (a comment-only change, in the LookML repository's own pull request when `--lookml-repo` is used); nothing else works around it, since the CLI reads the files as they are.

### The LookML is in its own repository and the dbt repository also has a `lookml/` folder

The folder in the dbt repository is usually generated output or a stale copy. `--lookml-repo` wins: the looker provider is planned from the named repository, the folder is ignored, and the report names it so nobody wonders why its files were not published. If the folder is in fact the served project, do not pass `--lookml-repo`.

### The consultant's `profiles.yml` holds many clients

It usually does. Step 5.5's script writes `DBT_PROFILES_YML` as the one profile and the one target the release uses and nothing else, and never prints a value. Check the `--check` output's `profiles` and `targets` lists before accepting the offer if in doubt; `wire/tests/development/validate_agents_schema_secrets.py` holds the trimming rule.

### `warehouse_spend: none`

The publication does not run, Step 5.5 is skipped, and `--publish` is refused with the setting named. The plan, the workflow, `agents.yml` and the skills are still written. `agents_schema-validate` records every warehouse check as `unverified`, which is not a pass.
