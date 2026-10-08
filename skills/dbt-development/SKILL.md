---
name: dbt-development
description: Proactive skill for validating dbt models against coding conventions. Auto-activates when creating, reviewing, or refactoring dbt models in staging, integration, or warehouse layers, and when writing base models, snapshots, seeds, macros or source declarations. Validates naming, SQL structure, field conventions, testing coverage, and documentation on new and changed code. Supports project-specific convention overrides, recorded form rulings, and sqlfluff integration.
---

# dbt Development Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | dbt-development | activated | dbt model creation, review, or refactoring triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.



## Purpose

This skill activates when working with dbt models. It applies the Rittman Analytics dbt conventions to the models Wire writes, and checks new and changed models against them. It covers model structure, naming, SQL style, testing and documentation.

**Where the rules come from.** The authority for people is the `ra_fw_core` dbt development reference: `analytics_warehouse/docs/development_reference_dbt.md`, version 0.0.1 (ra_fw_core#21). `wire/conventions/dbt.yml` is its machine-checkable form; its `reference:` block records the reference version it follows. Where the two disagree, the reference wins and the registry is corrected, with two exceptions that Wire holds until the reference adds them (see "Where Wire differs from the reference" below).

The reference states rules as facts and leaves out the reasons by design. This skill keeps the reasons, because a rule applied without its reason gets applied in the wrong place.

## The one rule

Wire applies the conventions to **new and changed** code. Wire **never renames or moves** an existing model, column, seed, snapshot or schema. Existing projects keep passing `/wire:dbt-validate`.

Why: downstream consumers (LookML views, dashboards, reverse ETL syncs, analysts' saved SQL, other teams' models) reference objects by name. A dbt rename builds a new relation and leaves the old one in the warehouse, stale. Renaming for convention alone has a cost and no benefit to the client. A rename is a separate decision, made in a refactor release (`/wire:data_refactor-generate`), never a side effect of adding a feature.

## When This Skill Activates

### User-Triggered Activation

This skill should activate when users:
- **Create new dbt models:** "Create a staging model for users from Salesforce"
- **Review existing models:** "Review this dbt model for issues"
- **Refactor models:** "Refactor this integration model to follow best practices"
- **Work with .sql files in models/, snapshots/ or macros/:** any read or write of dbt model, snapshot or macro files
- **Ask about dbt conventions:** "What are the naming conventions for warehouse models?"
- **Request schema, source or test files:** "Add tests to this model", "Declare this source"

**Keywords to watch for:**
- "dbt model", "staging", "integration", "warehouse", "intermediate", "base model"
- "snapshot", "seed", "macro", "_sources.yml", "field_descriptions"
- "refactor", "review", "validate", "check conventions"
- "stg_", "base_", "int_", "_dim", "_fact", "_xa", "snapshot_", "seed__", "macro__"
- "schema.yml", "_schema.yml", "tests", "data_tests", "dbt test"
- "multi-source", "entity resolution", "deduplication", "merge sources"
- "enable source", "disable source", "add source", "remove source"
- "source array", "dbt_project.yml vars"

### Self-Triggered Activation (Proactive)

**Activate BEFORE creating or modifying dbt SQL when:**
- You are about to suggest creating a model from scratch
- You detect .sql files in a models/ directory structure
- User asks to "write SQL" in a dbt project context
- You are reviewing changes in a dbt project
- Working with files that match dbt patterns (stg_, base_, int_, _dim, _fact, _xa)

**Example internal triggers:**
- "I'll create a staging model for..." → activate the skill first
- User shows dbt SQL file → validate against conventions
- "Let me write this transformation..." in dbt context → check conventions first

## Instructions

### 0. Establish the Situation Before Writing Anything

Answer three questions first. They decide which rules apply and how findings are reported.

**0.1 New project or existing project?**

- **New project**: no `dbt_project.yml` yet, or one Wire is creating in this release. Every file is new. Wire writes the new forms throughout, including the `dbt_project.yml` and `packages.yml` template (Step 6) and the `ra_type_date()` macro file.
- **Existing project**: the client already has models. Wire writes new forms only in files it adds or changes, and leaves everything else as it is.

**0.2 Which files are new or changed?**

"Changed" means models added or modified on the current branch compared with the base of the release branch, from git:

```bash
git merge-base HEAD <release base branch>
git diff --name-status <merge-base> -- models/ snapshots/ seeds/ macros/
```

Section A rules (below) apply to changed files only. File-naming rules for the new kinds (base model, snapshot, macro, seed) apply to **added** files only, so editing an existing macro never asks for a rename. Where git history is not available, section A findings are warnings, not failures.

**0.3 Has the project recorded a form ruling?**

A project may keep an old form for consistency with its existing models. That choice is a **ruling**: it is recorded in the release's `decisions.md` and set in the project's `.wire/conventions/dbt.yml` override under `form_choices:`:

```yaml
form_choices:
  model_name_number: singular     # plural | singular
  column_prefix: none             # entity | none
  test_key: tests                 # data_tests | tests
  source_file_name: _<source>__sources   # _sources | _<source>__sources
```

Generate follows the recorded ruling. With no ruling, generate writes the new form. Recording it in both places means the next session, or another lane, writes the same form without asking again.

Mixed naming inside one project is allowed where new models use the new form. Do not propose renaming old models to make a project uniform; the inconsistency costs less than the rename.

### 0.4 Load Convention Sources

**Priority order for the narrative conventions you apply by judgment:**
1. **Project-specific conventions** (highest priority)
   - `.dbt-conventions.md` in project root
   - `dbt_coding_conventions.md` in project root
   - `docs/dbt_conventions.md` in project
   - `analytics_warehouse/docs/development_reference_dbt.md` (a project built from `ra_fw_core` carries the reference itself)
2. **Embedded RA conventions** (fallback)
   - Conventions: `conventions-reference.md` (relative to this skill file)
   - Testing: `testing-reference.md` (relative to this skill file)

Use `Glob` to search for convention files, `Read` to load them, and note in your output which source you used.

### 0.5 Run the Checker

Naming patterns, forbidden constructs and the other mechanical checks live in a machine-readable convention file, checked by a script rather than by your own reading of the model. Resolve the convention file (client override wins):

1. `.wire/conventions/dbt.yml` in the client project, if present.
2. `wire/conventions/dbt.yml` next to this skill's framework installation (synced from the private `wire-process-registry`; see `wire/schemas/convention-schema.md`).

Run it against the models you are about to validate or have just written.

New project (every file treated as new):

```
python3 wire/scripts/lint_conventions.py --domain dbt \
  --convention <resolved dbt.yml path> --path <models dir> \
  --new-project --format json
```

Existing project (section A rules checked on changed files only):

```
python3 wire/scripts/lint_conventions.py --domain dbt \
  --convention <resolved dbt.yml path> --path <models dir> \
  --changed-from <merge-base ref> --format json
```

With neither `--new-project` nor `--changed-from`, section A rules report as warnings.

Treat its findings as ground truth for the rules it covers (filename patterns, column suffixes tied to type-cast macros, bare `join`, `union distinct`, the `final` CTE, layer boundaries, missing primary-key tests, the `Grain:` line, the test key). Do not re-argue a pass or fail the checker already gave. Everything it does not cover (grain choice, CTE quality, whether a join direction makes sense, whether a staging filter is about correctness) is your call, applied through Steps 1 to 10. If the checker is not available (no Python or PyYAML), fall back to the manual review below and say so in your output.

---

### 1. Identify the Kind of File

| Kind | Path | Filename |
|---|---|---|
| Base model | `models/staging/stg_<source>/` | `base_<source>__<entity>.sql` |
| Staging model | `models/staging/stg_<source>/` | `stg_<source>__<entities>.sql` |
| Intermediate model | `models/integration/int_<group>/intermediate/` | `int_<group>__<entities>__<verb>.sql` |
| Integration model | `models/integration/int_<group>/` | `int_<group>__<entities>.sql` |
| Dimension | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_dim.sql` |
| Fact | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_fact.sql` |
| Extended aggregate | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_xa.sql` |
| Snapshot | `snapshots/snapshot_<source>/` | `snapshot_<source>__<source_table>.sql` |
| Seed | `seeds/` | `seed__<description>.csv` |
| Macro | `macros/` (utility macros in `macros/utility/`) | `macro__<name>.sql` |
| Source declarations | `models/staging/stg_<source>/` | `_sources.yml` |

Also note: source system (staging), entity, related models (refs), expected materialization, and whether the file is new, changed or unchanged (Step 0.2).

---

### 2. Apply the Layer Design Rules

**Staging** (`models/staging/stg_<source>/`)
- Only staging models read sources, snapshots and seeds. If a source changes shape, one model changes.
- A staging model is the reusable version of one source concept, at one grain, from one source.
- Joins are avoided. A join or union is allowed only within one source system, and only where the concept cannot be staged without it (a separate delete or status table, symmetrical tables from the same system). A join across source systems is integration logic.
- A join that derives a new value from another concept, even within one source, is a derivation and belongs in a later model. Staging keeps a clear line to one source concept.
- Filtering is limited to correctness: deduplication, and rows known to be wrong. A CTE that removes rows carries a comment saying why. Filtering to a business subset here hides rows from every later model that might need them.
- The population and grain of the source are kept. Transactions are staged as transactions, not filtered to orders and named orders.
- Natural keys are extracted. Primary and foreign keys are **not** created here; they belong to the warehouse, where the entity is defined. Where no single column identifies a row, the natural key is a compound of the columns that do.
- Timestamps are cast to UTC. A timestamp held in another zone carries the zone in its name (`_cet_ts`).
- A nested record is flattened, one column per field. A repeated field (array) is carried through unchanged unless something downstream queries or tests its contents.
- Single-row derivations happen here: unit conversion, `case when` classification, resolving the meaning of null in a boolean, conforming a label the source changed over time. A derivation that needs a second model belongs in integration.
- Repeated transformation logic becomes a macro, not copied text.
- Materialized as a view.

**Base models** (`base_<source>__<entity>.sql`, beside the staging models of that source)
- Hold the join or union a source concept needs, within one source system only.
- Select from the source and apply the staging conventions.
- Only the staging model reads a base model. Later layers never do, so each concept has one staged version that everything else depends on.
- Use a base model where the shaping is repeated across models or tested on its own. Otherwise a base CTE inside the staging model is a judgement call. A simple join intrinsic to one concept sits in the staging model.

**Integration** (`models/integration/int_<group>/`)
- Exists only where needed. Where nothing needs combining, filtering or deriving, the warehouse model reads staging directly. An empty pass-through model adds a build step and nothing else.
- Joins across source systems happen here.
- Filtering to the concept the warehouse exposes happens here. Exception: where two or more warehouse models read one integration model, each exposing a different subset, each warehouse model filters to its own subset.
- Derived fields are created here, under the same rules as staging: attribute strings lowercased, casting through macros.
- Materialized as a view.

**Intermediate models** (`int_<group>__<entities>__<verb>.sql` in `models/integration/int_<group>/intermediate/`)
- Combine the same concept from more than one source, so the integration model receives one input per concept.
- The verb says what the model does to its inputs: `unioned`, `deduplicated`, `pivoted`.
- Materialized as a view, set by the folder config. Existing ephemeral intermediate models stay accepted.

**Warehouse** (`models/warehouse/wh_<group>/`)
- Dimension and fact models read integration models, or staging where no integration model is needed.
- Primary and foreign keys are created here and only here, with `dbt_utils.generate_surrogate_key`. Keys built in one place stay consistent; keys built in several drift.
- An entity's attributes live on its dimension. Other models reference it by foreign key. Copying an attribute onto a second entity is a modelling decision taken per case and recorded in `decisions.md`.
- A warehouse model filters its input only where it exposes one subset of an integration model that other warehouse models also read.
- `_xa` means **extended aggregate**: a denormalised table built from fact and dimension models, either aggregated to a summary grain (a daily summary) or combining several facts at a shared grain (an event stream). It exists only in the warehouse layer. An `_xa` model that reads an integration model may mean a dimension or fact is missing. `_xa` applies to new models; existing `_agg` models and existing `_xa` models built as bridge tables keep their names.
- Incremental materialization is allowed per model. The client decides when, and the strategy, unique key and lookback window.
- Materialized as a table.

**Snapshots** (`snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`)
- A snapshot targets a source. Staging reads it the same way it reads a source.
- The `{% snapshot %}` block name equals the filename without extension, so the relation and the file can be found from each other.
- `timestamp` strategy by default, on the source's modified timestamp. Use `check` with `check_cols` only where the source has no reliable modified timestamp; `check` compares every listed column on every run, which costs more and misses nothing only if the list is complete.
- `unique_key` names the column(s) identifying a row in the source. It is not unique in the snapshot; `dbt_scd_id` is.
- Source columns are held unchanged. The dbt meta columns (`dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`, `dbt_updated_at`) keep their names. Renaming happens in staging, so a naming change never touches captured history.
- New projects and new releases write snapshots to the `snapshots` schema. Existing snapshots keep their schema.
- `dbt_valid_to_current` is set once per client project and applied to every snapshot.

**Seeds** (`seeds/seed__<description>.csv`)
- Static reference data only. Only staging reads a seed.
- The `seed__` prefix tells a reader the table is static reference data, not loaded data.
- Seed columns keep the CSV's names; staging renames them.
- Seed naming and the `seeds` schema apply to **new projects and new releases only**. Dashboard-first mock seeds in releases already under way keep their names, so `/wire:data_refactor-generate` still finds them.

---

### 3. Validate Naming

File naming and layer-boundary findings come from the Step 0.5 checker. What follows is the full convention and the reasons.

**Model names, new form (generate):**
- Staging and integration models are **plural**: `stg_source_a__users`, `int_core__users`. A staging or integration model holds the set of source rows for a concept, and its name describes that set.
- Warehouse models are **singular**: `wh_core__user_dim`. A dimension or fact names the entity type each row is.
- Double underscore separates group (or source) from entity.

**Old forms still accepted (never renamed):**
- Singular staging and integration names (`stg_source_a__user`).
- `_<source>__sources.yml` source files.
- Existing schema file names (`stg_<source>.yml`, `integration.yml`, `wh_<group>.yml`).
- `_agg` warehouse aggregates.
- Ephemeral intermediate models.
- Existing seed names and schemas, existing snapshot schemas.

`/wire:dbt-validate` no longer reports "use singular names".

**Directory structure (new projects):**
```
models/
├── field_descriptions.md            # doc blocks for model columns, every layer
├── droughty_schema.yml              # only where the project uses droughty
├── staging/
│   └── stg_source_a/
│       ├── _sources.yml
│       ├── _schema.yml              # without droughty
│       ├── base_source_a__users.sql
│       └── stg_source_a__users.sql
├── integration/
│   └── int_core/
│       ├── _schema.yml
│       ├── int_core__users.sql
│       └── intermediate/
│           └── int_core__users__unioned.sql
└── warehouse/
    └── wh_core/
        ├── _schema.yml
        ├── wh_core__user_dim.sql
        ├── wh_core__order_fact.sql
        └── wh_core__order_xa.sql
snapshots/
└── snapshot_source_a/
    └── snapshot_source_a__users.sql
seeds/
└── seed__sku_category_lookup.csv
macros/
├── _schema_macros.yml
├── macro__geo_country.sql
└── utility/
    └── macro__type_date.sql
```

**Findings to report on new and changed files:**
- Missing or wrong layer prefix or suffix
- File in the wrong directory for its kind
- A later layer reading a base model, or a non-staging model reading a source, snapshot or seed

---

### 4. Validate SQL Structure and Style

**Required structure:**

1. Every `ref()` and `source()` sits in an import CTE at the top, prefixed `s_`. A reader sees every dependency in one place.
2. One logical unit of work per CTE where performance permits. CTE names say what the CTE does, as long as needed. A CTE with notable logic carries a comment.
3. The last CTE is `final`, and the model ends with `select * from final`. To debug, change that one line to select from any earlier CTE; nothing else needs editing. Every model ends the same way, so reviewers and tools know where the output is defined.
4. Columns take their output names in the CTE before `final`, so a column can be traced back to its source.
5. Aggregated columns lead with the function: `sum_invoice_line_item_amount`, `max_by_activity_user_name`. The name shows the value is no longer one row's, and the trace to the source column stays unbroken.
6. Every model's `config()` has a `description` that opens with a `Grain:` line: "Grain: One row per user." Grain is the first thing a reader needs to join or aggregate a model correctly; most fan-out and double-counting errors start with a wrong guess about grain. Putting it first means it is found by people and by tools.

**Canonical staging model:**
```sql
{{
    config(
        description = """
            Grain: One row per user account.
            User accounts as received from source system A.
        """
    )
}}

with s_users as (

    select * from {{ source('source_a', 'users') }}

),

rename_and_cast as (

    select

        {# natural keys #}
        cast(id as {{ dbt.type_string() }}) as user_natural_key,
        {# attributes #}
        lower(cast(name as {{ dbt.type_string() }})) as user_name,
        {# metrics #}
        cast(account_balance as {{ dbt.type_numeric() }}) as user_account_balance_amount,
        {# booleans #}
        cast(active as {{ dbt.type_boolean() }}) as user_is_active,
        {# temporal #}
        cast(created_date as {{ ra_type_date() }}) as user_created_dt,
        cast(updated_at as {{ dbt.type_timestamp() }}) as user_updated_ts

    from s_users

),

final as (

    select * from rename_and_cast

)

select * from final
```

Note that `user_natural_key` is not lowercased. See Step 5.

**SQL style:**
- Four-space indentation. Predicates line up with `where`.
- Lines up to **120** characters. The old 80 forced Jinja macro calls and surrogate key lists onto several lines for no gain in reading.
- Lowercase field and function names.
- `as` for every field and table alias.
- Trailing commas.
- Aggregate as early as possible, before joining.
- Group and order by column name, not number.
- `union all`, not `union distinct`.
- Explicit joins: `inner join`, `left join`, never bare `join`.
- No table alias initialisms. `customer` is clearer than `c`.
- A model selecting from two or more tables prefixes every column with its table name.
- Readability over a smaller line count.
- Comments in plain English, with full column names and the business's own terms (invoices, not bills). No new term for a thing the project already names.

**YAML style:** two-space indentation, list items indented, lines up to 80 characters, a blank line between dictionary list items where it helps reading.

**Jinja style:** delimiters carry inner spaces (`{{ this }}`, not `{{this}}`), newlines separate logical blocks, and column groups use the Jinja comment form (`{# attributes #}`) so the markers do not reach the compiled SQL.

**Findings:**
- `ref()` or `source()` outside the top CTEs
- Missing `final` CTE or a model not ending `select * from final`
- Missing `Grain:` line at the start of the config description
- Lines over 120, tabs, uppercase keywords, bare `join`, `union distinct`, alias initialisms

---

### 5. Validate Column Naming and Order

**Suffixes:**

| Suffix or prefix | Applies to | Example |
|---|---|---|
| `_pk` | Primary key | `subscription_pk` |
| `_fk` | Foreign key | `subscription_fk` |
| `_natural_key` | Source system identifier | `subscription_natural_key` |
| `_count` | Count of things | `order_line_count` |
| `_rank` | Ordinal position | `revenue_rank` |
| `_amount` | Value in the project's base currency | `revenue_amount` |
| `_amount_<currency>` | Value in another currency, ISO 4217 code lowercased | `revenue_amount_usd` |
| `_<measure>_<unit>` | Measured quantity with its unit | `package_weight_kg`, `call_duration_seconds` |
| `_pct` | Percentage, 0 to 100 | `discount_pct` |
| `_ratio` | Proportion, 0 to 1 | `conversion_ratio` |
| `<entity>_is_` / `_has_` / `_was_` | Boolean | `user_is_active` |
| `_dt` | Date | `user_created_dt` |
| `_ts` | Timestamp in UTC | `user_created_ts` |
| `_<timezone>_ts` | Timestamp outside UTC | `user_created_cet_ts` |

Reasons for the less obvious ones:
- **`_pct` and `_ratio` are kept apart.** A value of 0.5 is half a percent on one scale and half on the other. Mixing them gives errors of a factor of 100 that look plausible on a chart. The suffix tells the reader and the semantic layer which scale to format.
- **Every measure states its unit, except currency.** `duration` could be seconds or minutes; `duration_seconds` cannot be misread. The unit is the SI symbol lowercased where one exists (`kg`, `km`, `ml`), otherwise spelled out (`seconds`, `days`). Base currency is implicit in `_amount` because a project has one base currency; any other currency carries its code.
- **`_count` and `_rank`** mark values that must not be summed or averaged as if they were measures of the same kind.
- **Attributes carry no suffix.**
- Price columns are decimal currency (19.99, not 1999 cents), converted in staging.

**Column prefixes (new form):**
- Every output column carries the prefix of the thing the model holds: a users model gives `user_name`, `user_is_active`. After a join in the warehouse or BI tool, an unprefixed `name` is ambiguous; a prefixed one says where it came from.
- A column arriving from a model about a different thing takes this model's prefix on the way out. A column from a model about the same thing keeps its name.
- Where two columns describe the same thing, the relationship follows the prefix: `order_shipping_country_name`, `order_billing_country_name`.
- Foreign keys keep the referenced entity's prefix: `user_pk` becomes `user_fk`.
- A natural key surfaced on another entity takes that model's prefix: `order_user_natural_key`.
- Booleans follow the same rule: `user_is_active`, not `is_active`.

**Old form still accepted:** unprefixed columns (`name`, `is_active`) in existing models. Wire never renames them. In a changed model, new columns take the new form unless the project has a `column_prefix: none` ruling. Where a changed model uses unprefixed columns throughout, ask the consultant whether to record a ruling before adding prefixed columns beside them.

**Lowercasing (Wire holds an exception to the reference):**
- Wire lowercases **attribute strings only**. `London` and `london` group as one value in a BI tool only if they are stored the same way.
- **Natural keys and source identifiers are never lowercased.** Some are case-sensitive: Salesforce 15-character IDs differ only by case, so lowercasing merges different records and breaks joins back to the source. The reference lowercases every staging string; Wire holds this exception until the reference adds it.

**Casting:**
- Always through macros, never a bare warehouse type, so models stay portable across BigQuery, Snowflake, Databricks and Postgres: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`, `{{ dbt.type_int() }}`.
- Dates: new projects use `{{ ra_type_date() }}`, defined in `macros/utility/macro__type_date.sql`. dbt has no cross-database date type macro; this one asks the adapter for its date type:
  ```sql
  {% macro ra_type_date() %}
      {{ return(api.Column.translate_type("date")) }}
  {% endmacro %}
  ```
- An existing project keeps the date macro it already uses (`type_date()` or its own). Switching would change every model that casts a date, for no change in output.

**Column order (eight groups, each opened by a Jinja comment):**
1. `{# primary key #}`
2. `{# foreign keys #}`
3. `{# natural keys #}`
4. `{# attributes #}`
5. `{# indexes and ranks #}`
6. `{# metrics #}`
7. `{# booleans #}`
8. `{# temporal #}`

This refines the old six groups (keys, attributes, indexes/ranks, metrics, booleans, temporal). Splitting keys into three shows at a glance which keys Wire generated and which came from the source. Omit a group's comment where the model has no columns of that kind.

**General:** snake_case, business terms rather than source terms, no SQL reserved words, the same name for the same concept across models.

**Findings (new and changed columns):**
- Missing `_pk` / `_fk`, or keys not built with `dbt_utils.generate_surrogate_key`
- Keys created below the warehouse layer
- Measures without a unit, `_pct` values on a 0 to 1 scale or the reverse
- Natural keys lowercased
- Bare warehouse types in casts
- Columns out of group order, or groups without their Jinja comment

---

### 6. Validate Model Configuration

**Materialization by kind:**

| Kind | Materialization | Schema |
|---|---|---|
| Base, staging | `view` | `staging` |
| Intermediate, integration | `view` | `integration` |
| Warehouse | `table` (incremental allowed per model) | project default |
| Snapshot | `snapshot` | `snapshots` |
| Seed | `table` | `seeds` |

Base and intermediate models take their materialization from their folder and carry no entry of their own in `dbt_project.yml`. `ephemeral` applies per model, for a model that only exists to be inlined; dbt cannot select an ephemeral model directly and `dbt run-operation` cannot reference one.

**Where a config belongs:** anything that applies to every model in a directory, and materialization, goes in `dbt_project.yml`. The developer description, unique key, partitioning and clustering go in the model's `config()` block. The end-user description goes in the schema file.

**New projects: `dbt_project.yml` template.** Layer configs sit under the real project name. A config under any other key is silently ignored by dbt.

```yaml
models:
  +persist_docs:
    relation: true
    columns: true
  <project_name>:
    staging:
      +materialized: view
      +schema: staging
    integration:
      +materialized: view
      +schema: integration
    warehouse:
      +materialized: table
      +meta:
        required_docs: true
        required_tests: {"unique": 1, "not_null": 1}

seeds:
  <project_name>:
    +schema: seeds

snapshots:
  <project_name>:
    +schema: snapshots
```

`+persist_docs` sends descriptions to the warehouse, so analysts see them in the warehouse console as well as in dbt docs.

**New projects: `packages.yml`:**
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: ">=1.3.0"
  - package: tnightengale/dbt_meta_testing
    version: ">=0.4.0"
```

**Projects that use droughty** set `required_docs: false`. droughty does not write model descriptions and rewrites `models/droughty_schema.yml` on every run, so `required_docs` would fail every warehouse model. `required_tests` stays on. The documentation rule is met through doc blocks in `models/field_descriptions.md`, which droughty writes into column descriptions.

**Existing projects: suggest, never apply.** Compare the project's `dbt_project.yml` and `packages.yml` with the template and report the differences as suggestions. Do not edit them. Correcting the project key in an existing project can change which models build as tables or views: configs that were silently ignored start to apply on the next run.

**Findings:**
- Warehouse models not materialized as tables (incremental is allowed)
- Materialization set in a model where the folder config already sets it
- `config()` without a `description`

---

### 7. Validate Testing

Primary-key test coverage comes from the Step 0.5 checker. Testing strategy is project specific; what follows is the Wire default.

**Generated tests:**
- Primary keys: `unique` and `not_null`. Always.
- Other columns that are populated in every row: `not_null`.
- Wire adds `dbt_utils.at_least_one` **alongside** `not_null`, never in place of it. `at_least_one` only checks that a column is not entirely empty, which also catches an empty table or a column that broke upstream. `not_null` checks every row. Replacing one with the other would let partial nulls through. The reference makes `at_least_one` the default column test; Wire holds this exception until the reference adds it.
- Foreign keys: `relationships`. Enums: `accepted_values`. Multi-source integration models: `dbt_utils.unique_combination_of_columns`.

**Test key:**
- `data_tests:` on dbt 1.8 and later. dbt renamed schema tests to data tests to tell them apart from unit tests.
- `tests:` for dbt before 1.8.
- In a schema file that already uses `tests:`, keep `tests:`, so one file reads one way and the diff shows only the real change.
- Never both keys on one resource; dbt rejects it.
- A `test_key:` ruling in `form_choices` overrides the default.

**Enforcement:** where `packages.yml` includes `dbt_meta_testing`, run:
```bash
dbt run-operation required_docs
dbt run-operation required_tests
```
They do not run as part of `dbt run` or `dbt build`. Skip them where the package is not installed.

See `testing-reference.md` for patterns, severity and troubleshooting.

---

### 8. Validate Documentation

- **Every column in every layer** is documented: base, staging, intermediate, integration and warehouse. (Previously only warehouse and staging.)
- Model column descriptions are held once, as doc blocks in `models/field_descriptions.md`. Schema files reference them: `description: '{{ doc("user_pk") }}'`. A column that keeps its name across layers uses one doc block, so its meaning is written once and cannot drift.
- Source columns are the exception: their descriptions are written inline in `_sources.yml` (Step 9).
- Every model's `config()` description opens with the `Grain:` line (Step 4). That description is for developers; the schema file description is for end users. A `config()` description does not satisfy `required_docs`, which reads the schema file.

**Schema files:**
- **With droughty:** `models/droughty_schema.yml` is generated from the warehouse. Do not hand-edit it; write doc blocks and re-run droughty.
- **Without droughty:** new directories get a `_schema.yml` per subdirectory. Existing schema file names are kept.

```markdown
{% docs user_pk %}
The surrogate primary key of the user entity.
{% enddocs %}
```

```yaml
models:
  - name: wh_core__user_dim
    description: >
      Grain: One row per user.
      The user dimension. Current users, plus users seen on activity who
      have left.
    columns:
      - name: user_pk
        description: '{{ doc("user_pk") }}'
        data_tests:
          - unique
          - not_null
```

**Findings (new and changed models):** undocumented columns in any layer, the same column described twice instead of one doc block, vague descriptions ("the user", "an ID").

---

### 9. Validate Source Declarations (`_sources.yml`)

- One `_sources.yml` per `stg_<source>/` directory, declaring one source named for the directory without `stg_`: `stg_source_a/_sources.yml` declares `source_a`.
- `schema` (the dataset the loading tool writes to) and `loader` (the loading tool) are set.
- The source description states facts shared by its tables: system, loader, table groups, the date data starts, units, the columns that join tables.
- A table is declared only where a staging model, base model or snapshot reads it.
- Table `name` is the business name of the concept. `identifier` holds the raw table name where different, so models read in business terms and a raw rename touches one line.
- Table description opens `Grain: ...`, then `Source table group:` where the source has groups, then what the table holds and how it is loaded (full refresh, re-read window, deletes marked), and ends with a `Use it for ...` sentence.
- Every column of a declared table is declared, under its source name, unchanged.
- Column descriptions are written inline, not as doc blocks. A source column describes the raw system, not a staged column, and is not reused elsewhere.
- A column description states what the column means in the source system, and where they apply: unit, time zone, what a null means, the fields of a JSON object or array, the allowed values.
- An identifier column's description says it identifies a row and names the columns elsewhere that hold the same value.
- A column holding personal data carries "Personal data." so a privacy review can find every one by search.
- A profiled figure carries the date measured: "Null on 30% of rows as at 2026-09." Without the date, the figure cannot be checked later.
- Loader columns (`_fivetran_synced`, `_loaded_at`) are declared.
- `freshness` (with `loaded_at_field`) is the only test in `_sources.yml`. Assumptions about data shape are tested on the staging model, where the project can act on a failure. `warn_after` and `error_after` are set per client project.
- New source files are `_sources.yml`. Existing `_<source>__sources.yml` files keep their names.

```yaml
version: 2

sources:
  - name: source_a
    description: >
      Source system A, loaded by Fivetran. Data starts on 1 January 2024.
      Durations are in seconds.
    schema: fivetran_source_a
    loader: fivetran
    tables:
      - name: users
        identifier: user_accounts
        description: >
          Grain: One row per user account.
          Holds the current state of each account. Fivetran replaces the
          table in full on every run.
          Use it for user attributes such as name and email address.
        config:
          loaded_at_field: _fivetran_synced
          freshness:
            warn_after: {count: 24, period: hour}
            error_after: {count: 48, period: hour}
        columns:
          - name: id
            description: >
              Source system identifier for the account. One row per id.
              The same value is held in orders.account_id.
          - name: email
            description: >
              The account holder's email address. Personal data.
              Null on 5% of rows as at 2026-09.
          - name: _fivetran_synced
            description: When Fivetran loaded the row. UTC.
```

---

### 10. Validate Macros

- New macros: one per file, `macros/macro__<name>.sql`; utility macros in `macros/utility/`. Adapter versions (`default__`, `bigquery__`, `snowflake__`) sit in the same file as the macro they implement, so one file holds everything about one macro.
- Every macro has an entry in `macros/_schema_macros.yml`: `name`, `description` (what it does and returns; a macro run as an operation includes its `dbt run-operation` command), and `arguments`, each with `name`, `type`, `description`. The `name` must match the macro as defined in the file, because dbt attaches the entry by name.
- A change that adds a macro or changes its arguments or behaviour updates its `_schema_macros.yml` entry in the same change.
- dbt override macros such as `generate_schema_name` keep their dbt names; dbt finds them by name.
- Existing macro files are never renamed.

```yaml
macros:
  - name: macro__geo_country
    description: >
      Converts a country name or code to its ISO 3166-1 alpha-3 code, for
      Looker map fields. Returns the lowercased input when no match is found.
    arguments:
      - name: country
        type: string
        description: The country name or code to convert.
```

---

### 11. Run sqlfluff (if available)

```bash
which sqlfluff
```

If available: check for a `.sqlfluff` config in the project root, run `sqlfluff lint <model_file> --dialect <dialect>`, and include its findings. A project `.sqlfluff` that sets `max_line_length = 80` is the project's choice; report the difference from 120 as a suggestion only.

If not available: note "sqlfluff not detected; recommend installing for automated linting" and check style by hand.

---

### 12. Output the Validation Report

```
## dbt Model Validation Report

**Model:** `<model_name>.sql`
**Kind:** <base / staging / intermediate / integration / dim / fact / xa / snapshot / macro>
**Scope:** <new / changed / unchanged>   (from git; "unknown" if no history)
**Convention source:** <project-specific / RA defaults> | checker run with <--new-project / --changed-from <ref> / no scope flag>
**Form rulings:** <none / form_choices values in force>

### Summary
- X checks passed
- Y issues (N errors, M warnings, P suggestions)

### Naming
### SQL structure and style
### Columns
### Configuration
### Testing
### Documentation
### Source declarations / macros (where relevant)
### sqlfluff

## Recommendations
### Errors (must fix before merge)
1. <issue>
   - **Location:** <file:line>
   - **Current:** `<current code>`
   - **Should be:** `<correct pattern>`
   - **Reason:** <why this matters>
### Warnings (should fix)
### Suggestions (project-level, never applied automatically)
```

Severity rules:
- A section A rule broken in a new or changed file is an error.
- A section A rule broken in an unchanged file is not reported.
- Where scope is unknown (no git history), section A findings are warnings.
- An old form that is still accepted is never a finding.
- `dbt_project.yml` and `packages.yml` differences in an existing project are suggestions.

---

## 13. Multi-Source Data Warehouse Framework

Use this pattern when the same entities (companies, contacts, products) arrive from several source systems with different IDs and attributes. Full examples are in `examples/multi-source-*`.

### Layers in the pattern

| Layer | Purpose | New-form name | Materialization |
|---|---|---|---|
| Staging | Source-specific shaping, standard column names, ID prefixing | `stg_<source>__<entities>.sql` | view |
| Intermediate | Union of the same concept across enabled sources | `int_<group>__<entities>__unioned.sql` | view |
| Integration | Entity resolution, deduplication, merge-list handling | `int_<group>__<entities>.sql` | view (table if performance needs it) |
| Warehouse | Dimensions and facts with surrogate keys | `wh_<group>__<entity>_dim.sql` / `_fact.sql` | table |

Projects built on the older pattern (`models/sources/`, `int__company.sql`, `company_dim.sql`, `merge_sources.sql`) keep those names. New models in such a project follow the table above unless a `form_choices` ruling says otherwise.

### Configuration-driven source management

Sources are enabled or disabled through variables in `dbt_project.yml`:

```yaml
vars:
  crm_warehouse_company_sources:
    - 'hubspot_crm'
    - 'xero_accounting'
    - 'harvest_projects'
  finance_warehouse_invoice_sources:
    - 'xero_accounting'
    - 'harvest_projects'

  stg_hubspot_crm_id-prefix: 'hubspot-'
  stg_hubspot_crm_etl: 'fivetran'
  stg_hubspot_crm_schema: 'fivetran_hubspot'

  enable_companies_merge_file: true
```

### Conditional compilation in staging

```sql
{% if 'hubspot_crm' in var('crm_warehouse_company_sources', []) %}

{{
    config(
        description = """
            Grain: One row per HubSpot company.
            HubSpot companies with source-prefixed natural keys, ready to union with other sources.
        """
    )
}}

with s_companies as (

    select * from {{ source('hubspot_crm', 'companies') }}

),

-- Removes companies Fivetran has marked deleted in HubSpot.
remove_deleted as (

    select * from s_companies

    where not coalesce(_fivetran_deleted, false)

),

rename_and_cast as (

    select

        {# natural keys #}
        concat('{{ var("stg_hubspot_crm_id-prefix") }}', cast(id as {{ dbt.type_string() }})) as company_natural_key,
        {# attributes #}
        lower(trim(cast(property_name as {{ dbt.type_string() }}))) as company_name,
        lower(trim(cast(property_website as {{ dbt.type_string() }}))) as company_website,
        'hubspot_crm' as company_source_system,
        {# temporal #}
        cast(property_createdate as {{ dbt.type_timestamp() }}) as company_created_ts

    from remove_deleted

),

final as (

    select * from rename_and_cast

)

select * from final

{% else %}

{{ config(enabled = false) }}

{% endif %}
```

The ID prefix stops `12345` in HubSpot colliding with `12345` in Xero. The prefix is added; the source ID itself is not lowercased.

Where one source can arrive through more than one loader (Stitch, Fivetran, Airbyte), branch the import CTE on `var("stg_<source>_etl")` inside the same model so the rest of the model is shared.

### Intermediate union, integration merge, warehouse keys

1. **Intermediate** (`int_crm__companies__unioned.sql`): the `merge_sources` macro unions the staging model of every enabled source. See `examples/merge-sources-macro.sql`.
2. **Integration** (`int_crm__companies.sql`): group by the matching key, collect every source ID into an array (`company_natural_keys`), keep the best attribute values, count sources. Where name matching is not enough, a merge-list seed (`seeds/seed__company_merge_list.csv` in new projects) maps one company ID to another. See `examples/multi-source-integration-example.sql`.
3. **Warehouse dimension** (`wh_crm__company_dim.sql`): generate the surrogate key from the business key, not from a source ID, so the key is stable when sources are added or removed. Keep the source ID array. See `examples/multi-source-dimension-example.sql`.
4. **Warehouse fact** (`wh_finance__invoice_fact.sql`): join to the dimension through the source ID array (`in unnest(...)` on BigQuery). See `examples/multi-source-fact-example.sql`.

### Multi-source checklist

**Configuration**
- [ ] Source arrays in `dbt_project.yml` for each entity
- [ ] ID prefix variable for each source
- [ ] ETL variable where more than one loader is supported
- [ ] Feature flags for optional behaviour (merge files, enrichment)

**Staging**
- [ ] Each model checks its source is enabled before compiling
- [ ] Natural keys prefixed with the source identifier, case kept
- [ ] Column names the same across all sources for one concept

**Intermediate and integration**
- [ ] `merge_sources` used for the union
- [ ] Source IDs collected into arrays
- [ ] Attribute choice rule stated in a comment on the CTE
- [ ] Merge-list seed configured if needed
- [ ] Source count kept for data quality

**Warehouse**
- [ ] Surrogate keys from business keys, not source IDs
- [ ] Source ID arrays kept on dimensions
- [ ] Facts join through the array

### Adding a source

1. Add it to the source array and add its prefix, ETL and schema variables.
2. Declare it in `models/staging/stg_<source>/_sources.yml` (Step 9).
3. Create the staging model with the conditional compilation check.
4. Build and test the staging model alone before the integration models pick it up.

### Removing a source

1. Remove it from the source array. Its staging models disable themselves.
2. Historical source IDs stay in the dimension arrays for audit.

### Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Model not compiling | Source not in enablement array | Add source to the `*_sources` variable |
| Duplicate dimension rows | Matching key cleaned differently per source | Use one cleaning rule (or macro) in every source |
| Missing fact-to-dimension joins | Source ID not in the array | Check the ID prefix is the same in staging and fact |
| Array contains duplicates | Missing `distinct` in `array_agg` | Add `distinct` |
| Wrong loader used | ETL variable wrong | Check `stg_*_etl` |

---

## 14. Creating and Changing Models

**Creating a new model:**
1. Settle the kind with Step 1 and the layer maps in Step 2. Ask if unclear.
2. Name and place it by Step 3, following any `form_choices` ruling.
3. Write the `config()` description with the `Grain:` line first.
4. Import CTEs (`s_`), one unit of work per CTE, `final`, `select * from final`.
5. Apply Step 5: suffixes, entity prefixes, eight column groups, casting macros, attribute strings lowercased, natural keys left as they are.
6. Add doc blocks to `field_descriptions.md` for every new column, and the schema entry with tests (Step 7) under the project's test key.
7. For a staging model on a new table, declare the table in `_sources.yml`.
8. Run the checker (Step 0.5) and present the model for review before writing.

**Changing an existing model:**
1. Keep its file name, location, materialization and every existing column name.
2. Apply section A rules to the model as changed: `Grain:` line, `select * from final`, column groups, documentation of every column, tests on new columns.
3. New columns follow Step 5, subject to any ruling.
4. Do not "tidy" unrelated parts of the file. Unrelated edits widen the diff, the review and the risk.
5. Run the checker with `--changed-from`.

---

## 15. Supporting References

**In this skill directory:**
- `conventions-reference.md`: quick reference for naming, style and structure, with reasons
- `testing-reference.md`: test requirements, test key, patterns, troubleshooting
- `examples/staging-model-example.sql`, `examples/base-model-example.sql`
- `examples/intermediate-model-example.sql`, `examples/integration-model-example.sql`
- `examples/warehouse-model-example.sql`, `examples/extended-aggregate-example.sql`
- `examples/snapshot-example.sql`
- `examples/sources-example.yml`, `examples/schema-example.yml`, `examples/field-descriptions-example.md`
- `examples/new-project-dbt_project.yml`
- `examples/multi-source-staging-example.sql`, `examples/multi-source-integration-example.sql`
- `examples/multi-source-dimension-example.sql`, `examples/multi-source-fact-example.sql`
- `examples/merge-sources-macro.sql`, `examples/multi-source-dbt-project-example.yml`
- `examples/before-after-refactor.md`: changing an existing model without renaming it
- `examples/validation-report-pass.md`, `examples/validation-report-fail.md`

**Convention sources:**
- Reference for people: `ra_fw_core` `analytics_warehouse/docs/development_reference_dbt.md` (0.0.1)
- Machine-checkable form: `wire/conventions/dbt.yml`, or the project's `.wire/conventions/dbt.yml`
- Project-specific narrative: `.dbt-conventions.md` and the other files in Step 0.4

### Where Wire differs from the reference

| Topic | Reference | Wire | Why |
|---|---|---|---|
| Lowercasing in staging | Every string, natural keys included | Attribute strings only | Case-sensitive source IDs would merge records |
| Default column test | `dbt_utils.at_least_one` | `at_least_one` alongside `not_null`; PKs keep `unique` + `not_null` | `at_least_one` misses partial nulls |

Both are held until the reference adds the exceptions.

---

## 16. Important Guidelines

**Always validate when:** creating models, reviewing changes, refactoring, or giving dbt guidance in a project.

**Validation mode, not auto-fix:**
- Give clear findings with the correct pattern and the reason
- Offer to make specific changes if the user approves
- Never modify silently
- Never rename or move an existing object as part of a fix

**Project awareness:**
- Check project conventions and `form_choices` rulings first
- Say which convention source and checker scope you used
- Respect project overrides while noting the RA default

**Priority levels:**
- **Error:** breaks functionality, breaks a section A rule in new or changed code, missing primary key tests
- **Warning:** section A findings where scope is unknown; maintainability; missing documentation on unchanged code the user asked about
- **Suggestion:** project-level configuration, style preferences

---

## 17. Examples of Activation

**Example 1: Creating a staging model in an existing project**
```
User: "Create a staging model for HubSpot contacts"

Actions:
1. Activate the skill, log the activation
2. Existing project: read .wire/conventions/dbt.yml for form_choices
3. No ruling: name it stg_hubspot__contacts.sql (plural), prefix columns contact_
4. Declare the contacts table in _sources.yml (or the existing _hubspot__sources.yml)
5. Add doc blocks and schema entry with unique + not_null + at_least_one
6. Run the checker with --changed-from <merge-base>
7. Present the model for review
```

**Example 2: Reviewing an existing model**
```
User: "Review this dbt model" [provides file]

Actions:
1. Activate the skill, load conventions
2. Work out scope from git: new, changed or unchanged
3. Run the checker with --changed-from
4. Report section A findings only if the model is new or changed
5. Do not report accepted old forms (singular names, unprefixed columns, tests:)
```

**Example 3: Starting a new project**
```
User: "Set up the dbt project for this engagement"

Actions:
1. Write dbt_project.yml and packages.yml from the Step 6 template under the real project name
2. Add macros/utility/macro__type_date.sql and its _schema_macros.yml entry
3. Create models/field_descriptions.md
4. If droughty will be used, set required_docs: false
5. Run the checker with --new-project
```

**Example 4: Multi-source entity resolution**
```
User: "Create a company dimension combining HubSpot, Xero and Harvest"

Actions:
1. Review dbt_project.yml for source arrays; add them if missing
2. Staging per source: stg_<source>__companies.sql with conditional compilation and ID prefixing
3. Intermediate: int_crm__companies__unioned.sql using merge_sources
4. Integration: int_crm__companies.sql with source ID arrays and optional merge-list seed
5. Warehouse: wh_crm__company_dim.sql with surrogate key from the business key
6. Schema entries, doc blocks and tests; run the checker
```

---

### Command Execution Tips

- **Use `--quiet`** for cleaner `dbt run` and `dbt build` output.
- **Preview selectors** with `dbt list --select <selector>` before `dbt build` or `dbt run`.
- **Use `dbt show --limit N`** to preview model output.
- **Check `target/run_results.json`** after runs for per-model timing, status and row counts.
- **Prefer `dbt build`** over separate `dbt run` and `dbt test`; it runs models and tests in dependency order.
- **Use `--warn-error-options`** to promote specific warnings to errors.
- **Named runs**: where the client project has a `selectors.yml`, use `dbt build --selector <name>`.
- **dbt Fusion** (`dbtf`): if the project uses the Fusion runtime, invoke with `dbtf` or `~/.local/bin/dbt` (not the venv `dbt`). See the `dbt-fusion` skill.
- **dbt documentation**: append `.md` to any `docs.getdbt.com` URL for clean markdown. `https://docs.getdbt.com/llms.txt` lists pages.

---

## 18. Skill Deactivation

Do NOT activate this skill when:
- Working with non-dbt SQL (raw queries, database migrations)
- User explicitly says "ignore conventions" or "quick prototype"
- User is asking about dbt Cloud, dbt Core installation, or infrastructure rather than model development
