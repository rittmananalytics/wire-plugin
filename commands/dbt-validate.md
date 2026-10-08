---
description: Run dbt tests and validation
argument-hint: <project-folder>
---

# Run dbt tests and validation

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
    'command': 'dbt-validate',
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

## Workflow Specification

---
wire_schema: "1.0"
command: validate
artifact: dbt
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: dbt
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate dbt models - run tests, check conventions, verify documentation and testing coverage
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Validation Command

## Purpose

Validate generated dbt models by running dbt tests, checking naming conventions, verifying SQL structure, model configuration, testing coverage, documentation coverage, and optionally running sqlfluff. Produces a structured validation report with severity-rated issues.

The conventions follow the RA dbt development reference (adopted in Wire 4.1.2). Wire never renames or moves an existing model, column, seed, snapshot or schema, so an existing project keeps passing this command. See **Scope and Severity** below.

## Scope and Severity

Three kinds of rule apply. Each check in Step 3 onward is marked with its kind where it matters.

| Kind | What it covers | Applies to | Effect of a breach |
|------|----------------|------------|--------------------|
| **Carried rule** | A rule this spec checked before 4.1.2 (key naming, `ref()` in top CTEs, `select * from final`, explicit joins, PK tests, warehouse as `table`, line length, now 120) | All models | Severity as stated in the check |
| **Accepted form** | A choice where the new form and the older form are both valid (table below) | All models | Never a finding. Either form passes |
| **Reference rule** | A rule new in 4.1.2 (`Grain:` line, column docs in every layer held as doc blocks, new column suffixes, base/snapshot/macro/seed file names, source declaration content, macro entries, Jinja spacing, YAML style, comments on row-removing CTEs) | Models in the changed set only (Step 1.6) | Important and sets status FAIL, unless the check marks it advisory or warning. Never Critical |

**Accepted forms.** Both columns pass. Generate writes the new form unless the project has a `form_choices:` ruling in `.wire/conventions/dbt.yml` (recorded in the release's `decisions.md`). Mixed naming inside one project is allowed.

| Area | New form | Older form, still accepted |
|------|----------|---------------------------|
| Staging and integration model names | Plural: `stg_salesforce__users`, `int_core__users` | Singular: `stg_salesforce__user`, `int_core__user` |
| Warehouse model names | Singular: `wh_core__user_dim` | Same |
| Column prefixes | Entity prefix on every output column: `user_name` | Unprefixed: `name` |
| Boolean names | `user_is_active` | `is_active` |
| Test key in YAML | `data_tests:` | `tests:` (a resource that uses both is a finding) |
| Source file name | `_sources.yml` | `_<source>__sources.yml` |
| Schema file name (no droughty) | `_schema.yml` per subdirectory | Existing names: `stg_<source>.yml`, `integration.yml`, `wh_<group>.yml`, `intermediate.yml` |
| Intermediate model materialization | `view`, set by folder | `ephemeral` |
| Warehouse aggregate | `_xa` | Existing `_agg` models |
| Seeds | `seeds/seed__<description>.csv` in the `seeds` schema | Existing names and schema |
| Snapshots | `snapshots` schema | Existing schema |

**No git history.** Where the changed set cannot be worked out (Step 1.6), reference rules are checked on every model and reported as warnings (Nice-to-have). They do not set status FAIL.

**Unchanged models.** Nothing the pre-4.1.2 spec accepted is a Critical finding on an unchanged model. A reference rule never applies to an unchanged model when git history is available.

> **Per-layer alternative**: If the dbt project was built layer-by-layer instead of via `/wire:dbt-generate`, validate each layer with its own command instead: `/wire:dbt-staging-validate`, `/wire:dbt-integration-validate`, `/wire:dbt-warehouse-validate` — run after the corresponding `/wire:dbt-*-generate` command.

## Usage

```bash
/wire:dbt-validate YYYYMMDD_project_name
```

## Prerequisites

- dbt models must be generated (`/wire:dbt-generate` complete)
- dbt models must be run successfully (`/wire:utils-run-dbt` complete)
- dbt Cloud or dbt Core configured

## Workflow

### Step 1: Verify dbt Models Exist

**Process**:
1. Check that `dbt.generate == complete` in status.md
2. Verify dbt models exist in `dbt/models/`

**If not generated**:
```
Error: dbt models not generated yet.

Run `/wire:dbt-generate [folder]` first.
```

### Step 1.5: Load Convention Source

**Resolution order:**

1. **Project override**: `.wire/conventions/dbt.yml` in the engagement repo, if present. Read its `form_choices:` block if it has one (keys: `model_name_number`, `column_prefix`, `test_key`, `source_file_name`). A `form_choices:` value is a ruling recorded in the release's `decisions.md`. It tells generate which form to write. Validate still accepts both forms.
2. **Plugin default**: `<plugin>/conventions/dbt.yml`.

The resolved file is the `--convention` argument for the lint in Step 2.5.

**Prose conventions document.** If the project has its own prose conventions document (for example `docs/development_reference_dbt.md`, or the older `docs/dbt_coding_conventions.md`, `dbt_coding_conventions.md` or `.dbt-conventions.md`), read it for context. Where it states a rule the YAML file does not, apply the rule by reading the code. It does not replace the YAML file.

Record in the report which convention file resolved, whether it has `form_choices:`, and which prose document (if any) was read.

### Step 1.6: Work Out the Changed Set

Reference rules (see **Scope and Severity**) apply to new and changed files only. Work out the set before running any check.

**Process:**
1. Find the base ref: the branch the release branch was cut from (usually `main`, or the release's integration branch named in `status.md`).
2. Run `git merge-base HEAD <base branch>` to get the base commit.
3. Run `git diff --name-status <base commit>...HEAD -- <dbt project dir>` and add uncommitted changes from `git status --porcelain`.
4. Classify each path:
   - **Added** (`A`, or untracked): new file.
   - **Modified** (`M`, `R`): changed file. A renamed file counts as changed, not added.
   - Anything else: unchanged.
5. A model is in scope when its `.sql` file is added or modified, or its entry in a schema file changed.
6. File-naming rules for new kinds (base model, snapshot, macro, seed) apply to **added** files only. Editing an existing macro, seed or snapshot never asks for a rename.

**If git is not available** (not a repo, shallow clone without the base, or no base branch found): record "changed set unknown". Reference rules then run on all models and report as warnings only.

**Report** the base ref and commit, and list the models in scope (added and modified) in the report's Scope section.

### Step 2: Run dbt Tests

**Process**:
1. Ask user how to run tests:
   - dbt Cloud (API call)
   - dbt Core (local command)
   - Show manual command

**For dbt Core**:
```bash
cd dbt/
dbt test
```

**Capture test results**:
- Total tests run
- Tests passed
- Tests failed (with details)

### Step 2.5: Run the Convention Lint

Run the deterministic convention check. It is a plain script with no AI call. Run it before the semantic checks in Step 3, and trust its findings over a reading of the code where the two disagree.

**With a changed set** (Step 1.6 found a base commit):
```bash
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention file> \
  --path <dbt project dir>/models \
  --changed-from <base commit> \
  --format json
```

**Without git**: drop `--changed-from`. The script then reports reference rules as warnings.

**New project** (every file is new, for example the first `/wire:dbt-generate` run): `--new-project` in place of `--changed-from`.

Run it again with `--path` set to `snapshots/`, `seeds/` and `macros/` where those directories exist.

**Fold the findings into the report:**
- Each finding goes under the Step 3 heading it belongs to, with its rule id and file.
- A script `error` on a carried rule keeps the severity stated in Step 3.
- A script `error` on a reference rule for a changed file is Important. A script `warning` is Nice-to-have.
- If the script is not found, note "convention lint not run" in the report and do the Step 3 checks by reading the code.

### Step 2.6: Run dbt_meta_testing Checks (If Installed)

Only where the project's `packages.yml` includes `tnightengale/dbt_meta_testing`:

```bash
dbt run-operation required_tests
dbt run-operation required_docs
```

- Skip `required_docs` when the project uses droughty (a `droughty_project.yaml` exists, or `dbt_project.yml` sets `required_docs: false`). droughty does not write model descriptions, so the check would fail on every warehouse model.
- Both run against built models, so run them after `dbt run` or `dbt build`.
- Include each result in the report's Testing Coverage and Documentation Coverage sections. A failure of either is Important.
- Where the package is not installed, note "dbt_meta_testing not installed" and continue. Never add the package to an existing project.

### Step 3: Check Naming Conventions

#### 3.1 File and Model Naming

Entity names may be plural or singular in staging and integration models. Neither is a finding. Warehouse model names are singular in both forms.

| Kind | New form (generate) | Also accepted | Example | Applies to | Severity |
|------|---------------------|---------------|---------|------------|----------|
| Base model | `base_<source>__<entity>.sql` in `models/staging/stg_<source>/` | (new kind) | `base_salesforce__users.sql` | Added files | Important |
| Staging model | `stg_<source>__<entity>.sql`, entity usually plural | Singular entity | `stg_salesforce__users.sql`, `stg_salesforce__user.sql` | All models | Critical |
| Intermediate model | `int_<group>__<entity>__<verb>.sql` in `int_<group>/intermediate/`, verb in past tense | Singular entity | `int_core__users__unioned.sql` | All models | Critical |
| Integration model | `int_<group>__<entity>.sql` | Singular entity | `int_core__users.sql`, `int_core__user.sql` | All models | Critical |
| Warehouse dimension | `wh_<group>__<entity>_dim.sql` | Same | `wh_core__user_dim.sql` | All models | Critical |
| Warehouse fact | `wh_<group>__<entity>_fact.sql` | Same | `wh_finance__transaction_fact.sql` | All models | Critical |
| Warehouse extended aggregate | `wh_<group>__<entity>_xa.sql`: a denormalised table built from fact and dimension models, either aggregated to a summary grain or combining several facts at a shared grain | Existing `_xa` models built as bridge or cross-attribute tables | `wh_engagement__engagement_xa.sql` | All models | Critical |
| Warehouse aggregate (older form) | Not generated for new models | `wh_<group>__<entity>_agg.sql` | `wh_core__course_summary_by_year_agg.sql` | All models | Critical if the suffix is malformed; `_agg` itself is never a finding |
| Snapshot | `snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`, `{% snapshot %}` block name equals the file name | Existing names | `snapshot_salesforce__accounts.sql` | Added files | Important |
| Seed | `seeds/seed__<description>.csv`, `seeds` schema. Columns keep the CSV's names | Existing names and schema | `seed__sku_category_lookup.csv` | Added files in a new project or new release | Important |
| Macro | `macros/macro__<name>.sql`, one macro per file, adapter versions (`default__`, `bigquery__`, `snowflake__`) in the same file. Utility macros in `macros/utility/`. dbt override macros (`generate_schema_name` and similar) keep their dbt names | Existing names | `macro__geo_country.sql` | Added files | Important |
| Files | Lowercase with underscores only | Same | ✅ `wh_core__user_dim.sql` ❌ `StudentDim.sql` | All models | Critical |

Dashboard-first mock seeds in a release already under way keep their names, so `/wire:data_refactor-generate` still finds them.

**Directory Structure Check** (new form; the older file names in the accepted-forms table also pass):
```
models/
├── field_descriptions.md              # doc blocks for column descriptions
├── staging/
│   └── stg_<source>/
│       ├── _sources.yml               # or _<source>__sources.yml
│       ├── _schema.yml                # or stg_<source>.yml
│       ├── base_<source>__<entity>.sql
│       └── stg_<source>__<entity>.sql
├── integration/
│   └── int_<group>/
│       ├── intermediate/
│       │   ├── _schema.yml            # or intermediate.yml
│       │   └── int_<group>__<entity>__<verb>.sql
│       ├── _schema.yml                # or integration.yml
│       └── int_<group>__<entity>.sql
└── warehouse/
    └── wh_<group>/
        ├── _schema.yml                # or wh_<group>.yml
        ├── wh_<group>__<entity>_dim.sql
        ├── wh_<group>__<entity>_fact.sql
        └── wh_<group>__<entity>_xa.sql
macros/
├── _schema_macros.yml
├── macro__<name>.sql
└── utility/
snapshots/
└── snapshot_<source>/
    └── snapshot_<source>__<source_table>.sql
seeds/
└── seed__<description>.csv
```

Projects that use droughty hold model schema in `models/droughty_schema.yml` in place of per-directory schema files. That passes.

**Violations to Flag:**
- Missing or incorrect layer prefixes or suffixes
- Non-standard directory structure
- Mismatched filename and directory location
- Added base, snapshot, macro or seed files that do not follow the new pattern
- A `{% snapshot %}` block name that differs from its file name (added snapshots)

Plural or singular entity names are not a finding.

#### 3.2 Field Naming Conventions

For each model, check ALL fields against these conventions:

| Type | Pattern | Example | Applies to | Severity |
|------|---------|---------|------------|----------|
| Primary Key | `<entity>_pk`, generated via `dbt_utils.generate_surrogate_key(...)` | `user_pk`, `transaction_pk` | All models | Critical |
| Foreign Key | `<referenced_entity>_fk`, generated via `dbt_utils.generate_surrogate_key(...)`. Keeps the referenced entity's prefix | `user_fk`, `account_fk` | All models | Critical |
| Natural Key | `<descriptive_name>_natural_key`. On another entity it takes that model's prefix | `user_natural_key`, `order_user_natural_key` | All models | Important |
| Date | `<event>_dt` | `user_created_dt` | All models | Important |
| Timestamp (UTC) | `<event>_ts`, always UTC | `user_created_ts`, `created_ts` | All models | Important |
| Timestamp (non-UTC) | `<event>_<tz>_ts`, time zone before `_ts` | `user_created_cet_ts` | All models | Important |
| Boolean | `is_`, `has_` or `was_` at the start, or after the entity prefix | `user_is_active`, `is_active`, `has_subscription` | All models | Important |
| Money, base currency | `_amount`, decimal currency, converted from cents in staging | `user_account_balance_amount` (not `price_in_cents`) | All models | Important |
| Money, other currency | `_amount_<currency>`, ISO 4217 code lowercased | `revenue_amount_usd` | Changed models | Important |
| Count | `_count`: a count of things | `order_line_count` | Changed models | Important |
| Rank | `_rank`: an ordinal position | `revenue_rank` | Changed models | Important |
| Measured quantity | `_<measure>_<unit>`: SI symbol lowercased where one exists (`kg`, `km`, `ml`), else the unit spelled out (`seconds`, `days`). Currency is the only measure whose unit may be implicit | `package_weight_kg`, `session_duration_seconds` | Changed models | Important |
| Percentage | `_pct`: a value from 0 to 100 | `discount_pct` | Changed models | Important |
| Proportion | `_ratio`: a value from 0 to 1. A `_pct` column holding 0 to 1, or a `_ratio` column holding 0 to 100, is a finding | `conversion_ratio` | Changed models | Important |
| Attribute | No suffix | `user_name` | Changed models | Nice-to-have |
| Entity prefix | Every output column carries the entity prefix of the model. FKs keep the referenced entity's prefix. Two columns about the same thing are told apart by the relationship after the prefix (`order_shipping_country_name`, `order_billing_country_name`) | `user_name`, not `name` | Changed models | Advisory (Nice-to-have, never a failure) |
| Aggregated column | Leads with the aggregate function, then the source column name | `sum_invoice_line_item_amount`, `max_by_activity_user_name` | Changed models | Advisory (Nice-to-have, never a failure) |

Seed columns keep the CSV's names. Snapshot meta columns (`dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`, `dbt_updated_at`) keep their dbt names. Neither is a finding.

**Type Casting:**
- Use dbt's cross-database type macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`.
- For dates, new projects use the project macro `{{ ra_type_date() }}` (in `macros/utility/macro__type_date.sql`). An existing project keeps the date macro it already uses (`{{ type_date() }}` or similar). Either passes.
- This keeps models portable across warehouses (BigQuery / Snowflake / Databricks / Postgres).

**General Rules:**
- All names in `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models (same field names for same concepts)

**Violations to Flag:**
- Inconsistent naming patterns across models
- Missing `_pk`/`_fk` suffixes; PKs/FKs not generated via `dbt_utils.generate_surrogate_key`
- Timestamps without `_ts` suffix; dates without `_dt` suffix; non-UTC timestamps without a timezone tag before `_ts`
- Booleans without `is_`/`has_`/`was_` at the start or after the entity prefix
- Revenue columns without `_amount` suffix
- Raw SQL type casts instead of `dbt.type_*()` macros
- Reserved words as column names
- Changed models: counts, ranks, measured quantities, percentages and proportions without the suffixes above

Unprefixed columns (`name`, `is_active`) are not a finding on any model. On a changed model the missing entity prefix is advisory only.

#### 3.3 Field Ordering

Advisory on all models (Nice-to-have, never a failure). Check that fields in each model's final `select` list follow this order, each group opened by a Jinja comment:

1. `{# primary key #}`
2. `{# foreign keys #}`
3. `{# natural keys #}`
4. `{# attributes #}`: dimensions, slicing fields, descriptive columns
5. `{# indexes and ranks #}`: `row_number()`, `_rank` columns, sequence positions
6. `{# metrics #}`: measures, `_amount`, `_count`, `_pct`, `_ratio` columns
7. `{# booleans #}`: `is_`, `has_`, `was_` flags
8. `{# temporal #}`: `_dt`, `_ts` columns last

The older six-group order (keys, attributes, indexes/ranks, metrics, booleans, temporal) also passes. Missing group comments are noted for changed models only.

### Step 3.5: Validate SQL Structure

For each model file, check:

#### CTE Structure

| Check | Rule | Severity |
|-------|------|----------|
| Refs at top | All `{{ ref() }}` and `{{ source() }}` calls in top CTEs | Critical |
| CTE naming | `s_` prefix for ref/source CTEs | Important |
| Final CTE | Last CTE is named `final` and the model ends with `select * from final` | Critical (unchanged from earlier versions) |
| One logical unit | Each CTE does one transformation | Info |
| Row-removing CTE (changed models) | A CTE that filters out rows carries a comment saying why | Important |

**Required Pattern:**
```sql
with s_source_table as (

    select * from {{ ref('source_model') }}

),

transformation_cte as (

    select ... from s_source_table

),

final as (

    select * from transformation_cte

)

select * from final
```

#### Layer Boundaries

| Check | Rule | Applies to | Severity |
|-------|------|------------|----------|
| Sources | Only staging and base models select from `{{ source() }}` | All models | Critical |
| Staging inputs | A staging model reads sources, base models, snapshots and seeds | All models | Important if it reads a warehouse model |
| Base models | Read only by the staging model of the same source. Later layers read staging models, not base models | Changed models | Important |
| Seeds | Read only by staging models | Changed models | Important |
| Staging joins | No join or union except within one source system | Changed models | Important |
| Integration inputs | Staging models, intermediate models and other integration models | All models | Important if it reads a warehouse model |
| Warehouse inputs | Integration models, or staging models where no integration model is needed. `_xa` models also read `_dim` and `_fact` models | All models | Critical if it reads `{{ source() }}` |

**Violations to Flag:**
- `ref()` or `source()` calls outside of top CTEs
- Missing final CTE
- Non-staging models selecting from `{{ source() }}` (base models count as staging)
- Integration or warehouse models reading a base model (changed models)

#### SQL Style

| Check | Rule | Severity |
|-------|------|----------|
| Indentation | 4 spaces (not tabs) | Important |
| Line length | Max 120 characters | Info |
| Case | Lowercase field names and SQL functions | Important |
| Aliases | Always use `as` keyword | Important |
| Joins | Explicit: `inner join`, `left join` (never just `join`) | Critical |
| Table aliases | Full descriptive names, not initialisms (`customer`, not `c`) | Important |
| Column prefixes | Required when joining 2+ tables | Important |
| Union | `union all` preferred over `union distinct` | Info |
| Group by | Column names, not numbers | Important |
| Jinja spacing (changed models) | Delimiters carry inner spaces: `{{ this }}`, not `{{this}}` | Warning (Nice-to-have) |
| Comments (changed models) | Plain English, full column names, the business's own terms | Info |

**YAML style** (changed schema and source files): 2-space indent, list items indented, lines up to 80 characters. Warning (Nice-to-have) only.

**Violations to Flag:**
- Implicit joins or missing join qualifiers
- Hard-to-understand table aliases (single letters)
- Uppercase SQL keywords or functions
- Improper indentation, or lines over 120 characters

### Step 3.6: Validate Model Configuration

| Check | Rule | Severity |
|-------|------|----------|
| Warehouse models | Materialized as `table`, or `incremental` where the client chose it for that model | Critical |
| Staging and base models | `view` or ephemeral (not `table` unless performance requires) | Important |
| Integration models | `view` or ephemeral (not `table` unless performance requires) | Important |
| Intermediate models | `view` set by the folder config, or `ephemeral`. Both pass | Important if `table` without a stated reason |
| Snapshots | `timestamp` strategy, or `check` with `check_cols` where the source has no reliable modified timestamp. Source columns unchanged | Important (added snapshots) |
| Config placement | Model-specific in `{{ config() }}` block, directory-wide in `dbt_project.yml` | Info |
| Model description (changed models) | The `config()` block has a `description` that opens `Grain: One row per ...` | Important |

**dbt_project.yml (existing projects).** Compare the project's `dbt_project.yml` and `packages.yml` with the template for new projects (layer configs under the real project name, `+persist_docs` for relation and columns, staging and integration `+materialized: view` with `+schema: staging` / `integration`, warehouse `+materialized: table` with `+meta: {required_docs: true, required_tests: {"unique": 1, "not_null": 1}}`, seeds `+schema: seeds`, snapshots `+schema: snapshots`, `dbt_meta_testing` beside `dbt_utils`). Report each difference under **Suggestions** in the report. A difference is never a finding and never changes status. Do not apply any of them. Note that correcting the project key in an existing project can change which models build as tables or views.

**Violations to Flag:**
- Warehouse models not materialized as `table` or `incremental`
- Unnecessary table materializations in staging/integration
- Config that should be in `dbt_project.yml` but is in model
- Changed models with no `Grain:` line in the `config()` description

### Step 3.7: Validate Testing Coverage

#### Minimum Testing Requirements

**Every Model Must Have:**
- Entry in a schema file
- Primary key with `unique` and `not_null` tests. In staging and integration models that follow the reference, the key is the natural key (`_natural_key`), since `_pk` is created in the warehouse layer. An older model with a `_pk` in staging passes

**By Layer:**

| Layer | Required Tests | Severity |
|-------|---------------|----------|
| Staging | `unique` + `not_null` on the key, `not_null` on critical fields | Critical |
| Integration | `unique` + `not_null` on the key, `dbt_utils.unique_combination_of_columns` for multi-source | Critical |
| Warehouse | `unique` + `not_null` on pk, `relationships` on all fk fields | Critical |

**`dbt_utils.at_least_one`.** Accepted on any column as an addition. It never replaces `not_null` on a primary key: a PK with `at_least_one` and no `not_null` is a Critical finding (missing PK test). On other columns, the project decides between `not_null` and `at_least_one`. Neither is a finding.

**Test key.** `data_tests:` and `tests:` both pass. One resource that uses both keys is an Important finding (dbt rejects it). In a schema file that already uses `tests:`, new entries using `tests:` pass.

**Sources** (changed `_sources.yml` or `_<source>__sources.yml` files): `freshness`, with `loaded_at_field` set, is the only test expected. Other tests on source columns are a Nice-to-have finding. `warn_after` and `error_after` values are the client's choice and are not checked.

**Additional Tests to Check:**
- `relationships` tests for foreign keys
- `accepted_values` for enum/status fields
- `not_null_where` for conditional requirements
- Custom data tests in `tests/` directory for KPI validation
- `dbt run-operation required_tests` result, where Step 2.6 ran it

**Schema File Location:**
- Every model subdirectory holds a schema file: `_schema.yml` (new form) or the existing name (`stg_<source>.yml`, `integration.yml`, `wh_<group>.yml`, `intermediate.yml`). Both pass
- Projects that use droughty hold model schema in `models/droughty_schema.yml`. That passes

**Violations to Flag:**
- Missing schema file for a subdirectory (and no `droughty_schema.yml`)
- Models without any test coverage
- Primary keys without `unique`/`not_null` tests
- Missing `relationships` tests on foreign keys
- Integration models without `unique_combination_of_columns`
- A resource that uses both `data_tests:` and `tests:`

### Step 3.8: Validate Documentation Coverage

| Layer | Required Coverage | Applies to | Severity |
|-------|------------------|------------|----------|
| Staging | 100%: all models and columns documented | All models | Critical |
| Warehouse | 100%: all models and columns documented | All models | Critical |
| Integration | As needed: document complex logic and special cases | Unchanged models | Important |
| Base, intermediate, integration | 100%: every column documented | Changed models | Important |
| All layers | `config()` description opens `Grain: One row per ...` | Changed models | Important |

Projects that use droughty meet column coverage through the doc blocks droughty writes into `droughty_schema.yml`. They have no model description in a schema file, so the model-description checks for staging and warehouse read the `config()` description instead.

**Checks:**
- Every staging model has a `description` in its schema file
- Every warehouse model has a `description` in its schema file
- Every column in staging/warehouse has a `description`
- Changed models: every column in every layer has a `description`
- Descriptions use business terminology (not just field names)
- Complex/calculated fields have explanatory descriptions
- `dbt run-operation required_docs` result, where Step 2.6 ran it

**Doc blocks** (changed models): column descriptions are held once as doc blocks in `models/field_descriptions.md`, and schema files reference them with `'{{ doc("<name>") }}'`. A column that keeps its name across layers uses one doc block. Inline text on a changed model is a Nice-to-have finding. Existing doc blocks in other files (for example `models/docs/`) pass.

**Source declarations** (changed `_sources.yml` or `_<source>__sources.yml` files):

| Check | Severity |
|-------|----------|
| One source per `stg_<source>/` directory, named for the directory without `stg_` | Nice-to-have |
| `schema` and `loader` set | Important |
| Each table description opens `Grain: ...` (then `Source table group:` where relevant) and ends with a `Use it for ...` sentence | Important (Grain line), Nice-to-have (rest) |
| Every column of a declared table declared under its source name, including loader columns such as `_fivetran_synced` | Important |
| Column descriptions written inline, not as doc blocks | Nice-to-have |
| Columns holding personal data carry "Personal data." in the description | Important |
| Profiled figures carry the date measured ("Null on 30% of rows as at 2026-09") | Nice-to-have |

**Macros** (added or changed macro files): each macro has an entry in `macros/_schema_macros.yml` with `name`, `description` and `arguments` (each with `name`, `type`, `description`). A missing or out-of-date entry is Important.

**Violations to Flag:**
- Staging/warehouse models without descriptions
- Missing column documentation in staging/warehouse
- Changed models with undocumented columns in any layer, or no `Grain:` line
- Changed source files missing `loader`, a `Grain:` line, a column, or a personal-data marker
- Added or changed macros with no `_schema_macros.yml` entry
- Vague or unhelpful descriptions (e.g., description matches field name)

### Step 3.9: Run sqlfluff Validation (If Available)

**Process:**
1. Check for sqlfluff: `which sqlfluff`
2. Check for `.sqlfluff` config in project root

**If sqlfluff available:**
```bash
sqlfluff lint models/ --dialect <bigquery|snowflake|postgres>
```

Include sqlfluff violations in validation output. sqlfluff enforces many style conventions automatically:
- Line length limits
- Indentation consistency
- Capitalization rules
- Trailing commas
- Whitespace rules

**If not available:**
- Note in output: "sqlfluff not detected — recommend installing for automated linting"
- Provide manual validation of style conventions (Steps 3.5 and above)

### Step 4: Verify Model Dependencies

**Check for**:
- All `{{ ref() }}` references point to existing models
- No circular dependencies
- Proper layer order (staging → integration → warehouse)

**Use**:
```bash
dbt compile --select [models]
```

If compile fails, there are dependency issues.

### Step 5: Generate Validation Report

**Output Format:**

```markdown
## dbt Model Validation Report

**Project:** [PROJECT_NAME]
**Status:** PASS | FAIL
**Convention Source:** [.wire/conventions/dbt.yml / plugin conventions/dbt.yml] [form_choices: yes/no] [prose document read: path / none]
**Models Location:** dbt/models/

### Scope
- **Base ref:** [branch] at [commit] / changed set unknown (reference rules reported as warnings)
- **Models in scope for reference rules:** [n added, m modified]
  - Added: `[model]`, ...
  - Modified: `[model]`, ...
- **Unchanged models:** [count] (carried rules only)

### Summary
- ✓ X checks passed
- ⚠️ Y issues found (N critical, M important, P nice-to-have)

### Convention Lint
[✓/⚠️/Not run] **lint_conventions.py:** [errors] errors, [warnings] warnings, by rule id

### Test Results

✅/❌ **[passed]/[total] tests passed**

**By Layer:**
- Staging: [x]/[y] passed
- Integration: [x]/[y] passed
- Warehouse: [x]/[y] passed

**Failed Tests** (if any):
1. `test_name` - [failure details]
   - **Model:** `model_name`
   - **Fix:** [suggested fix]

### Naming Conventions
[✓/⚠️] **File naming:** [details]
[✓/⚠️] **Field naming:** [details]
[✓/⚠️] **Field ordering:** [details]

### SQL Structure
[✓/⚠️] **CTE structure:** [details]
[✓/⚠️] **Style compliance:** [details]
[✓/⚠️] **Layer boundaries:** [details]

### Configuration
[✓/⚠️] **Materialization:** [details]
[✓/⚠️] **Performance settings:** [details]

### Testing Coverage
[✓/⚠️] **Schema.yml exists:** [details]
[✓/⚠️] **Primary key tests:** [details]
[✓/⚠️] **Foreign key tests:** [details]
[✓/⚠️] **Additional tests:** [details]
[✓/⚠️/N/A] **required_tests (dbt_meta_testing):** [result / not installed]

### Documentation Coverage
[✓/⚠️] **Staging models documented:** [x]/[y]
[✓/⚠️] **Warehouse models documented:** [x]/[y]
[✓/⚠️] **Column descriptions:** [x]/[y]
[✓/⚠️] **Changed models with a Grain line:** [x]/[y]
[✓/⚠️/N/A] **Source declarations (changed files):** [details]
[✓/⚠️/N/A] **Macro entries in _schema_macros.yml:** [details]
[✓/⚠️/N/A] **required_docs (dbt_meta_testing):** [result / not installed / skipped: droughty]

### sqlfluff
[✓/⚠️/N/A] **Linter results:** [details]

### Dependency Check
[✓/⚠️] **All refs resolve:** [details]
[✓/⚠️] **Layer ordering:** [details]

---

## Recommendations

### Critical Issues (must fix)
1. [issue description]
   - **Location:** [file:line or section]
   - **Current:** `[current code]`
   - **Should be:** `[correct pattern]`
   - **Reason:** [why this matters]

### Important Issues (should fix)
[same format]

### Nice-to-have Improvements
[same format]

### Suggestions (dbt_project.yml and packages.yml)
Differences from the new-project template. Not findings. Not applied.
1. [difference]: [effect if adopted]

---

### Next Steps

1. **Fix issues** (if FAIL): Address critical and important issues, then re-validate
2. **Review dbt models with team**: `/wire:dbt-review [folder]`
3. **Generate semantic layer**: `/wire:semantic_layer-generate [folder]`
```

## Priority Levels

| Level | Criteria | Examples |
|-------|----------|---------|
| **Critical** | Breaks functionality, violates core principles, missing required tests | Missing pk tests, `ref()` outside CTEs, warehouse not materialized as table |
| **Important** | Inconsistent with conventions, maintainability issues, missing documentation | Wrong field naming, missing docs, implicit joins, no table aliases |
| **Nice-to-have** | Style preferences, minor optimizations, enhanced documentation | Line length, indentation, `union all` vs `union distinct` |

Status is FAIL when there is a failing dbt test, a Critical finding, or an Important reference-rule finding on a changed model. Important findings from carried rules are reported as before ("should fix"). Advisory items, warnings and suggestions never set FAIL. Reference rules are never Critical, and never apply to unchanged models when git history is available (see **Scope and Severity**).

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.dbt section:
   ```yaml
   dbt:
     generate: complete
     validate: pass | fail
     review: not_started
     tests_passed: 32
     tests_failed: 0
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `dbt`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### dbt Not Run Yet

If models haven't been run:
```
Warning: dbt models haven't been run yet.

Tests require models to be materialized first.

Run dbt models: /wire:utils-run-dbt [folder]
```

### dbt Command Not Found

If dbt not installed (local mode):
```
Error: dbt command not found.

Please either:
1. Install dbt: pip install dbt-bigquery
2. Use dbt Cloud instead
3. Show manual test commands
```

### Some Tests Failing

If tests fail:
- Set validate status to `fail`
- Show which tests failed with severity classification
- Suggest fixes based on test type
- User must fix data/models and re-run

### No Convention Source Found

```
Note: No .wire/conventions/dbt.yml found in this project.
Using the plugin's conventions/dbt.yml.

To override conventions for this project, create .wire/conventions/dbt.yml.
To keep an older form (for example singular model names or tests:),
record the ruling in the release's decisions.md and set it under
form_choices: in that file.
```

If the plugin's `conventions/dbt.yml` is also missing, skip Step 2.5, note "convention lint not run" in the report, and do the Step 3 checks by reading the code against this spec.

### No Git History

If Step 1.6 cannot work out the changed set, reference rules run on every model and report as warnings. Say so at the top of the report's Scope section.

## Common Violations Reference

❌ **Don't:**
- Rename or move an existing model, column, seed, snapshot or schema to match the new forms
- Put `ref()` calls outside top CTEs
- Use implicit joins or just `join` (use `inner join`, `left join`)
- Use table alias initialisms (`c` → use `customer`)
- Mix tabs and spaces (use 4 spaces)
- Skip tests on primary keys
- Leave staging/warehouse models undocumented
- Select from sources in non-staging models
- Use `union distinct` without good reason
- Look up PKs in separate queries (generate with `dbt_utils.generate_surrogate_key()`)
- Replace `not_null` on a primary key with `dbt_utils.at_least_one`
- Use both `data_tests:` and `tests:` on one resource
- Let integration or warehouse models read a base model

✅ **Do:**
- Accept either plural or singular names in staging and integration models
- Open every changed model's `config()` description with `Grain: One row per ...`
- All refs in top CTEs (prefixed with `s_`)
- Explicit join types
- Descriptive table aliases
- Consistent indentation (4 spaces)
- Test all primary keys (`unique` + `not_null`)
- Document staging and warehouse 100%
- Respect layer boundaries
- Prefer `union all`
- Generate PKs/FKs with `dbt_utils.generate_surrogate_key()`
- Use `dbt.type_*()` macros for all type casting

## Output

This command:
- Works out the changed set and states which models were in scope
- Runs dbt tests, and `required_tests` / `required_docs` where `dbt_meta_testing` is installed
- Runs the convention lint (`lint_conventions.py --domain dbt`)
- Validates naming conventions (file, field, ordering)
- Checks SQL structure and style
- Validates model configuration
- Checks testing coverage
- Checks documentation coverage
- Runs sqlfluff (if available)
- Checks dependencies
- Produces severity-rated validation report
- Updates `status.md` with validation results
- Provides actionable feedback if issues found

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
