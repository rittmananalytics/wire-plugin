# dbt Testing Reference

Embedded reference used by the dbt development skill for testing. The authority for people is the `ra_fw_core` dbt development reference (`analytics_warehouse/docs/development_reference_dbt.md`, version 0.0.1). The primary key requirement (`unique` + `not_null`) and the test key are also checked by `wire/conventions/dbt.yml` through `wire/scripts/lint_conventions.py` (see `wire/schemas/convention-schema.md`).

Testing is project specific. Each client project decides its strategy and when tests run, based on its data, warehouse and cost. What follows is what Wire generates by default. Like the other conventions, it applies to new and changed models; existing tests are not rewritten.

---

## Terminology and the test key

dbt calls them **data tests**. Older documents call them schema tests; the two mean the same thing. dbt renamed them to tell them apart from unit tests.

| Situation | Key |
|---|---|
| dbt 1.8 or later | `data_tests:` |
| dbt before 1.8 | `tests:` |
| Schema file that already uses `tests:` | keep `tests:` |
| Project with a `test_key:` ruling in `.wire/conventions/dbt.yml` `form_choices` | the ruling |

Never put both keys on one resource; dbt rejects it. Keeping `tests:` in a file that already uses it means one file reads one way and the diff shows only the real change.

Examples below use `data_tests:`.

---

## Layers and what they test

| Layer | Reads | Holds |
|---|---|---|
| Sources (`_sources.yml`) | raw tables | declarations only; `freshness` is the only test |
| Base | sources | the join or union one source concept needs |
| Staging | sources, snapshots, seeds, base models | one source concept, renamed and cast |
| Intermediate | staging | one concept combined from several sources |
| Integration | staging, intermediate | entities joined across sources, derived fields |
| Warehouse | integration (or staging) | dimensions, facts, extended aggregates; PK and FK created here |

**Why only `freshness` in `_sources.yml`.** A test on raw data fails on problems the project cannot fix in the raw table. Assumptions about data shape are tested on the staging model, where a failure points at the model that holds the assumption.

---

## Generic tests by model type

| Model type | Primary key | Other columns |
|---|---|---|
| Base | (no PK; natural key) | `not_null` where populated in every row, `dbt_utils.at_least_one` |
| Staging | `unique` + `not_null` on the natural key | `not_null`, `dbt_utils.at_least_one`, `accepted_values` |
| Intermediate | `unique` + `not_null` | `not_null`, `dbt_utils.at_least_one`, `accepted_values` |
| Integration | `unique` + `not_null` (or `unique_combination_of_columns`) | `not_null`, `dbt_utils.at_least_one`, `accepted_values` |
| Dimension | `unique` + `not_null` | `not_null`, `dbt_utils.at_least_one`, `relationships` |
| Fact | `unique` + `not_null` | `not_null`, `dbt_utils.at_least_one`, `relationships`, business-logic tests |
| Extended aggregate | `unique` + `not_null` | `not_null`, `dbt_utils.at_least_one` |

### `at_least_one` alongside `not_null`, never instead

- `not_null` asserts every row is populated.
- `dbt_utils.at_least_one` asserts the column is not entirely empty, which also catches an empty table or a column that broke upstream.
- The reference makes `at_least_one` the default column test. Wire adds it **alongside** `not_null` and never removes a `not_null` to make room for it. On its own, `at_least_one` passes a column that is 99% null. Primary keys always keep `unique` + `not_null`.
- On a column that is legitimately null on some rows, `at_least_one` is the right test on its own, because `not_null` would fail.

### Minimum enforcement

New projects set `required_tests: {"unique": 1, "not_null": 1}` under `+meta` on the warehouse layer. Where `packages.yml` has `tnightengale/dbt_meta_testing`:

```bash
dbt run-operation required_tests
dbt run-operation required_docs
```

These do not run as part of `dbt run` or `dbt build`; they run against built models. Skip them where the package is not installed. Projects that use droughty set `required_docs: false` and keep `required_tests` on.

---

## Built-in and dbt_utils tests

**`unique`**, **`not_null`**: required on every primary key.

**`relationships`**: foreign keys.
```yaml
data_tests:
  - relationships:
      to: ref('wh_core__user_dim')
      field: user_pk
```

**`accepted_values`**: enums and status fields. Values are lowercase, because staging lowercases attribute strings.
```yaml
data_tests:
  - accepted_values:
      values: ['visitor', 'trial', 'paying', 'churned']
```

**`dbt_utils.at_least_one`**: column not entirely empty.
```yaml
data_tests:
  - not_null
  - dbt_utils.at_least_one
```

**`dbt_utils.not_null_where`**: conditional not-null.
```yaml
data_tests:
  - dbt_utils.not_null_where:
      where: "subscription_is_paying = true"
```

**`dbt_utils.unique_combination_of_columns`**: uniqueness across columns, for multi-source integration models.
```yaml
data_tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - user_natural_key
        - user_source_system
```

**`dbt_utils.expression_is_true`**: relationships between fields.
```yaml
data_tests:
  - dbt_utils.expression_is_true:
      expression: "subscription_ended_dt >= subscription_started_dt"
```

**`dbt_utils.accepted_range`**: bounds. Useful on `_pct` (0 to 100) and `_ratio` (0 to 1) columns, where a value on the wrong scale is otherwise easy to miss.
```yaml
- name: order_discount_pct
  data_tests:
    - dbt_utils.accepted_range:
        min_value: 0
        max_value: 100
```

---

## Source freshness

`freshness` applies where a source table has a column recording when each row was loaded, set as `loaded_at_field`. `warn_after` and `error_after` are set per client project.

```yaml
tables:
  - name: users
    identifier: user_accounts
    config:
      loaded_at_field: _fivetran_synced
      freshness:
        warn_after: {count: 24, period: hour}
        error_after: {count: 48, period: hour}
```

---

## Schema files

- **With droughty:** `models/droughty_schema.yml` is generated from the warehouse information schema. Do not hand-edit it. Column descriptions come from the doc blocks in `models/field_descriptions.md`.
- **Without droughty:** each new model subdirectory holds a `_schema.yml`. Existing schema file names are kept.
- Source declarations (`_sources.yml`) are always written by hand; droughty does not generate them.

---

## Documentation coverage

- Every column of a base, staging, intermediate, integration and warehouse model is documented.
- Model column descriptions are held once, as doc blocks in `models/field_descriptions.md`, and referenced from schema files. A column that keeps its name across layers uses one doc block.
- Source columns are documented inline in `_sources.yml`.

```markdown
{% docs user_pk %}
The surrogate primary key of the user entity.
{% enddocs %}
```

```yaml
- name: user_pk
  description: '{{ doc("user_pk") }}'
```

---

## Regression tests, singular tests and unit tests

- **Regression tests** live in `analyses/regression_tests/` and run with `dbt compile`. Existing projects that use `analysis/` keep it.
- **Singular data tests** (`tests/*.sql`) and **custom generic tests** are project specific.
- **Unit tests** mock model inputs and assert outputs without querying the warehouse. Which models need one is set by the unit test rule below. For how to write them, see the `dbt-unit-testing` skill (`wire/skills/dbt-unit-testing/SKILL.md`).

---

## Unit test rule

This is the one statement of which dbt models need a unit test. The `dbt-unit-testing` skill and `/wire:data_quality-generate` refer to it. Change it here only.

| Layer | Model names | Rule |
|---|---|---|
| Staging | `stg_`, `base_` | **Recommended** when the model has non-trivial logic: parsing, casting with rules, CASE logic. Not required. |
| Integration | `int_` (integration and intermediate models) | **Required** when the model has business logic, including entity resolution, matching, deduplication, merging sources, or derived business flags. |
| Warehouse | `wh_..._dim`, `wh_..._fact`, `wh_..._xa` (and the older `wh_..._agg`) | **Required** on every dimension and fact with business logic: derived columns, joins that apply rules, aggregations with rules. Pure pass-through columns need no unit test. |

A model's layer comes from its name prefix. If the name matches no prefix (an older project), the folder decides: `models/staging/`, `models/integration/` or `models/warehouse/`. If neither does, the layer is not recognised and the model is listed for the consultant to classify.

### Business logic signals

A model has business logic when its SQL (compiled SQL where `target/compiled/` exists, else the model file, with comments removed) shows any of these signals:

| Signal | What it looks like |
|---|---|
| `conditional` | `CASE`, `IF(`, `IFF(` |
| `window` | a window function: `... OVER (` |
| `regex` | `REGEXP_...(` functions |
| `parsing` | parsing or casting with rules: `PARSE_...(`, `JSON_...(`, `SPLIT(`, `SAFE_CAST(`, `TRY_CAST(`, `TRY_TO_...(`, `TO_DATE(` or `TO_TIMESTAMP(` with a format |
| `date_logic` | date arithmetic and boundaries: `DATE_DIFF`, `DATETIME_DIFF`, `TIMESTAMP_DIFF`, `DATEDIFF`, `DATE_ADD`, `DATE_SUB`, `DATEADD`, `DATE_TRUNC`, `LAST_DAY` |
| `deduplication` | `SELECT DISTINCT`, `QUALIFY` |
| `merge_sources` | `UNION`, or the `merge_sources` macro |
| `conditional_aggregation` | an aggregate over a condition: `SUM(CASE ...)`, `COUNT(IF(...))`, `COUNTIF`, `SUMIF`, `COUNT_IF`, `FILTER (WHERE` |
| `rule_join` | a join whose `ON` condition has more than key equality: `<`, `>`, `!=`, `<>`, `BETWEEN`, `LIKE`, `OR`, or a function call |
| `derived_column` | a selected column computed with arithmetic (`+`, `-`, `*`, `/`) |
| `derived_flag` | a boolean-named column (`is_`, `has_`, `was_` at the start or after the entity prefix) set from an expression rather than a plain column |

Not signals on their own: renames, plain `CAST`, `TRIM`, `LOWER`, `UPPER`, joins on key equality, `SELECT *`.

Not decided by this rule: a plain aggregation (`GROUP BY` with `SUM` or `COUNT` and no condition), `COALESCE` or `IFNULL`, and a call to a project macro other than `ref`, `source`, `config`, `var` or `merge_sources` (its logic is not visible in the model file). On an integration or warehouse model with none of the signals above, these mark the model **check by hand**: the consultant decides and records the decision.

### Outcome per model

| Layer | Signals found | Outcome | Gap when no `unit_tests:` block |
|---|---|---|---|
| Staging | yes | Recommended | Advisory |
| Staging | no | None | None |
| Integration or warehouse | yes | Required | Required (must be resolved or tracked) |
| Integration or warehouse | no, but a check-by-hand marker | Check by hand | Check by hand |
| Integration or warehouse | no | None (pass-through) | None |
| Not recognised | any | Classify by hand | Classify by hand |

The test `wire/tests/misc_release_types/validate_unit_test_rule.py` holds this classification as code and checks it against fixture models.

---

## Running tests

Prefer `dbt build`, which runs models and their tests in dependency order and stops downstream models when a test fails:

```bash
dbt build --select staging
dbt build --select integration
dbt build --select warehouse
```

Where the client project has a `selectors.yml`, use its named runs: `dbt build --selector <name>`. A common one builds warehouse models and runs only their primary-key `unique` tests, to keep warehouse cost down.

---

## Severity

```yaml
data_tests:
  - unique:
      config:
        severity: warn
```

- Primary key tests: always `error`.
- Foreign key tests: usually `error`.
- `at_least_one`: `error`; an empty column is a broken load or model.
- Optional fields and nice-to-have checks: `warn`.

---

## Patterns

### Dimension
```yaml
models:
  - name: wh_core__user_dim
    description: >
      Grain: One row per user.
      The user dimension.
    columns:
      - name: user_pk
        description: '{{ doc("user_pk") }}'
        data_tests:
          - unique
          - not_null

      - name: account_fk
        description: '{{ doc("account_fk") }}'
        data_tests:
          - relationships:
              to: ref('wh_core__account_dim')
              field: account_pk

      - name: user_natural_key
        description: '{{ doc("user_natural_key") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one

      - name: user_status
        description: '{{ doc("user_status") }}'
        data_tests:
          - accepted_values:
              values: ['active', 'inactive', 'suspended']

      - name: user_created_ts
        description: '{{ doc("user_created_ts") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
```

### Fact
```yaml
models:
  - name: wh_core__transaction_fact
    description: >
      Grain: One row per transaction.
      Completed payment transactions.
    columns:
      - name: transaction_pk
        description: '{{ doc("transaction_pk") }}'
        data_tests:
          - unique
          - not_null

      - name: user_fk
        description: '{{ doc("user_fk") }}'
        data_tests:
          - not_null
          - relationships:
              to: ref('wh_core__user_dim')
              field: user_pk

      - name: transaction_amount
        description: '{{ doc("transaction_amount") }}'
        data_tests:
          - not_null
          - dbt_utils.at_least_one
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: transaction_ts
        description: '{{ doc("transaction_ts") }}'
        data_tests:
          - not_null
```

### Integration model, several sources
```yaml
models:
  - name: int_core__users
    description: >
      Grain: One row per user per source system.
      Users from Salesforce and Stripe.
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - user_natural_key
            - user_source_system
    columns:
      - name: user_natural_key
        description: '{{ doc("user_natural_key") }}'
        data_tests:
          - not_null

      - name: user_source_system
        description: '{{ doc("user_source_system") }}'
        data_tests:
          - not_null
          - accepted_values:
              values: ['salesforce', 'stripe']
```

---

## Testing checklist (new or changed model)

- [ ] Schema entry exists (`_schema.yml`, the existing schema file, or droughty regenerated)
- [ ] Primary key has `unique` and `not_null`
- [ ] Columns populated on every row have `not_null`
- [ ] `dbt_utils.at_least_one` added alongside `not_null`, not in place of it
- [ ] Foreign keys have `relationships`
- [ ] Enum and status fields have `accepted_values`, lowercase
- [ ] `_pct` and `_ratio` columns bounded where useful
- [ ] Multi-source integration models use `unique_combination_of_columns`
- [ ] Test key matches the dbt version, the file, and any ruling
- [ ] Every column has a doc block in `field_descriptions.md`
- [ ] Source tables declared with `freshness` where a load timestamp exists
- [ ] Regression tests updated if logic changed
- [ ] `dbt build` passes; `required_tests` / `required_docs` pass where `dbt_meta_testing` is installed

---

## Troubleshooting failed tests

### `unique`
Cause: duplicate values. Often a grain that differs from the `Grain:` line.
```sql
select
    field_name,
    count(*) as row_count
from {{ ref('model_name') }}
group by field_name
having count(*) > 1
```

### `not_null`
Cause: null values.
```sql
select *
from {{ ref('model_name') }}
where field_name is null
limit 100
```

### `at_least_one`
Cause: the column is null on every row, or the model is empty. Check the upstream model and the source freshness first.

### `relationships`
Cause: foreign key values missing from the referenced table.
```sql
select distinct child_model.fk_field
from {{ ref('child_model') }} as child_model
left join {{ ref('parent_model') }} as parent_model
    on child_model.fk_field = parent_model.pk_field
where parent_model.pk_field is null
```

### `accepted_values`
Cause: values outside the list. Check for upper-case values that staging should have lowercased.
```sql
select distinct field_name
from {{ ref('model_name') }}
where field_name not in ('value1', 'value2', 'value3')
```
