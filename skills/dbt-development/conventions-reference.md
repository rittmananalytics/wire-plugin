# dbt Conventions Quick Reference

Embedded reference used by the dbt development skill. The authority for people is the `ra_fw_core` dbt development reference (`analytics_warehouse/docs/development_reference_dbt.md`, version 0.0.1, ra_fw_core#21). `wire/conventions/dbt.yml` is its machine-checkable form, run by `wire/scripts/lint_conventions.py` (see `wire/schemas/convention-schema.md`). Where the reference and Wire's copy disagree, the reference wins, except for the two exceptions listed at the end of this file.

The reference states rules without reasons. This file gives the reason beside each rule that needs one.

---

## Scope: new and changed code only

- Wire writes these conventions into **new and changed** files.
- Wire **never renames or moves** an existing model, column, seed, snapshot or schema. Downstream consumers (LookML, dashboards, syncs, analysts' SQL) reference names, and a dbt rename leaves the old relation behind, stale.
- Section A rules (the structural rules below) are checked on changed models only. File naming for the new kinds (base, snapshot, macro, seed) is checked on **added** files only.
- Where git history is not available, section A findings are warnings.
- An old form that is still accepted is never a finding.

Checker:

```
python3 wire/scripts/lint_conventions.py --domain dbt \
  --convention <.wire/conventions/dbt.yml if present, else wire/conventions/dbt.yml> \
  --path <models dir> (--new-project | --changed-from <merge-base ref>)
```

Without either scope flag, section A rules report as warnings.

---

## New form and accepted old form

| Area | New (generate) | Old (still accepted) |
|---|---|---|
| Staging and integration model names | plural: `stg_source_a__users`, `int_core__users` | singular: `stg_source_a__user` |
| Warehouse model names | singular: `wh_core__user_dim` | same |
| Column prefixes | entity prefix on every output column: `user_name` | unprefixed: `name` |
| Boolean names | `user_is_active` | `is_active` |
| Seed files | `seeds/seed__<description>.csv`, `seeds` schema | existing names and schema |
| Snapshot schema | `snapshots` | existing schema |
| Intermediate models | `view`, set by folder | `ephemeral` |
| Test key | `data_tests:` (dbt 1.8+) | `tests:` |
| Source file name | `_sources.yml` | `_<source>__sources.yml` |
| Schema file name (no droughty) | `_schema.yml` per subdirectory | `stg_<source>.yml`, `integration.yml`, `wh_<group>.yml` |
| Warehouse aggregate | `_xa` | `_agg` |

Seed naming and the `seeds` and `snapshots` schemas apply to new projects and new releases only. Dashboard-first mock seeds in a release already under way keep their names so `data_refactor` still finds them.

**Rulings.** A project may keep an old form for consistency. The choice is recorded in the release's `decisions.md` and set in `.wire/conventions/dbt.yml`:

```yaml
form_choices:
  model_name_number: plural            # plural | singular
  column_prefix: entity                # entity | none
  test_key: data_tests                 # data_tests | tests
  source_file_name: _sources           # _sources | _<source>__sources
```

Generate follows the ruling. Mixed naming inside one project is allowed where new models use the new form.

**Why plural for staging and integration, singular for warehouse.** A staging or integration model holds a set of source rows for a concept, and its name describes the set (`users`). A dimension or fact names the entity type each row is (`user_dim`).

---

## File naming

| Kind | Path | Pattern | Example |
|---|---|---|---|
| Base model | `models/staging/stg_<source>/` | `base_<source>__<entity>.sql` | `base_source_a__users.sql` |
| Staging model | `models/staging/stg_<source>/` | `stg_<source>__<entities>.sql` | `stg_source_a__users.sql` |
| Intermediate model | `models/integration/int_<group>/intermediate/` | `int_<group>__<entities>__<verb>.sql` | `int_core__users__unioned.sql` |
| Integration model | `models/integration/int_<group>/` | `int_<group>__<entities>.sql` | `int_core__users.sql` |
| Dimension | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_dim.sql` | `wh_core__user_dim.sql` |
| Fact | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_fact.sql` | `wh_core__transaction_fact.sql` |
| Extended aggregate | `models/warehouse/wh_<group>/` | `wh_<group>__<entity>_xa.sql` | `wh_engagement__engagement_xa.sql` |
| Snapshot | `snapshots/snapshot_<source>/` | `snapshot_<source>__<source_table>.sql` | `snapshot_source_a__users.sql` |
| Seed | `seeds/` | `seed__<description>.csv` | `seed__sku_category_lookup.csv` |
| Macro | `macros/`, utility in `macros/utility/` | `macro__<name>.sql` | `macro__geo_country.sql` |
| Source declarations | `models/staging/stg_<source>/` | `_sources.yml` | |
| Model schema (no droughty) | each model subdirectory | `_schema.yml` | |
| Column doc blocks | `models/` | `field_descriptions.md` | |

`_xa` means **extended aggregate**: a denormalised table built from fact and dimension models, aggregated to a summary grain or combining several facts at a shared grain. Wire used to describe `_xa` as a cross-attribute or bridge model. The new meaning applies to new models; no existing name changes.

---

## Layer rules

| Layer | Reads | Does | Does not |
|---|---|---|---|
| Staging | sources, snapshots, seeds, its own base models | rename, cast, lowercase attribute strings, UTC timestamps, flatten records, extract natural keys, single-row derivations, correctness filters | create PK/FK, join across sources, filter to a business subset |
| Base | sources | the join or union one source concept needs, within one source system | get read by anything except its staging model |
| Intermediate | staging | combine the same concept from several sources | |
| Integration | staging, intermediate | joins across sources, filtering to the exposed concept, derived fields | exist where nothing needs integrating |
| Warehouse | integration, or staging where no integration model is needed | create PK/FK with `dbt_utils.generate_surrogate_key`, hold an entity's attributes on its dimension | |
| Snapshot | a source | record source state over time, columns unchanged | rename columns or dbt meta columns |

Reasons:
- **Only staging reads sources.** If a source changes shape, one model changes.
- **Later layers never read base models.** Each concept has one staged version that everything else depends on.
- **Staging filters only for correctness, with a comment on the CTE.** A business filter in staging hides rows from every later model that might need them.
- **Keys are created in the warehouse only.** Keys built in one place stay consistent.
- **Integration only where needed.** An empty pass-through model adds a build step and nothing else.

---

## SQL structure

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

| Rule | Reason |
|---|---|
| `config()` description opens `Grain: One row per ...` | Grain is the first thing needed to join or aggregate correctly; wrong grain causes fan-out and double counting |
| Every `ref()` / `source()` in an import CTE at the top, prefixed `s_` | Every dependency visible in one place |
| One unit of work per CTE, named for what it does; comment notable logic | Each step can be read and checked on its own |
| Columns take their output names in the CTE before `final` | A column can be traced back to its source |
| Last CTE is `final`; model ends `select * from final` | Debug by changing one line to select any earlier CTE |
| Aggregated columns lead with the function: `sum_invoice_line_item_amount` | Shows the value is no longer one row's, keeps the trace to the source column |

---

## SQL, YAML and Jinja style

| Rule | Value |
|---|---|
| SQL indentation | 4 spaces, predicates lined up with `where` |
| SQL line length | 120 characters (was 80; 80 forced macro calls onto several lines for no gain) |
| Case | lowercase fields and functions |
| Aliases | always `as` |
| Commas | trailing |
| Joins | explicit `inner join`, `left join`; never bare `join` |
| Table names | full names, no initialisms (`customer`, not `c`) |
| Column prefixes in joins | every column prefixed with its table name when two or more tables are selected |
| Union | `union all`, not `union distinct` |
| Group and order by | column names, not numbers |
| Aggregation | as early as possible, before joins |
| YAML | 2-space indentation, list items indented, lines up to 80 |
| Jinja | inner spaces in delimiters (`{{ this }}`), newlines between logical blocks |
| Comments | plain English, full column names, the business's own terms |

---

## Column naming

| Suffix or prefix | Applies to | Example |
|---|---|---|
| `_pk` | Primary key | `subscription_pk` |
| `_fk` | Foreign key | `subscription_fk` |
| `_natural_key` | Source system identifier | `subscription_natural_key` |
| `_count` | Count of things | `order_line_count` |
| `_rank` | Ordinal position | `revenue_rank` |
| `_amount` | Base currency | `revenue_amount` |
| `_amount_<currency>` | Other currency, ISO 4217 lowercased | `revenue_amount_usd` |
| `_<measure>_<unit>` | Measured quantity | `package_weight_kg`, `call_duration_seconds` |
| `_pct` | Percentage, 0 to 100 | `discount_pct` |
| `_ratio` | Proportion, 0 to 1 | `conversion_ratio` |
| `<entity>_is_` / `_has_` / `_was_` | Boolean | `user_is_active` |
| `_dt` | Date | `user_created_dt` |
| `_ts` | UTC timestamp | `user_created_ts` |
| `_<timezone>_ts` | Non-UTC timestamp | `user_created_cet_ts` |

- **`_pct` and `_ratio` are kept apart** because 0.5 means half a percent on one scale and half on the other. Mixing them gives plausible-looking errors of a factor of 100.
- **Every measure states its unit except currency.** SI symbol lowercased where one exists (`kg`, `km`, `ml`), otherwise spelled out (`seconds`, `days`). A project has one base currency, so `_amount` needs no code; any other currency carries one.
- **Attributes carry no suffix.**
- Prices are decimal currency (19.99), converted in staging.
- PK and FK are generated with `dbt_utils.generate_surrogate_key` (not the deprecated `surrogate_key`).

**Entity prefixes (new form).** Every output column carries the model's entity prefix: `user_name`. A column from a model about a different thing takes this model's prefix; one from a model about the same thing keeps its name. Two columns about the same thing are told apart by the relationship after the prefix: `order_shipping_country_name`. Foreign keys keep the referenced entity's prefix (`user_fk`). A natural key on another entity takes that model's prefix (`order_user_natural_key`). Reason: after a join, an unprefixed `name` is ambiguous.

**Lowercasing.** Attribute strings only, so `London` and `london` group as one value. Natural keys and source identifiers are never lowercased: some are case-sensitive (Salesforce 15-character IDs), and lowercasing can merge different records.

**Casting.** Always a macro, never a bare warehouse type: `dbt.type_string()`, `dbt.type_numeric()`, `dbt.type_boolean()`, `dbt.type_timestamp()`, `dbt.type_int()`. Dates in new projects use `ra_type_date()` from `macros/utility/macro__type_date.sql`:

```sql
{% macro ra_type_date() %}
    {{ return(api.Column.translate_type("date")) }}
{% endmacro %}
```

An existing project keeps the date macro it already uses (`type_date()` or its own).

---

## Column order

Eight groups, each opened by a Jinja comment:

1. `{# primary key #}`
2. `{# foreign keys #}`
3. `{# natural keys #}`
4. `{# attributes #}`
5. `{# indexes and ranks #}`
6. `{# metrics #}`
7. `{# booleans #}`
8. `{# temporal #}`

This refines the old six (keys, attributes, indexes/ranks, metrics, booleans, temporal). Splitting the keys shows which ones Wire generated and which came from the source. Jinja comments do not reach the compiled SQL.

---

## Configuration

| Kind | Materialization | Schema |
|---|---|---|
| Base, staging | `view` | `staging` |
| Intermediate, integration | `view` | `integration` |
| Warehouse | `table`; incremental allowed per model | project default |
| Snapshot | `snapshot` | `snapshots` |
| Seed | `table` | `seeds` |

- Directory-wide settings and materialization: `dbt_project.yml`. Developer description, unique key, partitioning, clustering: the model's `config()`. End-user description: the schema file.
- New projects get the `dbt_project.yml` template (layer configs under the real project name, `+persist_docs`, warehouse `+meta` with `required_docs` and `required_tests`, `seeds` and `snapshots` schemas) and a `packages.yml` with `dbt-labs/dbt_utils` (>=1.3.0) and `tnightengale/dbt_meta_testing` (>=0.4.0). See `examples/new-project-dbt_project.yml`.
- Projects that use droughty set `required_docs: false`: droughty writes no model descriptions and rewrites `droughty_schema.yml`, so the check would fail every warehouse model. `required_tests` stays on.
- Existing projects: report differences from the template as suggestions. Never apply them. Correcting the project key can change which models build as tables or views.

---

## Testing (summary)

- Primary keys: `unique` + `not_null`.
- `dbt_utils.at_least_one` is added **alongside** `not_null`, never instead of it. It only checks a column is not entirely empty (which also catches an empty table); `not_null` checks every row.
- `data_tests:` on dbt 1.8+, `tests:` before. Keep `tests:` in a file that already uses it. Never both on one resource.
- `freshness` is the only test in `_sources.yml`.
- `dbt run-operation required_docs` and `required_tests` run only where `packages.yml` has `dbt_meta_testing`.

See `testing-reference.md`.

---

## Documentation (summary)

- Every column in every layer is documented (was warehouse and staging only).
- Model column descriptions live once, as doc blocks in `models/field_descriptions.md`, referenced as `'{{ doc("user_pk") }}'`.
- Source column descriptions are written inline in `_sources.yml`, not as doc blocks.
- `_sources.yml`: one source per `stg_<source>/` directory, named for the directory without `stg_`; `schema` and `loader` set; table `name` is the business name, `identifier` the raw name; table description opens `Grain:`, then `Source table group:` where relevant, says how the table is loaded, and ends `Use it for ...`; every column declared under its source name with meaning, unit, time zone, null meaning and allowed values; identifier columns name where the same value is held elsewhere; "Personal data." on personal data columns; profiled figures dated; loader columns declared. See `examples/sources-example.yml`.

---

## Macros

- One macro per file, `macro__<name>.sql`; utility macros in `macros/utility/`; adapter versions in the same file.
- Each macro described in `macros/_schema_macros.yml` with `name`, `description`, and `arguments` (`name`, `type`, `description`). The entry is updated in the same change as the macro.
- dbt override macros (`generate_schema_name`) keep their dbt names.
- Existing macro files keep their names.

---

## Quick checklist (new or changed model)

- [ ] File name and folder match the kind (plural staging/integration, singular warehouse, unless a ruling says otherwise)
- [ ] `config()` description opens `Grain: One row per ...`
- [ ] Every `ref()` / `source()` in an `s_` CTE at the top
- [ ] Last CTE is `final`; model ends `select * from final`
- [ ] 4-space indentation, lines up to 120
- [ ] Explicit joins, no alias initialisms, `union all`
- [ ] Columns in the eight groups with Jinja comments
- [ ] Entity prefix on every new column, booleans `<entity>_is_`
- [ ] Suffixes: `_pk`, `_fk`, `_natural_key`, `_count`, `_rank`, `_amount`, `_amount_<ccy>`, `_<measure>_<unit>`, `_pct`, `_ratio`, `_dt`, `_ts`
- [ ] Aggregates lead with the function name
- [ ] Attribute strings lowercased; natural keys not
- [ ] Casts through `dbt.type_*()` and the project's date macro
- [ ] PK and FK only in the warehouse, via `dbt_utils.generate_surrogate_key`
- [ ] PK has `unique` + `not_null`; `at_least_one` alongside `not_null`, not instead
- [ ] Project's test key used (`data_tests:` on 1.8+, `tests:` where the file already uses it)
- [ ] Every column has a doc block in `field_descriptions.md`
- [ ] No existing model, column, seed, snapshot or schema renamed or moved

---

## Where Wire differs from the reference

| Topic | Reference | Wire |
|---|---|---|
| Lowercasing | every staging string, natural keys included | attribute strings only |
| Default column test | `dbt_utils.at_least_one` | `at_least_one` alongside `not_null`; PKs keep `unique` + `not_null` |

Both are held until the reference adds the exceptions.
