---
description: Generate dbt models
argument-hint: <project-folder>
---

# Generate dbt models

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
    'command': 'dbt-generate',
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
preconditions: dynamic
auto_validate: false          # validate runs dbt test (or the dbt Cloud API equivalent) against the real warehouse
delegates_to:
  - utils/precondition_gate
description: Generate dbt models following layered architecture (staging → integration → warehouse)
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Generate Command

## Purpose

Generate dbt models based on the data model design, following best practices for layered architecture. Creates staging, integration, and warehouse models with appropriate tests, documentation, and naming conventions.

> **Per-layer alternative**: For very large dbt projects where you want to review/commit each layer independently rather than generating all three in one pass, use the per-layer commands instead: `/wire:dbt-staging-generate` → `/wire:dbt-staging-validate` → `/wire:dbt-integration-generate` → `/wire:dbt-integration-validate` → `/wire:dbt-warehouse-generate` → `/wire:dbt-warehouse-validate`, run in that order.

The conventions in this spec follow the Rittman Analytics dbt development reference. The reference version is recorded in the `reference:` block of the plugin's `conventions/dbt.yml`.

## Existing projects

These rules apply before every other rule in this spec.

- Never rename or move an existing model, column, seed, snapshot or schema. The conventions below apply to new and changed code only.
- Where the project keeps an old form (for example singular staging names, unprefixed columns, `tests:`, or `_<source>__sources.yml`), follow the ruling recorded in the release's `decisions.md` and the `form_choices:` block in the project's `.wire/conventions/dbt.yml`. Generate new models in that form. Keys: `model_name_number: plural|singular`, `column_prefix: entity|none`, `test_key: data_tests|tests`, `source_file_name: _sources|_<source>__sources`.
- Where no ruling exists, generate new models in the new form. Mixed naming inside one project is allowed.
- Do not change `dbt_project.yml` or `packages.yml` in an existing project. Compare them with the new-project templates (Step 8) and report the differences as suggestions only.
- Keep the date-cast macro the project already uses (`type_date()` or similar). `ra_type_date()` is for new projects.

**New or existing project.** A project is new when this command creates its `dbt_project.yml`. A project is existing when `dbt_project.yml` was already present before the run. Record which one applies in the summary document (Step 9).

## Prerequisites

**Default** (all project types except `dashboard_first`):

**Required Artifacts (must be complete)**:
- `requirements`: Requirements specification
- `data_model`: dbt model design specification

**Optional**:
- `pipeline_design`: Understanding of data sources
- Existing dbt project structure

**Dashboard-first** (`dashboard_first` project type):

**Required Artifacts (must be complete)**:
- `requirements`: Requirements specification
- `data_model`: dbt model design specification
- `seed_data`: `review: approved` — provides CSV seed files for initial data

**Seed-based generation notes**:
When `project_type` is `dashboard_first`, the dbt project should:
1. Use `ref('seed_name')` in staging models instead of `source('source_name', 'table_name')`
2. Include seed configuration in `dbt_project.yml` (seed paths, schema overrides)
3. Read seed files from `.wire/<project_id>/dev/seed_data/` and include them in the dbt project's `seeds/` directory
4. Generate source definitions that map to seed tables rather than external databases
5. Keep the staging model SQL compatible with later refactoring to real sources (use the `data_refactor` command when real data becomes available)
6. Seed naming: in a new project or a new release, seed files are named `seeds/seed__<description>.csv` and written to the `seeds` schema. Seed columns keep the CSV's names. In a release already under way, dashboard-first mock seeds keep their current names, so `data_refactor` still finds them.
7. Only staging models read seeds.

## Inputs

**From data_model artifact**:
- Source system schemas
- Target dimensional model design
- Transformation logic specifications
- Naming conventions
- Data quality requirements

## Workflow

### Step 1: Read Data Model Design

**Process**:
1. Read `.wire/<project_id>/design/data_model_specification.md`
2. Extract:
   - Source systems and tables
   - Staging layer specifications
   - Integration layer transformations
   - Warehouse layer dimensions and facts
   - Naming conventions
   - Required tests

### Step 1.5: Load Convention Source

**Priority Order:**

1. **Rulings** (highest priority)
   - Rulings in the release's `decisions.md` that keep an old form
   - The `form_choices:` block in the project's `.wire/conventions/dbt.yml`

2. **Project-specific conventions**
   - Check for `.wire/conventions/dbt.yml` (the project's override of the plugin's `conventions/dbt.yml`)
   - Check for `.dbt-conventions.md` in project root
   - Check for `dbt_coding_conventions.md` in project root
   - Check for `docs/dbt_conventions.md` in project

3. **Embedded conventions** (fallback: use the conventions defined in this spec)

**Detection:**
- Use Glob to search for convention files in project root
- If found, read and use project conventions
- If not found, use the embedded conventions below
- Note which source is being used in generated output
- Note any `form_choices:` keys that apply, and the `decisions.md` entry behind each

**Convention file for the lint step (Step 8.6):** the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`.

### Step 2: Determine dbt Project Location

**Process**:
1. Check if dbt project exists in repository
2. Common locations:
   - `dbt/` or `dbt_project/` at root
   - `transform/` at root
   - Within client folder

**Ask user if location is ambiguous:**
```
Where should I create the dbt models?

Options:
1. Existing dbt project at: [detected path]
2. Create new dbt project
3. Specify custom path
```

For this guide, assume dbt project root is at: `dbt/`

### Step 3: Generate Staging Models

**Purpose**: Clean and standardize raw source data

#### Field Naming Conventions

All new models MUST follow these naming conventions, unless a ruling under `form_choices:` keeps an old form (see Existing projects).

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `<entity>_pk`, generated via `dbt_utils.generate_surrogate_key(...)`, warehouse layer only | `user_pk`, `transaction_pk` |
| Foreign Key | `<referenced_entity>_fk`, generated via `dbt_utils.generate_surrogate_key(...)`, warehouse layer only. Keeps the referenced entity's prefix | `user_fk`, `account_fk` |
| Natural Key | `<entity>_natural_key`. On another entity it takes that model's prefix | `user_natural_key`, `order_user_natural_key` |
| Attribute | `<entity>_<attribute>`, no suffix | `user_name`, `customer_name` (not `name`) |
| Count | `<entity>_<thing>_count` | `order_line_count` |
| Index or rank | `<entity>_<thing>_rank` | `customer_revenue_rank` |
| Money (base currency) | `<entity>_<measure>_amount`, decimal currency, converted from cents at the staging layer | `user_account_balance_amount` (not `price_in_cents`) |
| Money (other currency) | `<entity>_<measure>_amount_<currency>`, ISO 4217 code lowercased | `order_revenue_amount_usd` |
| Measured quantity | `<entity>_<measure>_<unit>`. SI symbol lowercased where one exists, else the unit spelled out | `package_weight_kg`, `call_duration_seconds` |
| Percentage | `<entity>_<measure>_pct`, 0 to 100 | `order_discount_pct` |
| Ratio | `<entity>_<measure>_ratio`, 0 to 1 | `campaign_conversion_ratio` |
| Boolean | `<entity>_is_<state>`, `<entity>_has_<thing>`, `<entity>_was_<event>` | `user_is_active`, `user_has_subscription`, `order_was_refunded` |
| Date | `<entity>_<event>_dt` | `user_created_dt` |
| Timestamp (UTC) | `<entity>_<event>_ts`, always UTC | `user_created_ts`, `order_placed_ts` |
| Timestamp (non-UTC) | `<entity>_<event>_<tz>_ts`, time zone tag before `_ts` | `user_created_cet_ts` |
| Aggregated column | aggregate function first, then the source column name | `sum_invoice_line_item_amount`, `max_by_activity_user_name` |

**Column prefixes:**
- Every output column carries the prefix of the entity the model holds. A users model prefixes its columns `user_`.
- A column arriving from an upstream model that holds a different entity takes this model's prefix on the way out. A column arriving from a model that holds the same entity keeps its name.
- Where two columns describe the same thing, the relationship follows the prefix: `order_shipping_country_name`, `order_billing_country_name`.
- Foreign keys keep the prefix of the entity they point at: `user_pk` becomes `user_fk`.
- Columns take their output names in the CTE before `final`.

**Model names:**
- Staging and integration model names use the plural entity name: `stg_source_a__users`, `int_core__users`.
- Warehouse model names use the singular entity name: `wh_core__user_dim`, `wh_core__order_fact`.
- A project with a `form_choices: model_name_number: singular` ruling keeps singular staging and integration names for new models.

**General Rules:**
- All names in `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models (same field names for same concepts)
- Attributes carry no suffix. Currency is the only measure whose unit may be implicit.
- Seed columns keep the CSV's names. Snapshot meta columns (`dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`, `dbt_updated_at`) keep their dbt names.

**Key Generation:**
- Primary and foreign keys are created in the warehouse layer only, never in staging or integration.
- Primary keys: `{{ dbt_utils.generate_surrogate_key(['<entity>_natural_key']) }}`
- Foreign keys: `{{ dbt_utils.generate_surrogate_key(['<referenced_entity>_natural_key']) }}`, built from the same inputs as the referenced primary key
- Natural keys: extracted in staging as `<entity>_natural_key`. Where no single column identifies a row, the natural key is a compound of the columns that together identify it.

**Lowercasing:**
- Lowercase attribute strings only: `lower(...)` on names, categories, statuses and similar values.
- Never lowercase natural keys or source identifiers. Some are case-sensitive (for example Salesforce 15-character IDs), and lowercasing them can merge different records.

**Type Casting:**
- Always use cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_int() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`.
- Dates: new projects use `{{ ra_type_date() }}`, defined in `macros/utility/macro__type_date.sql` (Step 7). An existing project keeps the date macro it already uses (for example `{{ type_date() }}`).
- This keeps models portable across warehouses (BigQuery / Snowflake / Databricks / Postgres)
- Timestamps are cast to UTC in staging. A timestamp held in another zone carries that zone in its name.

#### Field Ordering Rules

Columns appear in eight groups, in this order. Each group present in a model opens with a Jinja comment:

| Order | Group | Jinja comment |
|-------|-------|---------------|
| 1 | Primary key | `{# primary key #}` |
| 2 | Foreign keys | `{# foreign keys #}` |
| 3 | Natural keys | `{# natural keys #}` |
| 4 | Attributes | `{# attributes #}` |
| 5 | Indexes and ranks | `{# indexes and ranks #}` |
| 6 | Metrics (`_count`, `_amount`, measured quantities, `_pct`, `_ratio`) | `{# metrics #}` |
| 7 | Booleans | `{# booleans #}` |
| 8 | Temporal (`_dt`, `_ts`) | `{# temporal #}` |

Omit the comment for a group the model does not have. Staging and integration models have no primary or foreign keys.

#### SQL Style Rules

All generated SQL MUST follow these style conventions:

| Rule | Requirement |
|------|-------------|
| Indentation | 4 spaces (not tabs). Predicates line up with `where` |
| Line length | Max 120 characters |
| Case | Lowercase field names and SQL functions |
| Aliases | Always use `as` keyword |
| Commas | Trailing |
| Joins | Explicit: `inner join`, `left join` (never just `join`) |
| Table aliases in joins | Use full descriptive names, not initialisms (`customer`, not `c`) |
| Column prefixes | Required when selecting from 2+ tables |
| CTEs from refs/sources | Prefix with `s_` (e.g., `s_salesforce_contacts`) |
| Transformation CTEs | Descriptive names (e.g., `filtered_events`, `aggregated_metrics`) |
| Final CTE | Always name `final` and end the model with `select * from final` |
| Union | Prefer `union all` to `union distinct` |
| Group by | Use column names, not numbers |
| Jinja | Spaces inside delimiters: `{{ this }}`, not `{{this}}`. Newlines between logical blocks |
| Model description | `config()` carries a `description` whose first line is `Grain: One row per ...` |
| Comments | Plain English. Full column names. The business's own terms. A comment on every CTE that removes rows, stating why |

**YAML style:** 2-space indentation, list items indented, lines up to 80 characters.

**Required SQL Structure:**
```sql
{{
    config(
        description = """
            Grain: One row per <entity>.
            <What the model holds.>
        """
    )
}}

with s_source_models as (

    select * from {{ ref('source_models') }}

),

s_other_models as (

    select * from {{ ref('other_models') }}

),

-- Comment explaining transformation logic
transformation_cte as (

    select

        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_name

    from s_source_models

),

final as (

    select

        {# natural keys #}
        transformation_cte.<entity>_natural_key,
        {# attributes #}
        transformation_cte.<entity>_name,
        s_other_models.<entity>_category_name

    from transformation_cte
    left join s_other_models
        on transformation_cte.<entity>_natural_key = s_other_models.<entity>_natural_key

)

select * from final
```

#### Key Principles

1. **Only staging models select from sources, snapshots and seeds** (via `{{ source() }}` and `{{ ref() }}`)
2. **All other models select from other models** (via `{{ ref() }}`). Later layers never read base models.
3. **All refs go in CTEs at the top**, never inline
4. **Always have a `final` CTE** and end with `select * from final`
5. **One CTE = one logical unit of work**
6. **Create an integration model only where one is needed** (a join across sources, a filter to the exposed concept, or derived fields). Otherwise the warehouse model reads staging.
7. **Aggregations should happen early**, before joins
8. **Newlines are cheap, brain time is expensive**: optimize for readability
9. **Repeated logic becomes a macro** (Step 7), not copied between models

#### Staging design rules

- Joins are avoided. A join or union is allowed only within one source system, and only where the concept cannot be staged without it. That work sits in a base model or a base CTE.
- Filtering is limited to correctness: deduplication, and rows known to be erroneous. A CTE that removes rows carries a comment stating why.
- The population and grain of the source entity are preserved.
- Natural keys are extracted. Primary and foreign keys are not created here.
- Timestamps are cast to UTC.
- A nested record is flattened into one column per field. A repeated field (array) is carried through unchanged unless it is queried or tested downstream.
- Derivations that read only columns of the same source row are allowed (unit conversion, `case when` classification, conforming values).
- Materialized as a view, set by folder in `dbt_project.yml`.

---

**For each source concept, create:**

**File**: `dbt/models/staging/stg_<source>/stg_<source>__<entities>.sql` (plural entity name)

**Template**:
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
        cast(<foreign_id_column> as {{ dbt.type_string() }}) as <entity>_<referenced_entity>_natural_key,
        {# attributes #}
        lower(trim(cast(<name_column> as {{ dbt.type_string() }}))) as <entity>_name,
        {# metrics #}
        cast(<count_column> as {{ dbt.type_int() }}) as <entity>_<thing>_count,
        cast(<cents_column> as {{ dbt.type_numeric() }}) / 100 as <entity>_<measure>_amount,
        {# booleans #}
        cast(<flag_column> as {{ dbt.type_boolean() }}) as <entity>_is_<state>,
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

Natural keys are cast but never lowercased. In an existing project, replace `ra_type_date()` with the date macro the project already uses.

#### Base models (where needed)

Where a source concept needs a join or union within one source system, put that shaping work in a base model.

**File**: `dbt/models/staging/stg_<source>/base_<source>__<entities>.sql`

- Selects directly from the source and applies the staging conventions above.
- Read only by the staging model of the same concept. Later layers never read it.
- Materialized as a view by the staging folder config. No `materialized` setting in the model.
- Use a base model where the shaping is repeated across models or independently testable. Otherwise a base CTE in the staging model is enough.

#### Snapshots (where needed)

Where the source overwrites history the project needs, create a snapshot of the source table.

**File**: `dbt/snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`

```sql
{% snapshot snapshot_<source>__<source_table> %}

{{
    config(
        unique_key = '<id_column>',
        strategy = 'timestamp',
        updated_at = '<modified_timestamp_column>'
    )
}}

select * from {{ source('<source>', '<table_name>') }}

{% endsnapshot %}
```

- The `{% snapshot %}` block name equals the file name without `.sql`.
- `timestamp` is the default strategy. Where the source has no reliable modified timestamp, use `strategy = 'check'` with `check_cols` naming the columns compared.
- The snapshot holds the source columns unchanged. dbt meta columns keep their names.
- New projects write snapshots to the `snapshots` schema (`dbt_project.yml`, Step 8). An existing project keeps its current snapshot schema.
- The staging model reads the snapshot as it reads a source.

**Also create**: `dbt/models/staging/stg_<source>/_sources.yml` (one per source folder; in a project with a `source_file_name: _<source>__sources` ruling, use `_<source>__sources.yml`)

```yaml
version: 2

sources:
  - name: <source>
    description: >
      <Source system>, loaded by <loading tool>. Data starts on
      <date>. <Units and the columns that join tables.>
    schema: <dataset the loading tool writes to>
    loader: <loading tool>
    tables:
      - name: <business_name>
        identifier: <raw_table_name>
        description: >
          Grain: One row per <thing>.
          Source table group: <group, where the source has groups>.
          <What the table holds and how the loading tool writes it.>
          Use it for <what the table is used for>.
        config:
          loaded_at_field: _fivetran_synced
          freshness:
            warn_after: {count: <n>, period: hour}
            error_after: {count: <n>, period: hour}
        columns:
          - name: id
            description: >
              Source system identifier for the <thing>. One row per id.
              The same value is held in <other_table>.<column>.
          - name: email
            description: >
              The <thing>'s email address. Personal data.
              Null on <n>% of rows as at <yyyy-mm>.
          - name: _fivetran_synced
            description: When the loading tool loaded the row. UTC.
```

`_sources.yml` content rules:
- One source per `stg_<source>/` folder, named for the folder without `stg_`.
- `schema` and `loader` are set.
- Declare a table only where a staging model, base model or snapshot reads it. `name` is the business name; `identifier` holds the raw name where it differs.
- The table description opens with `Grain:`, then `Source table group:` where relevant, then what it holds and how it is loaded, and ends with a `Use it for ...` sentence.
- Every column of a declared table is declared under its source name, unchanged, including loader columns such as `_fivetran_synced`.
- Column descriptions are written inline (no doc blocks). They state the meaning in the source, and where they apply: unit, time zone, what a null means, allowed values.
- An identifier column names the columns elsewhere that hold the same value.
- A column holding personal data carries "Personal data." in its description.
- A profiled figure carries the date it was measured.
- `freshness` (with `loaded_at_field`) is the only test in `_sources.yml`. `warn_after` and `error_after` are set per client project; ask the user if the data model does not state them.

**Also create**: `dbt/models/staging/stg_<source>/_schema.yml` for the staging and base models in the folder (not needed where the project uses droughty; see Step 6). Column descriptions reference doc blocks in `models/field_descriptions.md`. The test key (`data_tests:` or `tests:`) follows Step 6.

```yaml
version: 2

models:
  - name: stg_<source>__<entities>
    description: >
      Grain: One row per <entity> in <source table>.
      <What the model holds.>
    columns:
      - name: <entity>_natural_key
        description: '{{ doc("<entity>_natural_key") }}'
        data_tests:
          - unique
          - not_null
      - name: <entity>_name
        description: '{{ doc("<entity>_name") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
```

### Step 4: Generate Integration Models

**Purpose**: Business logic and complex transformations

An integration model exists only where one is needed: a join across sources, a filter to the concept the warehouse exposes, or derived fields. Where none is needed, the warehouse model reads staging directly.

- Integration models select from staging models and intermediate models, never from base models or sources.
- Joins across source systems happen here.
- New columns follow the staging conventions: entity prefix, lowercased attribute strings (never natural keys), cast macros.
- Materialized as a view, set by folder in `dbt_project.yml`.

**Types of integration models:**

#### Intermediate Models (`int_<group>__<entities>__<verb>.sql`)

Combine the same concept from more than one source before the integration model (the verb is past tense, e.g. `unioned`, `deduped`):

**File**: `dbt/models/integration/int_<group>/intermediate/int_<group>__<entities>__<verb>.sql`

**Example**: `int_core__students__unioned.sql`

New intermediate models are views, set by the `intermediate/` folder (the integration folder config in Step 8). They carry no `materialized` setting. An existing project that sets intermediate models to `ephemeral` keeps that setting.

```sql
{{
    config(
        description = """
            Grain: One row per student per source system.
            Students from the management information system and the admissions system, unioned.
        """,
        tags = ['integration', 'intermediate']
    )
}}

with s_mis_students as (

    select * from {{ ref('stg_mis__students') }}

),

s_admissions_students as (

    select * from {{ ref('stg_admissions__students') }}

),

unioned as (

    select

        {# natural keys #}
        student_natural_key,
        {# attributes #}
        student_forename,
        student_surname,
        'mis' as student_source_system_name,
        {# booleans #}
        student_is_sen

    from s_mis_students

    union all

    select

        {# natural keys #}
        student_natural_key,
        {# attributes #}
        student_forename,
        student_surname,
        'admissions' as student_source_system_name,
        {# booleans #}
        student_is_sen

    from s_admissions_students

),

final as (

    select * from unioned

)

select * from final
```

#### Final Integration Models (`int_<group>__<entities>.sql`)

**File**: `dbt/models/integration/int_<group>/int_<group>__<entities>.sql`

```sql
{{
    config(
        description = """
            Grain: One row per student.
            Students from all sources, with demographics and the access plus flag.
        """,
        tags = ['integration']
    )
}}

with s_students as (

    select * from {{ ref('int_core__students__unioned') }}

),

s_demographics as (

    select * from {{ ref('stg_mis__student_demographics') }}

),

final as (

    select

        {# natural keys #}
        s_students.student_natural_key,
        {# attributes #}
        s_students.student_forename,
        s_students.student_surname,
        s_demographics.student_demographic_ethnic_group_name as student_ethnic_group_name,
        {# booleans #}
        s_students.student_is_sen,
        s_students.student_is_free_meals,
        s_demographics.student_demographic_is_ethnically_diverse as student_is_ethnically_diverse,
        -- A student counts as access plus where they have special educational needs or free meals.
        case
            when s_students.student_is_sen or s_students.student_is_free_meals then true
            else false
        end as student_is_access_plus

    from s_students
    left join s_demographics
        on s_students.student_natural_key = s_demographics.student_demographic_student_natural_key

)

select * from final
```

### Step 5: Generate Warehouse Models

**Purpose**: Dimensional model ready for BI consumption

- Dimension and fact models select from integration models, or from staging where no integration model is needed.
- Primary and foreign keys are created here, and only here, via `dbt_utils.generate_surrogate_key`.
- An entity's attributes live on that entity's dimension. Other models reference it by foreign key.
- Warehouse model names are singular: `wh_<group>__<entity>_dim`, `_fact`, `_xa`.
- Materialized as a table, set by folder in `dbt_project.yml`. A model may be `incremental` where the client decides; the client sets the strategy, unique key and lookback.

#### Dimension Tables (`wh_<group>__<entity>_dim.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_dim.sql`

**For SCD Type 1 (current state only)**:
```sql
{{
    config(
        description = """
            Grain: One row per <entity>.
            <What the dimension holds.>
        """,
        tags = ['warehouse', 'dimension'],
        cluster_by = ['<entity>_pk']
    )
}}

with s_<entities> as (

    select * from {{ ref('int_<group>__<entities>') }}

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<entity>_natural_key']) }} as <entity>_pk,
        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_<attribute_1>,
        <entity>_<attribute_2>,
        {# booleans #}
        <entity>_is_<state>,
        {# temporal #}
        <entity>_created_ts

    from s_<entities>

),

final as (

    select * from add_primary_key

)

select * from final
```

**For SCD Type 2 (historical tracking)**: prefer a snapshot of the source (Step 3, Snapshots), read by staging. The dimension then carries one row per version:

```sql
{{
    config(
        description = """
            Grain: One row per <entity> per version.
            <What the dimension holds.> Built from snapshot_<source>__<source_table>.
        """,
        tags = ['warehouse', 'dimension', 'scd2']
    )
}}

with s_<entity>_versions as (

    select * from {{ ref('stg_<source>__<entity>_versions') }}

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<entity>_natural_key', '<entity>_valid_from_ts']) }} as <entity>_pk,
        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_<attribute_1>,
        {# booleans #}
        <entity>_valid_to_ts is null as <entity>_is_current,
        {# temporal #}
        <entity>_valid_from_ts,
        <entity>_valid_to_ts

    from s_<entity>_versions

),

final as (

    select * from add_primary_key

)

select * from final
```

#### Fact Tables (`wh_<group>__<entity>_fact.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_fact.sql`

```sql
{{
    config(
        description = """
            Grain: One row per <event>.
            <What the fact holds.>
        """,
        tags = ['warehouse', 'fact'],
        cluster_by = ['<event>_<event>_dt', '<dimension>_fk']
    )
}}

with s_<events> as (

    select * from {{ ref('int_<group>__<events>') }}

),

add_keys as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<event>_natural_key']) }} as <event>_pk,
        {# foreign keys #}
        {{ dbt_utils.generate_surrogate_key(['<event>_<dimension>_natural_key']) }} as <dimension>_fk,
        {# natural keys #}
        <event>_natural_key,
        <event>_<dimension>_natural_key,
        {# metrics #}
        <event>_<measure>_amount,
        <event>_<thing>_count,
        {# booleans #}
        <event>_is_<state>,
        {# temporal #}
        <event>_<event>_dt

    from s_<events>

),

final as (

    select * from add_keys

)

select * from final
```

The foreign key is built from the same inputs as the dimension's primary key, so no join to the dimension is needed.

#### Extended Aggregate Tables (`wh_<group>__<entity>_xa.sql`)

**File**: `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_xa.sql`

An extended aggregate is a denormalised table built from fact and dimension models. It either aggregates to a summary grain (such as a daily summary) or combines several facts at a shared grain (such as an event stream). It exists only in the warehouse layer. New aggregate models use `_xa`. Existing `_agg` models keep their names.

```sql
{{
    config(
        description = """
            Grain: One row per <dimension> per day.
            Daily summary of <events>.
        """,
        tags = ['warehouse', 'extended_aggregate']
    )
}}

with s_<event>_facts as (

    select * from {{ ref('wh_<group>__<event>_fact') }}

),

aggregated as (

    select

        <dimension>_fk,
        <event>_<event>_dt,
        count(*) as count_<event>_pk,
        sum(<event>_<measure>_amount) as sum_<event>_<measure>_amount

    from s_<event>_facts

    group by <dimension>_fk, <event>_<event>_dt

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<dimension>_fk', '<event>_<event>_dt']) }} as <entity>_pk,
        {# foreign keys #}
        <dimension>_fk,
        {# metrics #}
        count_<event>_pk,
        sum_<event>_<measure>_amount,
        {# temporal #}
        <event>_<event>_dt

    from aggregated

),

final as (

    select * from add_primary_key

)

select * from final
```

Aggregated columns lead with the function name (`sum_`, `count_`, `max_by_`), so the name traces back to the source column.

### Step 5.5: Multi-Source Framework (If Applicable)

When integrating data from **multiple source systems** where the same entities (companies, contacts, products) exist across sources with different IDs and attributes, use this framework pattern.

**When to use:** The data model design identifies multiple sources for the same entity (e.g., companies from HubSpot + Xero + Harvest).

In an existing multi-source project, keep its current model names, folder (`models/sources/` or `models/staging/`), macro name (`merge_sources`) and source file names. Add new sources in the same form. The examples below show the new-project form.

#### Architecture Overview

```
Staging Layer (stg_*) → Integration Layer (int_<group>__*) → Warehouse Layer (wh_<group>__*_dim/*_fact)
```

| Layer | Purpose | Naming | Materialization |
|-------|---------|--------|-----------------|
| **Staging** | Source-specific transformations, column standardization, ID prefixing | `stg_<source>__<objects>.sql` | view |
| **Integration** | Cross-source entity resolution, deduplication, merging | `int_<group>__<objects>.sql` | view |
| **Warehouse** | Final dimensional models with surrogate keys | `wh_<group>__<object>_dim.sql`, `wh_<group>__<object>_fact.sql` | table |

#### Configuration-Driven Source Management

Add source enablement variables to `dbt_project.yml`:

```yaml
# dbt_project.yml
vars:
  # Source enablement arrays - add/remove sources as needed
  crm_warehouse_company_sources: ['hubspot_crm', 'xero_accounting', 'harvest_projects']
  crm_warehouse_contact_sources: ['hubspot_crm', 'mailchimp_email', 'harvest_projects']
  finance_warehouse_invoice_sources: ['xero_accounting', 'harvest_projects']

  # Per-source configuration
  stg_hubspot_crm_id-prefix: 'hubspot-'
  stg_hubspot_crm_etl: 'fivetran'
  stg_hubspot_crm_schema: 'fivetran_hubspot'

  stg_xero_accounting_id-prefix: 'xero-'
  stg_xero_accounting_etl: 'fivetran'
  stg_xero_accounting_schema: 'fivetran_xero'

  # Feature flags
  enable_companies_merge_file: true
```

#### Step 1: Staging Layer: Conditional Compilation with ID Prefixing

Each staging model checks if enabled before compiling and prefixes its natural keys. The prefix keeps keys from different sources apart. The source ID itself is not lowercased.

```sql
-- models/staging/stg_hubspot_crm/stg_hubspot_crm__companies.sql

{% if var("crm_warehouse_company_sources") %}
{% if 'hubspot_crm' in var("crm_warehouse_company_sources") %}

{{
    config(
        description = """
            Grain: One row per HubSpot company.
            Companies from HubSpot, with natural keys prefixed by source.
        """
    )
}}

{% if var("stg_hubspot_crm_etl") == 'fivetran' %}
with s_companies as (

    select * from {{ source('hubspot_crm', 'companies') }}

),

-- Removes companies HubSpot has deleted. Fivetran keeps them with a deleted flag.
filtered as (

    select * from s_companies
    where not _fivetran_deleted

),
{% elif var("stg_hubspot_crm_etl") == 'stitch' %}
with s_companies as (

    select * from {{ source('hubspot_crm', 'companies') }}

),

-- Keeps the latest copy of each company. Stitch writes a row on every batch.
filtered as (

    select * from s_companies
    qualify row_number() over (partition by companyid order by _sdc_batched_at desc) = 1

),
{% endif %}

rename_and_cast as (

    select

        {# natural keys #}
        concat(
            '{{ var("stg_hubspot_crm_id-prefix") }}',
            cast(companyid as {{ dbt.type_string() }})
        ) as company_natural_key,
        {# attributes #}
        -- The company name with legal suffixes removed, so names match across sources.
        trim(regexp_replace(
            regexp_replace(properties_name, r'(?i)\s*(Limited|Ltd\.?|Inc\.?|LLC|Corp\.?)$', ''),
            r'\s+', ' '
        )) as company_name,
        lower(trim(properties_website)) as company_website,
        lower(properties_industry) as company_industry_name,
        properties_phone as company_phone,
        'hubspot_crm' as company_source_system_name,
        {# temporal #}
        cast(properties_createdate as {{ dbt.type_timestamp() }}) as company_created_ts,
        cast(properties_hs_lastmodifieddate as {{ dbt.type_timestamp() }}) as company_last_modified_ts

    from filtered

),

final as (

    select * from rename_and_cast

)

select * from final

{% endif %}
{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 2: Create the merge sources Macro

**File**: `dbt/macros/macro__merge_sources.sql` (new projects). An existing project keeps `merge_sources` in its current file.

```sql
{% macro macro__merge_sources(sources, model_suffix) %}
(
    {% set relations_list = [] %}

    {% for source in sources %}
        {% do relations_list.append(ref("stg_" ~ source ~ model_suffix)) %}
    {% endfor %}

    {{ dbt_utils.union_relations(
        relations=relations_list,
        source_column_name='_dbt_source_relation'
    ) }}
)
{% endmacro %}
```

Describe it in `macros/_schema_macros.yml` (Step 7).

#### Step 3: Integration Layer: Entity Deduplication and Merging

```sql
-- models/integration/int_crm/int_crm__companies.sql

{% if var('crm_warehouse_company_sources') %}

{{
    config(
        description = """
            Grain: One row per company name.
            Companies from all enabled sources, merged by cleaned company name.
        """
    )
}}

with companies_unioned as (

    {{ macro__merge_sources(
        sources=var('crm_warehouse_company_sources'),
        model_suffix='__companies'
    ) }}

),

-- Collects every source natural key for each company name. Removes rows with no name.
company_natural_keys as (

    select

        company_name,
        array_agg(distinct company_natural_key ignore nulls) as company_source_natural_keys

    from companies_unioned
    where company_name is not null
      and trim(company_name) != ''

    group by company_name

),

-- One row per company name. Takes the highest value of each attribute across sources.
companies_grouped as (

    select

        company_name,
        max(company_website) as max_company_website,
        max(company_industry_name) as max_company_industry_name,
        max(company_phone) as max_company_phone,
        count(distinct company_source_system_name) as count_company_source_system_name,
        min(company_created_ts) as min_company_created_ts,
        max(company_last_modified_ts) as max_company_last_modified_ts

    from companies_unioned
    where company_name is not null

    group by company_name

),

final as (

    select

        {# attributes #}
        companies_grouped.company_name,
        companies_grouped.max_company_website as company_website,
        companies_grouped.max_company_industry_name as company_industry_name,
        companies_grouped.max_company_phone as company_phone,
        company_natural_keys.company_source_natural_keys,
        {# metrics #}
        companies_grouped.count_company_source_system_name as company_source_count,
        {# temporal #}
        companies_grouped.min_company_created_ts as company_created_ts,
        companies_grouped.max_company_last_modified_ts as company_last_modified_ts

    from companies_grouped
    inner join company_natural_keys
        on companies_grouped.company_name = company_natural_keys.company_name

)

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 4: Warehouse Layer: Dimension with Surrogate Key

```sql
-- models/warehouse/wh_crm/wh_crm__company_dim.sql

{% if var("crm_warehouse_company_sources") %}

{{
    config(
        description = """
            Grain: One row per company.
            Companies from all enabled sources, with every source natural key.
        """,
        unique_key = 'company_pk'
    )
}}

with s_companies as (

    select * from {{ ref('int_crm__companies') }}

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['company_name']) }} as company_pk,
        {# natural keys #}
        company_source_natural_keys,
        {# attributes #}
        company_name,
        company_website,
        company_industry_name,
        company_phone,
        {# metrics #}
        company_source_count,
        {# temporal #}
        company_created_ts,
        company_last_modified_ts

    from s_companies

),

final as (

    select * from add_primary_key

)

select * from final

{% else %} {{ config(enabled=false) }} {% endif %}
```

#### Step 5: Fact Table Joins Using Source Natural Key Arrays

```sql
-- Join fact tables to dimensions using the array of source natural keys:

with s_invoices as (

    select * from {{ ref('int_finance__invoices') }}

),

s_company_dim as (

    select * from {{ ref('wh_crm__company_dim') }}

),

final as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['s_invoices.invoice_natural_key']) }} as invoice_pk,
        {# foreign keys #}
        s_company_dim.company_pk as company_fk,
        {# natural keys #}
        s_invoices.invoice_natural_key,
        {# attributes #}
        s_invoices.invoice_status_name,
        {# metrics #}
        s_invoices.invoice_amount,
        {# temporal #}
        s_invoices.invoice_created_ts

    from s_invoices
    -- Matches the invoice's company to any source natural key held on the company dimension.
    left join s_company_dim
        on s_invoices.invoice_company_natural_key in unnest(s_company_dim.company_source_natural_keys)

)

select * from final
```

#### Multi-Source Directory Structure

```
models/
├── field_descriptions.md
├── staging/
│   ├── stg_hubspot_crm/
│   │   ├── _sources.yml
│   │   ├── _schema.yml
│   │   ├── stg_hubspot_crm__companies.sql
│   │   └── stg_hubspot_crm__contacts.sql
│   ├── stg_xero_accounting/
│   │   ├── _sources.yml
│   │   ├── _schema.yml
│   │   └── stg_xero_accounting__companies.sql
│   └── stg_harvest_projects/
│       ├── _sources.yml
│       ├── _schema.yml
│       └── stg_harvest_projects__companies.sql
├── integration/
│   └── int_crm/
│       ├── _schema.yml
│       ├── int_crm__companies.sql
│       └── int_crm__contacts.sql
└── warehouse/
    ├── wh_crm/
    │   ├── _schema.yml
    │   └── wh_crm__company_dim.sql
    └── wh_finance/
        ├── _schema.yml
        └── wh_finance__invoice_fact.sql

macros/
├── _schema_macros.yml
├── macro__merge_sources.sql
└── utility/
    └── macro__type_date.sql

seeds/
└── seed__companies_merge_list.csv  (optional manual merge)
```

#### Adding a New Source

1. Add source to enablement array in `dbt_project.yml`
2. Add ID prefix and ETL variables
3. Create the source's `_sources.yml`
4. Create staging model with conditional compilation
5. Test independently before enabling in integration

#### Removing a Source

1. Remove from source array in `dbt_project.yml`
2. Source models automatically disable via conditional compilation
3. Historical source natural keys remain in dimension arrays for audit

#### Multi-Source Framework Checklist

**Configuration:**
- [ ] Source arrays defined in `dbt_project.yml` for each entity type
- [ ] ID prefix variables defined for each source
- [ ] ETL type variables defined if supporting multiple pipelines

**Staging Layer:**
- [ ] Each staging model checks if enabled before compiling
- [ ] All natural keys prefixed with unique source identifier (and not lowercased)
- [ ] Column names standardized across all sources
- [ ] Entity names normalized (trim, remove Ltd/Inc suffixes)

**Integration Layer:**
- [ ] Merge sources macro used for dynamic unions
- [ ] Pre-merge CTE collects natural keys into arrays
- [ ] Attributes deduplicated using MAX/MIN logic
- [ ] Source count tracked for data quality

**Warehouse Layer:**
- [ ] Surrogate keys generated from business keys (not source IDs)
- [ ] Source natural key arrays preserved in dimension tables
- [ ] Fact tables join using `IN UNNEST()` pattern
- [ ] All conditional config blocks in place

---

### Step 6: Generate Model Documentation

#### Documentation Coverage Requirements

| Layer | Coverage | Details |
|-------|----------|---------|
| Staging (and base) | 100% | Every model and every column documented |
| Integration (and intermediate) | 100% | Every model and every column documented |
| Warehouse | 100% | Every model and every column documented |
| Sources | 100% | Every column of a declared table, written inline in `_sources.yml` (Step 3) |

**Rules:**
- Every model's `config()` carries a `description` whose first line is `Grain: One row per ...`. Further lines state what the model holds.
- Column descriptions are held once, as doc blocks in `models/field_descriptions.md`. Schema files reference them with `'{{ doc("<name>") }}'`. A column that keeps its name across layers uses one doc block.
- Source column descriptions are the exception: they are written inline in `_sources.yml`, with no doc blocks.
- Focus on business terminology. Explain why, not only what. Include business context for calculated fields.
- In an existing project, add doc blocks for new columns to the project's current doc block file if it has one (for example `models/docs/`). Do not move existing doc blocks.

**File**: `dbt/models/field_descriptions.md`

```markdown
{% docs <entity>_pk %}
The surrogate primary key of the <entity> entity.
{% enddocs %}

{% docs <entity>_natural_key %}
The <source system> identifier for the <entity>. Not lowercased.
{% enddocs %}
```

**Schema file location:**
- **Without droughty:** each subdirectory within a layer holds a `_schema.yml` covering the models in that directory (for example `models/staging/stg_<source>/_schema.yml`, `models/integration/int_<group>/_schema.yml`, `models/warehouse/wh_<group>/_schema.yml`). An existing project keeps its current schema file names (`stg_<source>.yml`, `integration.yml`, `wh_<group>.yml`, ...) and adds new entries to them.
- **With droughty:** droughty writes `models/droughty_schema.yml` from the warehouse and takes column descriptions from the doc blocks in `models/field_descriptions.md`. Do not hand-write model schema files. Write the doc blocks so droughty can use them.

#### Tests

| Column | Default tests |
|--------|---------------|
| Primary key (`_pk`), or the natural key that identifies a staging or integration row | `unique`, `not_null` |
| Foreign key (`_fk`) | `not_null`, `dbt_utils.at_least_one`, `relationships` to the referenced dimension |
| Other columns | `not_null`, `dbt_utils.at_least_one` |
| Columns with a known value set | add `accepted_values` |

- `dbt_utils.at_least_one` is added alongside `not_null`, never in place of it. It checks that a column is not entirely empty, which also catches an empty table.
- Drop `not_null` only where the data model or the source profile shows the column can be null. Keep `dbt_utils.at_least_one` on that column and note the reason in the summary.
- Sources carry `freshness` only (Step 3). No column tests in `_sources.yml`.

#### Test key (`data_tests:` or `tests:`)

1. If the project's `.wire/conventions/dbt.yml` sets `form_choices: test_key`, use that key.
2. If the schema file being written to already uses `tests:`, keep `tests:` in that file.
3. Otherwise detect the dbt version:
   - `dbt --version` in the project's environment
   - `require-dbt-version` in `dbt_project.yml`
   - the dbt or adapter version pinned in `requirements.txt`, `pyproject.toml` or similar (for example `dbt-bigquery>=1.8`)
   - the dbt Cloud environment's dbt version, if the project runs in dbt Cloud
4. dbt 1.8 or later: write `data_tests:`. Before 1.8: write `tests:`.
5. If the version cannot be found, write `tests:` (every version accepts it) and record this in the summary.

Never write both keys on one resource.

**File**: `dbt/models/warehouse/wh_<group>/_schema.yml`

```yaml
version: 2

models:
  - name: wh_<group>__<entity>_dim
    description: >
      Grain: One row per <entity>.
      <What the dimension holds.>
    columns:
      - name: <entity>_pk
        description: '{{ doc("<entity>_pk") }}'
        data_tests:
          - unique
          - not_null
      - name: <entity>_natural_key
        description: '{{ doc("<entity>_natural_key") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one

  - name: wh_<group>__<event>_fact
    description: >
      Grain: One row per <event>.
      <What the fact holds.>
    columns:
      - name: <event>_pk
        description: '{{ doc("<event>_pk") }}'
        data_tests:
          - unique
          - not_null
      - name: <dimension>_fk
        description: '{{ doc("<dimension>_fk") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
          - relationships:
              to: ref('wh_<group>__<dimension>_dim')
              field: <dimension>_pk
```

### Step 7: Generate Macros (if needed)

**File**: `dbt/macros/macro__<name>.sql` (utility macros in `dbt/macros/utility/`)

- One macro per file. The macro is named `macro__<name>`, matching the file name.
- Adapter-specific versions (`default__`, `bigquery__`, `snowflake__`) sit in the same file.
- dbt override macros such as `generate_schema_name` keep their dbt names.
- Every new macro has an entry in `macros/_schema_macros.yml` with `name`, `description` and `arguments` (each with `name`, `type`, `description`). A change to a macro's arguments or behaviour updates its entry.
- These file-naming rules apply to added macros only. An existing macro keeps its name and file.

**Example**: Calculate derived fields

```sql
{% macro macro__is_access_plus(is_sen, is_free_meals) %}
    case
        when {{ is_sen }} = true or {{ is_free_meals }} = true then true
        else false
    end
{% endmacro %}
```

**File**: `dbt/macros/_schema_macros.yml`

```yaml
version: 2

macros:
  - name: macro__is_access_plus
    description: >
      Returns true where a student has special educational needs or free
      meals, else false.
    arguments:
      - name: is_sen
        type: boolean
        description: Whether the student has special educational needs.
      - name: is_free_meals
        type: boolean
        description: Whether the student receives free meals.
```

**New projects only**: create `dbt/macros/utility/macro__type_date.sql`:

```sql
{% macro ra_type_date() %}
    {{ return(api.Column.translate_type("date")) }}
{% endmacro %}
```

and its entry in `macros/_schema_macros.yml`:

```yaml
  - name: ra_type_date
    description: >
      Returns the warehouse's date type, for use in casts to a date.
      Takes no arguments.
```

An existing project keeps the date macro it already uses and does not get this file.

### Step 8: Generate dbt_project.yml and packages.yml

#### New project

**File**: `dbt/dbt_project.yml`. Layer configs sit under the real project name.

```yaml
name: '<project_name>'
version: '1.0.0'
config-version: 2

profile: '<project_name>'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
snapshot-paths: ["snapshots"]
macro-paths: ["macros"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  +persist_docs:
    relation: true
    columns: true
  <project_name>:
    staging:
      +materialized: view
      +schema: staging
      +tags: ['staging']
    integration:
      +materialized: view
      +schema: integration
      +tags: ['integration']
    warehouse:
      +materialized: table
      +tags: ['warehouse']
      +meta:
        required_docs: true
        required_tests: {"unique": 1, "not_null": 1}

seeds:
  <project_name>:
    +schema: seeds

snapshots:
  <project_name>:
    +schema: snapshots

vars:
  # Add project-specific variables
```

A project that uses droughty sets `required_docs: false` (droughty does not write model descriptions and rewrites `droughty_schema.yml`). It meets the documentation rule through the doc blocks in `models/field_descriptions.md`. `required_tests` stays on.

**File**: `dbt/packages.yml`

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: ">=1.3.0"
  - package: tnightengale/dbt_meta_testing
    version: ">=0.4.0"
```

Also create `dbt/macros/utility/macro__type_date.sql` and `dbt/macros/_schema_macros.yml` (Step 7), and an empty `dbt/models/field_descriptions.md` if no doc blocks were written.

#### Existing project

Do not change `dbt_project.yml` or `packages.yml`. Compare them with the new-project templates above and list each difference in the summary as a suggestion, for example:

- layer configs sit under a key that is not the project's `name:`
- no `+persist_docs`
- no `+meta` with `required_docs` / `required_tests` on the warehouse layer
- no `seeds` or `snapshots` schema
- no `dbt_meta_testing` package

State why they are suggestions only: correcting the project key can change which models build as tables or views, and adding schemas can move where models are built. The project owner decides.

`dbt run-operation required_docs` and `dbt run-operation required_tests` run only where `packages.yml` includes `dbt_meta_testing`.

### Step 8.5: sqlfluff Configuration (If Applicable)

**Process:**
1. Check for existing `.sqlfluff` config file in the dbt project root
2. If not present, recommend creating one:

```ini
# .sqlfluff
[sqlfluff]
templater = dbt
dialect = bigquery
max_line_length = 120

[sqlfluff:indentation]
indent_unit = space
tab_space_size = 4

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = lower

[sqlfluff:rules:capitalisation.functions]
capitalisation_policy = lower
```

3. Note that sqlfluff enforces many style conventions automatically (line length, indentation, capitalization, trailing commas, whitespace)
4. If sqlfluff is available, recommend running: `sqlfluff lint models/ --dialect bigquery`
5. In an existing project with its own `.sqlfluff`, do not change it.

### Step 8.6: Convention Self-Check

Run the convention lint over the generated models before writing the summary.

Resolve the convention file: the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`.

New project:

```bash
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models --new-project
```

Existing project (checks only models added or changed on this branch):

```bash
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models \
  --changed-from "$(git merge-base HEAD <release branch>)"
```

Fix every `error` finding in the generated models. Never fix a finding by renaming or moving an existing model, column, seed, snapshot or schema. List warnings in the summary with a reason.

### Step 9: Create Summary Document

**File**: `.wire/<project_id>/dev/dbt_models_summary.md`

```markdown
# dbt Models Summary

**Generated**: [Date]
**Project**: [Client Name]
**Project state**: [New project | Existing project]
**Conventions**: [convention file used; form_choices rulings applied, with their decisions.md entries]
**Test key**: [data_tests | tests, and how the dbt version was found]

## Models Created

### Staging Layer
[Table of staging and base models with grain and description]

### Snapshots
[Table of snapshots, if any]

### Integration Layer
[Table of intermediate and integration models with grain and description]

### Warehouse Layer

#### Dimensions
[List of dimension tables]

#### Facts
[List of fact tables]

#### Extended Aggregates
[List of extended aggregate (`_xa`) tables]

### Macros
[List of macros added, with their `_schema_macros.yml` entries]

## Testing Strategy

- [Count] uniqueness tests
- [Count] not null tests
- [Count] at least one tests
- [Count] relationship tests
- [Count] custom tests
- [Columns where `not_null` was dropped, with the reason]

## Convention Lint

[Result of Step 8.6: error count (should be 0), warnings with reasons]

## Suggestions for the Existing Project

[Existing projects only: differences between the project's dbt_project.yml / packages.yml and the new-project templates. Suggestions only, not applied. Correcting the project key can change which models build as tables or views.]

## Next Steps

1. Run dbt models: `/wire:utils-run-dbt <project_id>`
2. Validate models: `/wire:dbt-validate <project_id>`
3. Review with team: `/wire:dbt-review <project_id>`
```

### Step 10: Update Status

**Process**:
1. Read current status file
2. Update artifacts.dbt section:
   ```yaml
   dbt:
     generate: complete
     validate: not_started
     review: not_started
     models_count: [count]
     tests_count: [count]
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 10.5: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt`
- `artifact_name`: `dbt Models Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_models_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 11: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `dbt`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 12: Confirm and Suggest Next Steps

**Output**:

```
## dbt Models Generated Successfully

**Models Created**: [count]
- Staging: [count]
- Integration: [count]
- Warehouse: [count]

**Tests Configured**: [count]

### Files Created

```
dbt/models/
├── field_descriptions.md
├── staging/
│   └── stg_<source>/
│       ├── _sources.yml
│       ├── _schema.yml
│       ├── base_<source>__<entities>.sql (x[count])
│       └── stg_<source>__<entities>.sql (x[count])
├── integration/
│   └── int_<group>/
│       ├── _schema.yml
│       ├── intermediate/
│       │   └── int_<group>__<entities>__<verb>.sql (x[count])
│       └── int_<group>__<entities>.sql (x[count])
└── warehouse/
    └── wh_<group>/
        ├── _schema.yml
        ├── wh_<group>__<entity>_dim.sql (x[count])
        ├── wh_<group>__<entity>_fact.sql (x[count])
        └── wh_<group>__<entity>_xa.sql (x[count])
dbt/snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql (x[count])
dbt/macros/_schema_macros.yml
dbt/macros/macro__<name>.sql (x[count])
dbt/macros/utility/macro__type_date.sql (new projects)
```

In an existing project, new files follow the project's current file names where a ruling keeps them (for example `stg_<source>.yml` in place of `_schema.yml`).

### Next Steps

1. **Run the dbt models**:
   /wire:utils-run-dbt <project_id>

   This will execute the models in your dbt Cloud or local environment.

2. **Validate the models**:
   /wire:dbt-validate <project_id>

   This will:
   - Run dbt tests
   - Check data quality
   - Verify row counts
   - Validate relationships

3. **Review with Analytics Engineering**:
   /wire:dbt-review <project_id>

### Quick Links

- View summary: `.wire/<project_id>/dev/dbt_models_summary.md`
- dbt models: `dbt/models/`
- View status: `/wire:status <project_id>`
```

## Reference Examples

These examples show the new-project form. In an existing project, follow any `form_choices:` ruling and keep the project's date macro.

### Staging Model Example

```sql
-- models/staging/stg_salesforce/stg_salesforce__contacts.sql
{{
    config(
        description = """
            Grain: One row per Salesforce contact.
            Contacts as received from Salesforce, excluding contacts Salesforce marks as deleted.
        """
    )
}}

with s_contacts as (

    select * from {{ source('salesforce', 'contacts') }}

),

-- Removes contacts Salesforce marks as deleted. They are kept in the source for recovery only.
filtered as (

    select * from s_contacts
    where not is_deleted

),

rename_and_cast as (

    select

        {# natural keys #}
        cast(id as {{ dbt.type_string() }}) as contact_natural_key,
        cast(account_id as {{ dbt.type_string() }}) as contact_account_natural_key,
        {# attributes #}
        lower(trim(email)) as contact_email,
        trim(first_name) as contact_first_name,
        trim(last_name) as contact_last_name,
        trim(phone) as contact_phone,
        trim(title) as contact_job_title,
        lower(trim(lead_source)) as contact_lead_source_name,
        trim(mailing_city) as contact_mailing_city_name,
        trim(mailing_country) as contact_mailing_country_name,
        {# metrics #}
        cast(number_of_employees as {{ dbt.type_int() }}) as contact_employee_count,
        {# booleans #}
        cast(has_opted_out_of_email as {{ dbt.type_boolean() }}) as contact_has_opted_out_of_email,
        {# temporal #}
        cast(last_activity_date as {{ ra_type_date() }}) as contact_last_activity_dt,
        cast(created_date as {{ dbt.type_timestamp() }}) as contact_created_ts,
        cast(last_modified_date as {{ dbt.type_timestamp() }}) as contact_last_modified_ts

    from filtered

),

final as (

    select * from rename_and_cast

)

select * from final
```

`id` and `account_id` are Salesforce identifiers. They are case-sensitive and are not lowercased.

### Integration Model Example

```sql
-- models/integration/int_core/int_core__contacts.sql
{{
    config(
        description = """
            Grain: One row per contact email address.
            Contacts from Salesforce and HubSpot, keeping the most recently changed record for each email address.
        """
    )
}}

with s_contacts_unioned as (

    select * from {{ ref('int_core__contacts__unioned') }}

),

-- Ranks each contact's records by most recent change, so one record is kept per email address.
ranked_contacts as (

    select

        *,
        row_number() over (
            partition by contact_email
            order by contact_last_modified_ts desc
        ) as contact_email_rank

    from s_contacts_unioned

),

-- Keeps the most recently changed record for each email address. Removes contacts with no email address.
latest_contacts as (

    select * from ranked_contacts
    where contact_email_rank = 1
      and contact_email is not null

),

final as (

    select

        {# natural keys #}
        contact_natural_key,
        contact_account_natural_key,
        {# attributes #}
        contact_source_system_name,
        contact_email,
        contact_first_name,
        contact_last_name,
        contact_phone,
        {# booleans #}
        contact_has_opted_out_of_email,
        {# temporal #}
        contact_created_ts,
        contact_last_modified_ts

    from latest_contacts

)

select * from final
```

`int_core__contacts__unioned` is the intermediate model that unions `stg_salesforce__contacts` and `stg_hubspot__contacts` (see Step 4).

### Warehouse Dimension Example

```sql
-- models/warehouse/wh_core/wh_core__contact_dim.sql
{{
    config(
        description = """
            Grain: One row per contact.
            Contacts from Salesforce and HubSpot, one per email address.
        """
    )
}}

with s_contacts as (

    select * from {{ ref('int_core__contacts') }}

),

add_keys as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['contact_natural_key', 'contact_source_system_name']) }} as contact_pk,
        {# foreign keys #}
        {{ dbt_utils.generate_surrogate_key(['contact_account_natural_key', 'contact_source_system_name']) }}
            as account_fk,
        {# natural keys #}
        contact_natural_key,
        contact_account_natural_key,
        {# attributes #}
        contact_source_system_name,
        contact_email,
        concat(contact_first_name, ' ', contact_last_name) as contact_full_name,
        {# booleans #}
        contact_has_opted_out_of_email,
        {# temporal #}
        contact_created_ts,
        contact_last_modified_ts

    from s_contacts

),

final as (

    select * from add_keys

)

select * from final
```

Account attributes live on `wh_core__account_dim`. The contact dimension references the account by `account_fk`.

### Schema File Example

`models/staging/stg_salesforce/_schema.yml`:

```yaml
version: 2

models:
  - name: stg_salesforce__contacts
    description: >
      Grain: One row per Salesforce contact.
      Contacts as received from Salesforce, excluding deleted contacts.
    columns:
      - name: contact_natural_key
        description: '{{ doc("contact_natural_key") }}'
        data_tests:
          - unique
          - not_null

      - name: contact_email
        description: '{{ doc("contact_email") }}'
        data_tests:
          - dbt_utils.at_least_one

      - name: contact_lead_source_name
        description: '{{ doc("contact_lead_source_name") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
          - accepted_values:
              values: ['web', 'referral', 'partner', 'event', 'other']
```

`contact_email` carries no `not_null` because Salesforce contacts can have no email address. The summary records the reason.

`models/warehouse/wh_core/_schema.yml`:

```yaml
version: 2

models:
  - name: wh_core__contact_dim
    description: >
      Grain: One row per contact.
      Contacts from Salesforce and HubSpot, one per email address.
    columns:
      - name: contact_pk
        description: '{{ doc("contact_pk") }}'
        data_tests:
          - unique
          - not_null

      - name: account_fk
        description: '{{ doc("account_fk") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
          - relationships:
              to: ref('wh_core__account_dim')
              field: account_pk
```

Use `tests:` in place of `data_tests:` where Step 6 says so.

### Quick Conventions Checklist

Before committing a dbt model:

- [ ] No existing model, column, seed, snapshot or schema renamed or moved
- [ ] `form_choices:` rulings in `.wire/conventions/dbt.yml` followed
- [ ] Filename follows the pattern for its kind: `base_<source>__<entities>`, `stg_<source>__<entities>`, `int_<group>__<entities>__<verb>`, `int_<group>__<entities>`, `wh_<group>__<entity>_(dim|fact|xa)`
- [ ] Staging and integration names plural; warehouse names singular
- [ ] File in the correct folder (`staging/stg_<source>/`, `integration/int_<group>/`, `integration/int_<group>/intermediate/`, `warehouse/wh_<group>/`)
- [ ] `config()` description opens with `Grain: One row per ...`
- [ ] All refs/sources in CTEs at top (prefixed with `s_`)
- [ ] Last CTE is `final`; model ends with `select * from final`
- [ ] 4-space indentation, lines up to 120 characters; Jinja delimiters with inner spaces
- [ ] All fields lowercase
- [ ] Every output column carries the entity prefix (foreign keys keep the referenced entity's prefix)
- [ ] Primary key `<entity>_pk` and foreign keys `<entity>_fk` created in the warehouse layer only, via `dbt_utils.generate_surrogate_key`
- [ ] Natural keys `<entity>_natural_key`, never lowercased
- [ ] Attribute strings lowercased where the value is a name, category or status
- [ ] Dates `_dt`. Timestamps `_ts` (UTC) or `_<tz>_ts`
- [ ] Booleans `<entity>_is_`, `<entity>_has_`, `<entity>_was_`
- [ ] Metrics: `_count`, `_amount`, `_amount_<currency>`, `_<measure>_<unit>`, `_pct` (0 to 100), `_ratio` (0 to 1)
- [ ] Aggregated columns lead with the function: `sum_...`, `max_by_...`
- [ ] Type casts use `{{ dbt.type_*() }}` and `{{ ra_type_date() }}` (or the project's existing date macro)
- [ ] Explicit joins (`inner join`, `left join`), no initialism aliases
- [ ] Columns in eight groups with `{# group #}` comments: primary key, foreign keys, natural keys, attributes, indexes and ranks, metrics, booleans, temporal
- [ ] Every CTE that removes rows has a comment saying why
- [ ] Configuration appropriate for layer (materialization set by folder)
- [ ] Schema file entry exists; every column documented with a doc block in `models/field_descriptions.md`
- [ ] Primary key has `unique` + `not_null`; other columns `not_null` + `dbt_utils.at_least_one`
- [ ] Test key is `data_tests:` or `tests:` per Step 6, never both on one resource
- [ ] New macros named `macro__<name>` and described in `macros/_schema_macros.yml`
- [ ] Convention lint (Step 8.6) shows no errors

---

## Edge Cases

### No Data Model Design Found

If `data_model` artifact not complete:

```
Error: Data model design not found or incomplete.

Please complete the data model design first:
/wire:data_model-generate <project_id>

The data model design is required to generate dbt models.
```

### Existing dbt Models

If dbt models already exist for some tables:

1. Detect existing models
2. Ask user:
   ```
   Found existing dbt models for:
   - <model_1>
   - <model_2>

   How should I proceed?
   1. Skip existing models (only create new ones)
   2. Update existing models in place (keeps each model's file name, location and output column names)
   3. Create with different names (append _v2)
   ```

Never rename or move an existing model, column, seed, snapshot or schema, whichever option is chosen. Changes to an existing model add columns or change logic; they do not rename what downstream models, the semantic layer or dashboards already read.

### dbt Project Not Found

If no dbt project exists:

```
No dbt project found. Would you like me to:

1. Create a new dbt project
2. Specify the dbt project location
3. Cancel (set up dbt project manually first)
```

## Validation Checks (for next step)

The validate command will:
- [ ] Run `dbt compile` (syntax check)
- [ ] Run `dbt test` (all tests pass)
- [ ] Check model dependencies (correct ref() usage)
- [ ] Validate naming conventions on added and changed models (`lint_conventions.py --changed-from`), accepting the old forms listed under Existing projects
- [ ] Check for circular dependencies

## Output Files

This command creates:
- Multiple `.sql` model files in `dbt/models/`
- Multiple `.yml` documentation files (`_sources.yml`, `_schema.yml`)
- `models/field_descriptions.md` doc blocks
- Snapshot files in `dbt/snapshots/` (if needed)
- Macro files and `macros/_schema_macros.yml` (if needed; `macros/utility/macro__type_date.sql` for new projects)
- `dbt_project.yml` and `packages.yml` (new projects only)
- `.wire/<project_id>/dev/dbt_models_summary.md`
- Updates `.wire/<project_id>/status.md`

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
