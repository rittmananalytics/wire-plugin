---
description: Publish the release's metadata into the warehouse AGENTS schema for AI agents: plan the providers (dbt manifest, LookML, Omni, OSI, Sigma, skills), write the pinned GitHub workflow, agents.yml and the skills, complete the warehouse guide, offer to set the repository secrets from the dbt profile, publish from CI or with --publish; --lookml-repo publishes LookML from its own repository
argument-hint: <release-folder> [--providers <list>] [--skills-source <path>]... [--lookml-repo <owner/repo[@ref]>] [--provider <name>] [--no-guide] [--set-secrets] [--publish] [--no-warehouse] [--force]
---

# Publish the release's metadata into the warehouse AGENTS schema for AI agents: plan the providers (dbt manifest, LookML, Omni, OSI, Sigma, skills), write the pinned GitHub workflow, agents.yml and the skills, complete the warehouse guide, offer to set the repository secrets from the dbt profile, publish from CI or with --publish; --lookml-repo publishes LookML from its own repository

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'agents_schema-generate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: agents_schema
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
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

`dbt_development`, `full_platform` and `dashboard_first` always have one. On `bi_migration` the plan may hold only the omni provider; that is a complete plan. On any release type a plan with no provider at all stops with exit code 2 and the `needs_human` reasons; nothing is written.

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

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
