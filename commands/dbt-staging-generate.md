---
description: Generate dbt staging-layer models only (alternative to the monolithic dbt-generate)
argument-hint: <project-folder>
---

# Generate dbt staging-layer models only (alternative to the monolithic dbt-generate)

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
    'command': 'dbt-staging-generate',
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
command: utility
artifact: dbt
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: utility
logs_execution: true
preconditions: dynamic
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
description: Generate dbt staging models (stg_) that clean and standardize raw source data
argument-hint: <project-folder> [--slice <slice>]
delegates_to:
  - utils/precondition_gate
---

# dbt Staging Models — Generate

## Purpose

Generate the staging layer of the dbt project: one model per source concept, applying cleaning, renaming, type casting and natural key extraction. Primary and foreign keys are created later, in the warehouse layer. Only staging models may read sources, snapshots and seeds; all other layers use `{{ ref() }}` to models.

## Existing projects

These rules apply before every other rule in this spec.

- Never rename or move an existing model, column, seed, snapshot or schema. The conventions below apply to new and changed code only.
- Where the project keeps an old form (for example singular staging names, unprefixed columns, `tests:`, or `_<source>__sources.yml`), follow the ruling recorded in the release's `decisions.md` and the `form_choices:` block in the project's `.wire/conventions/dbt.yml`. Generate new models in that form. Keys: `model_name_number: plural|singular`, `column_prefix: entity|none`, `test_key: data_tests|tests`, `source_file_name: _sources|_<source>__sources`.
- Where no ruling exists, generate new models in the new form. Mixed naming inside one project is allowed.
- Do not change `dbt_project.yml` or `packages.yml` in an existing project. Report differences from the new-project templates in `specs/development/dbt_generate.md` (Step 8) as suggestions only.
- Keep the date-cast macro the project already uses (`type_date()` or similar). `ra_type_date()` is for new projects.

A project is new when this command creates its `dbt_project.yml`; otherwise it is existing.

## Prerequisites

- `data_model`: dbt model design specification must be complete — read `.wire/<project_id>/design/data_model_specification.md`

This is the first step of the per-layer alternative to the monolithic `/wire:dbt-generate` — it can be run standalone on any project that has an approved data model, without `dbt-generate` having been run first.

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the slice's staging models and their `schema.yml` entries only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. The precondition gate evaluates this slice's dependencies, not the whole
   release's (`specs/utils/precondition_gate.md`, "Sliced runs").
3. Add or replace the slice's part only. Never regenerate the whole document
   or project to change one slice; every other line stays as it is.
4. On a ticket branch, write the step's result to the ticket record's front
   matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`. The status and Jira or Linear updates in the workflow
   below are made by `/wire:status-sync`'s ticket roll-up when the pull request
   merges.

## Workflow

### Step 1: Read Data Model Design

Read `.wire/<project_id>/design/data_model_specification.md` and extract:
- Source systems and tables
- Column mappings and renames
- Required tests and naming conventions

### Step 2: Load Naming Conventions

Priority order:
1. Rulings: `decisions.md` in the release, and `form_choices:` in the project's `.wire/conventions/dbt.yml`
2. Project-specific: `.wire/conventions/dbt.yml`, `.dbt-conventions.md`, `dbt_coding_conventions.md`, or `docs/dbt_conventions.md` in repo root
3. Embedded conventions below (fallback). The full tables are in `specs/development/dbt_generate.md`, Step 3.

**Naming conventions (staging):**

| Type | Pattern | Example |
|------|---------|---------|
| Model | `stg_<source>__<entities>` (plural) | `stg_salesforce__contacts` |
| Base model | `base_<source>__<entities>` | `base_salesforce__contacts` |
| Natural Key | `<entity>_natural_key`; on another entity it takes this model's prefix. Never lowercased | `contact_natural_key`, `contact_account_natural_key` |
| Attribute | `<entity>_<attribute>`, no suffix | `contact_email` (not `email`) |
| Count | `<entity>_<thing>_count` | `order_line_count` |
| Money | `<entity>_<measure>_amount` (base currency), `_amount_<currency>` otherwise; decimal, converted from cents here | `user_account_balance_amount`, `order_revenue_amount_usd` |
| Measured quantity | `<entity>_<measure>_<unit>` | `package_weight_kg`, `call_duration_seconds` |
| Percentage / ratio | `_pct` (0 to 100), `_ratio` (0 to 1) | `order_discount_pct` |
| Boolean | `<entity>_is_<state>`, `<entity>_has_<thing>`, `<entity>_was_<event>` | `user_is_active` |
| Date | `<entity>_<event>_dt` | `user_created_dt` |
| Timestamp (UTC) | `<entity>_<event>_ts` | `user_created_ts` |
| Timestamp (non-UTC) | `<entity>_<event>_<tz>_ts` | `user_created_cet_ts` |

Primary and foreign keys are not created in staging. They are created in the warehouse layer.

**Lowercasing:** lowercase attribute strings only. Never lowercase natural keys or source identifiers (some are case-sensitive, for example Salesforce 15-character IDs).

**Type Casting:** always use cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_int() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`. Dates use `{{ ra_type_date() }}` in new projects; an existing project keeps its date macro (for example `{{ type_date() }}`). Timestamps are cast to UTC.

**SQL style:** 4-space indent, lines up to 120 characters, lowercase, explicit joins, all refs in CTEs prefixed `s_`, last CTE named `final`, model ends with `select * from final`, Jinja delimiters with inner spaces (`{{ this }}`). Every model's `config()` carries a `description` whose first line is `Grain: One row per ...`. A CTE that removes rows carries a plain-English comment saying why.

**Field ordering in `select` lists:** eight groups, each opened by a Jinja comment: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`. Staging models have no primary or foreign key groups.

**Staging design rules:**
- Only staging models read sources, snapshots and seeds.
- Joins are avoided. A join or union is allowed only within one source system, in a base model or base CTE.
- Filtering is limited to correctness (deduplication, rows known to be erroneous). Population and grain are preserved.
- Nested records are flattened. Repeated fields are carried through unchanged unless queried downstream.
- Single-row derivations are allowed. Repeated logic becomes a macro (`macros/macro__<name>.sql`, described in `macros/_schema_macros.yml`).

### Step 3: Determine dbt Project Location

Check for existing dbt project at `dbt/`, `transform/`, or similar. If ambiguous, ask the user. Default to `dbt/`.

### Step 4: Generate Staging Models

For each source concept, create:

**File:** `dbt/models/staging/stg_<source>/stg_<source>__<entities>.sql`

```sql
{{
    config(
        description = """
            Grain: One row per <entity> in <source table>.
            <What the model holds, as received from <source>.>
        """,
        tags = ['staging', '<source>']
    )
}}

with s_<source_table> as (

    select * from {{ source('<source>', '<table_name>') }}

),

-- Keeps the latest copy of each row. The loading tool can write a row more than once.
deduplicated as (

    select * from s_<source_table>
    qualify row_number() over (partition by <id_column> order by <loaded_at_column> desc) = 1

),

rename_and_cast as (

    select

        {# natural keys #}
        cast(<id_column> as {{ dbt.type_string() }}) as <entity>_natural_key,
        {# attributes #}
        lower(trim(cast(<name_column> as {{ dbt.type_string() }}))) as <entity>_name,
        {# metrics #}
        cast(<cents_column> as {{ dbt.type_numeric() }}) / 100 as <entity>_<measure>_amount,
        {# booleans #}
        cast(<status_column> as {{ dbt.type_boolean() }}) as <entity>_is_<state>,
        {# temporal #}
        cast(<date_column> as {{ ra_type_date() }}) as <entity>_<event>_dt,
        cast(<timestamp_column> as {{ dbt.type_timestamp() }}) as <entity>_<event>_ts

    from deduplicated

),

final as (

    select * from rename_and_cast

)

select * from final
```

**Base models (where needed):** `dbt/models/staging/stg_<source>/base_<source>__<entities>.sql` holds a join or union within one source system. Only the staging model of the same concept reads it. It takes its view materialization from the folder config.

**Snapshots (where needed):** `dbt/snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`. The `{% snapshot %}` block name equals the file name. `timestamp` strategy by default; `check` with `check_cols` where the source has no reliable modified timestamp. Source columns unchanged; dbt meta columns keep their names. New projects write to the `snapshots` schema; an existing project keeps its snapshot schema. The staging model reads the snapshot as it reads a source.

**Seeds:** in a new project or new release, seed files are `seeds/seed__<description>.csv` in the `seeds` schema, with the CSV's column names. Only staging models read seeds. Dashboard-first mock seeds in a release already under way keep their names, so `data_refactor` still finds them.

**Also create:** `dbt/models/staging/stg_<source>/_sources.yml` (one per source folder; `_<source>__sources.yml` where a `source_file_name` ruling keeps it). Content rules:
- One source, named for the folder without `stg_`. `schema` and `loader` set.
- Table `name` is the business name; `identifier` holds the raw name where different.
- Table description opens `Grain: ...`, then `Source table group:` where relevant, then what it holds and how it is loaded, and ends with a `Use it for ...` sentence.
- Every column of a declared table declared under its source name, including loader columns such as `_fivetran_synced`. Descriptions written inline (no doc blocks): meaning in the source, unit, time zone, null meaning, allowed values. Identifier columns name where the same value is held elsewhere. Personal data columns carry "Personal data.". Profiled figures carry the date measured.
- `freshness` (with `loaded_at_field`) is the only test. `warn_after` and `error_after` are set per client project.

The full template is in `specs/development/dbt_generate.md`, Step 3.

**Also create:** `dbt/models/staging/stg_<source>/_schema.yml` for the staging and base models (not where the project uses droughty, which writes `models/droughty_schema.yml`). An existing project adds entries to its current schema file (for example `stg_<source>.yml`). Every column references a doc block held in `models/field_descriptions.md` (`'{{ doc("<column>") }}'`).

Tests:
- The natural key that identifies a row: `unique` + `not_null`.
- Other columns: `not_null` + `dbt_utils.at_least_one`. `at_least_one` is added alongside `not_null`, never in place of it. Drop `not_null` only where the column can be null, keep `at_least_one`, and note the reason in the summary.
- Test key: `data_tests:` on dbt 1.8 or later, `tests:` before. Find the version from `dbt --version`, `require-dbt-version` in `dbt_project.yml`, or the dbt or adapter version pinned in requirements. A `form_choices: test_key` ruling wins. In a schema file that already uses `tests:`, keep `tests:`. If the version cannot be found, write `tests:`. Never both keys on one resource.

### Step 5: Generate dbt_project.yml (if new project)

New project: create `dbt/dbt_project.yml` and `dbt/packages.yml` from the templates in `specs/development/dbt_generate.md`, Step 8: layer configs under the real project name, `+persist_docs` for relation and columns, staging and integration as views in the `staging` and `integration` schemas, warehouse as tables with `+meta` `required_docs: true` and `required_tests: {"unique": 1, "not_null": 1}`, seeds in `seeds`, snapshots in `snapshots`, and the `dbt_meta_testing` package beside `dbt_utils`. A project that uses droughty sets `required_docs: false`. Also create `dbt/macros/utility/macro__type_date.sql` (defines `ra_type_date()`) and its entry in `dbt/macros/_schema_macros.yml`.

Existing project: do not change `dbt_project.yml` or `packages.yml`. List differences from the templates in the summary as suggestions only. Correcting the project key can change which models build as tables or views.

### Step 5.5: Convention Self-Check

Resolve the convention file: the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`. Then run:

```bash
# New project
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/staging --new-project

# Existing project (added and changed models only)
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/staging \
  --changed-from "$(git merge-base HEAD <release branch>)"
```

Fix every `error` finding in the generated models without renaming or moving anything that already existed. List warnings in the summary with a reason.

### Step 6: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_staging_summary.md`

Include: whether the project is new or existing, the convention file and any `form_choices:` rulings applied, the test key used, staging and base models created with their grain, snapshots, source tables covered, tests configured (and any column where `not_null` was dropped, with the reason), the convention lint result, and, for an existing project, the `dbt_project.yml` / `packages.yml` suggestions.

### Step 7: Update Status

Update `.wire/<project_id>/status.md`:
```
dbt_staging:
  generate: complete
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt_staging`
- `artifact_name`: `dbt Staging Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_staging_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Suggest Next Steps

```
## Staging Models Generated

- <count> staging models created in dbt/models/staging/
- Next: /wire:dbt-staging-validate <project_id>
- Then: /wire:dbt-integration-generate <project_id>
```

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

From 4.1.0 the Wire mod (`hooks/register.ts`, a function hook in the Claude
Code plugin) fills the metric cells. It replaces the `Stop` settings hook
(`hooks/wire-metrics.sh` and `wire_metrics.py`), which re-read the session
transcript after each turn.

1. Each Wire command opens a run when it starts: a typed `/wire:` command, or
   a Wire command called through the Skill tool by the orchestrating session,
   a lane or Autopilot.
2. Every model request adds its measured usage to the run open in its own
   loop (the main session, or one subagent). Counts come only from the usage
   the API reports, never estimates.
3. When that loop's turn ends, the run closes and the mod fills the
   Duration (only if still `n/a`), Tokens and Cost cells of the newest row
   whose Command cell names the command, whose Tokens cell is still `n/a`, and
   which is dated no earlier than the day before the run started (a date, not
   a time, because commands write the row's time themselves and it is often
   rough). It
   never touches another cell or row, and never widens a row without the
   metric columns.
4. A row written after the run closed (an orchestrating session writing a
   lane's row once the lane reports) is filled when that write happens.
5. Cost comes from the mod's price table; an unrecognised model leaves Cost
   at `n/a` with Tokens filled.

`/wire-usage` prints the session's runs with their duration, tokens and cost.
The plugin's `metrics` option, or `WIRE_METRICS=false`, turns the backfill
off. On runtimes without the mod (Gemini CLI), the metric cells keep the
values the workflow wrote.

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
