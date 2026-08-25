---
description: Per-item tenant-predicate registry for carve-out releases — the five resolution mechanisms, the seed from region tagging, the read contract for equivalency/bulk-copy/relocate/defer-build, the CSV write contract and expression well-formedness check (#200), and the rule that an unresolved item is flagged rather than compared unfiltered
---

# Utils — Tenant Predicate Registry

A shared data contract, not a command. Written by `region-tagging-generate` (the seed) and `dbt-carveout-relocate-generate` (resolutions and provenance); read by `equivalency-validate`, `bulk-copy-migration-generate`, `dbt-carveout-relocate-generate`, and `dbt-migration-defer-build`'s tenant boundary guard.

## Why a registry and not one string

`migration.tenant_predicate` is a single string, and a carve-out needs more than one. One engagement's carve-out needed five resolution mechanisms at once, on the same release: a plain row predicate on most Silver/Gold models, a differently-named tenant column on a handful of globalised models, an object-level schema-prefix carve on the Bronze layer where no row predicate exists at all, a hardcoded id list in an advertising account column, and a derived expression over a composite key. Pinning that variety as prose inside one config field means every consumer re-parses it and gets a different answer.

The registry resolves one item at a time. `migration.tenant_predicate` stays, and its role narrows: it is the **default row predicate** used when seeding a row, never the thing a consumer reads directly.

## Location and schema

`.wire/releases/<release>/migration/tenant_predicate_registry.csv`. Template: `TEMPLATES/migration/tenant_predicate_registry.csv`.

| Column | Meaning |
|---|---|
| `item_id` | Model, table, or view name — matches `region_tags_adjudicated.csv`'s `item_id` |
| `item_type` | `dbt_model` \| `table` \| `view` \| `reverse_etl_sync` \| `metabase_card` \| `metabase_dashboard` (#184) |
| `mechanism` | One of the five below, or `unresolved` |
| `expression` | The filter text, in target dialect. Empty for `object_carve`, `inherited`, and `unresolved` |
| `tenant_column` | The column the expression filters on, where there is one. Empty for `object_carve` and `inherited` |
| `resolved_by` | How the row reached its current state (below) |
| `resolving_node` | For `inherited`, the upstream item whose predicate covers this one. Empty otherwise |
| `provenance` | Free text: the adjudication note, the evidence query, or the rule id that produced it |
| `verified_date` | ISO date the mechanism was last confirmed against live data or a human ruling. Empty when never verified |
| `confidence` | `high` \| `medium` \| `low` — how strongly the provenance supports the mechanism |
| `notes` | Anything a reader needs that the columns above don't carry |

## The write contract (CSV quoting, #200)

Every writer of the registry emits rows through a CSV writer, never by string concatenation. Per RFC 4180: a field containing a comma, a double quote, or a newline is wrapped in double quotes, and each double quote inside the field is doubled. The rule applies to every column; `expression` and `provenance` are the ones that need it in practice, because a semi-join (`customer_id IN (SELECT id FROM {{ ref('account_history') }})`) and a regex predicate (`REGEXP_CONTAINS(descriptive_name, r'(?i)acme, inc')`) both carry commas.

The rule exists because 3.11.x writers concatenated fields and truncated every comma-bearing expression at its first comma: 18 of 88 wave-1 models on one engagement stored half a rule (a semi-join cut mid-subquery, an unterminated regex). The truncated rows kept the right column count, so schema checks passed, and every consumer that trusted the stored expression inherited a broken filter. It was caught only when a post-merge verification re-derived the predicates from merged model SQL.

The writers (`region-tagging-generate` Step 5b, `dbt-carveout-relocate-generate` Step 2c, `/wire:upgrade` Step 6a) reference this section rather than restating it.

## Expression well-formedness (#200)

A stored `expression` must parse superficially before any consumer applies it. The check is deterministic and dialect-agnostic: it catches a truncated or corrupted rule, not a wrong one. It applies to every **non-empty** `expression`; an empty expression is out of its scope (registry-wide check 2 below governs which mechanisms may leave the field empty).

Scan the expression left to right:

1. A single quote (`'`) opens a string; the next single quote closes it. Likewise for double quotes (`"`). Inside a string nothing else counts: parentheses, commas, braces, and the other quote character are literal. SQL's doubled-quote escape (`''` inside a string) balances under this rule, because each quote toggles the state. A backslash is **not** an escape: an expression that relies on `\'` to embed a quote is flagged; write it with the doubled-quote form instead. Still inside a string at the end: `unclosed_quote`.
2. Outside a string, `(` opens a group and `)` closes one. A `)` with nothing open, or an unclosed `(` at the end: `unbalanced_parens`.
3. Outside a string, `{{` opens a Jinja expression and `}}` closes one. A dangling `{{` at the end, or a `}}` with nothing open: `unbalanced_jinja`.

A failing expression **blocks**: the consuming validate fails, it does not warn. Verdict-writing consumers record verdict `fail`, reason `malformed_expression`, naming the item and the violation. A malformed expression is half a rule: applying it as written errors at best, and repairing it by guesswork compares or copies a row set nobody ruled on. The fix belongs at the writer: re-derive the expression (the resolution ladder, or a ruling) and re-write the row under the write contract above.

Tests implement this check literally (`wire/tests/platform_migration/validate_tenant_predicate_registry.py`).

## Predicate semantics check (#219)

A well-formed expression can still filter on a column that does not mean tenant. On one carve-out, a predicate on a column named like a tenant column actually filtered the install geography of a global app: 231 distinct ISO codes, tenant share zero. It parsed, compiled, passed lint, dbt tests, and the pre-raise equivalency run, because it silently changed the measure's meaning rather than breaking anything. Only the column's value distribution shows the problem.

**Scope.** Every row whose mechanism carries a `tenant_column` (`row_predicate`, `derived_expr`, `account_cascade`) and whose `resolved_by` is anything other than `adjudication` or `manual`. These are the derived rows: no human has confirmed the column means tenant. Adjudicated and manual rows are exempt; the ruling is the confirmation.

**The check.** Before a consumer applies a derived expression for the first time (for `dbt-carveout-relocate-generate`, before injection), measure the predicate column on the source relation:

- `distinct_values` = `COUNT(DISTINCT <tenant_column>)`
- `tenant_share` = rows the expression keeps, divided by total rows

**Plausibility rule (deterministic; tests mirror it: `wire/tests/platform_migration/validate_carveout_hygiene.py`).**

| Condition | Verdict |
|---|---|
| `tenant_share` = 0 (the expression keeps no rows) | `implausible_zero_share` |
| `distinct_values` >= 100 **and** `tenant_share` < 1% | `implausible_dispersed` |
| Otherwise | `plausible` |

The thresholds are framework defaults, stated here so every consumer applies the same rule. A column with 100 or more distinct values and under 1% tenant concentration reads as an open domain (a geography, a currency, a category), not a tenant marker. The boundaries are inclusive as written: exactly 100 distinct values at exactly 1% share is `plausible`.

**Recording.** Write the measured figures and the verdict into the row: append `semantics_check: distinct=<N>, tenant_share=<P>%, verdict=<verdict>` to `provenance` (or `notes` where `provenance` already carries a ruling), and set `verified_date` to the check date. Re-run the check whenever the row's `expression` or `tenant_column` changes.

**Routing.** A `plausible` verdict lets the consumer proceed. An implausible verdict blocks: the expression is never applied, and `dbt-carveout-relocate-generate` routes the model to `manual_review_required` with reason `predicate_semantics_implausible`. Do not confuse this with an expected-empty model: `implausible_zero_share` on a dispersed or foreign-domain column questions whether the column means tenant at all; a plausible tenant column that keeps zero rows in one specific model is the expected-empty case (`dbt-carveout-relocate-generate`, expected-empty markers), which ships with a recorded reason rather than a filter doubt.

## Predicate grain: row vs entity (#219)

Two grains, and the registry vocabulary for both:

- **Row grain** — the expression evaluates per row: `WHERE <expression>`. Correct for event and transaction tables, where each row's tenant membership is its own fact.
- **Entity grain** — tenant membership is decided per entity, and every version of a tenant entity is kept together: `<entity_key> IN (SELECT DISTINCT <entity_key> FROM <relation> WHERE <expression>)`. The entity key comes from the model's `unique_key`/snapshot config, or the registry row's `notes`.

**SCD-shape detection (deterministic; tests mirror it: `wire/tests/platform_migration/validate_carveout_hygiene.py`).** A model is SCD/history-shaped when any of these holds:

1. Materialised as `snapshot`.
2. Columns include `dbt_valid_from` or `dbt_valid_to`.
3. Columns include both `valid_from` and `valid_to` (one alone is not the pair).
4. Columns include an `is_current` flag.

**The rule.** An SCD/history-shaped model takes its predicate at entity grain, never row grain. A row-grain predicate on a history table truncates an entity's version history with no NULL to signal it: on live data where every version happens to carry the tenant value the two forms are row-identical, so no data comparison sees the difference, and the defect is latent until a version differs. Corollary for children: a child model whose predicate relies on a parent's nullable rollup drops rows behind dangling keys, so a predicate on a nullable parent-derived column must handle NULL explicitly (`IS NULL` branch or `COALESCE`), never bare equality.

Consumers: `dbt-carveout-relocate-generate` (the ladder injects the entity-grain form for SCD-shaped models), `dbt-carveout-relocate-validate` (re-derives the shape and the grain from the relocated file), and `dbt-migration-lint` (static rules `SCD_ROW_GRAIN_PREDICATE` and `NULLABLE_ROLLUP_PREDICATE`, which catch the class on any migration, carve-out or not).

## The five mechanisms

| `mechanism` | What it means | `expression` example | Row filter a consumer applies |
|---|---|---|---|
| `row_predicate` | A boolean over a column present in the object | `country = 'DE'` | `WHERE country = 'DE'` |
| `derived_expr` | The tenant is only recoverable by an expression over a column, not by equality on it | `LEFT(group_id, 2) = 'DE'` | `WHERE LEFT(group_id, 2) = 'DE'` |
| `account_cascade` | The tenant is identified by an enumerated id set in an account/id column, typically because the upstream platform carries no market column at all | `ad_account_id IN (1234567890, 1234567891)` | `WHERE ad_account_id IN (...)` |
| `object_carve` | No row predicate exists. The whole object is in or out of the carve-out by name or schema convention (a `DE_*` schema prefix, a region-dedicated landing dataset) | *(empty)* | **None.** The object is wholly in scope; compare or copy it whole |
| `inherited` | The object carries no tenant column of its own, and its entire upstream path is already scoped. `resolving_node` names the upstream that carries the predicate | *(empty)* | **None.** Its rows are tenant-only on both sides already |

A sixth value, `unresolved`, is not a mechanism: it records that no mechanism has been established. See **The unresolved rule** below.

## `resolved_by` values

| Value | Written by | Meaning |
|---|---|---|
| `global_default` | `region-tagging-generate` seed | `mechanism: row_predicate`, expression taken from `migration.tenant_predicate` |
| `object_signal` | `region-tagging-generate` seed | Classified `object_carve` from the object-level region signal that put the item in `confident-region` |
| `adjudication` | `region-tagging-review` | A human ruled the mechanism at the adjudication gate |
| `alias_resolution` | `dbt-carveout-relocate-generate` | The tenant column was a SELECT-list alias; the expression is the alias's defining expression |
| `row_distribution_probe` | `dbt-carveout-relocate-generate` | Established (or proposed) by a live row-count-by-column check |
| `upstream_inheritance` | `dbt-carveout-relocate-generate` | Resolved by graph traversal to a covered upstream; `resolving_node` is set |
| `manual` | A person, by hand | Hand-edited. Never overwritten by a re-run |

A re-run may upgrade a row from `unresolved` to a mechanism, and may replace a `global_default` seed with something more specific. It must never overwrite a row whose `resolved_by` is `adjudication` or `manual` — those are rulings, and a command that silently reverses a ruling is worse than one that stops.

## The seed (written by `region-tagging-generate`)

After bucket classification, emit one registry row per classified item:

| Bucket | Seeded `mechanism` | `resolved_by` | `confidence` |
|---|---|---|---|
| `confident-region` | `object_carve` | `object_signal` | `high` when the signal was name-suffix or destination; `medium` for `grant-scope` |
| `shared-row-level`, and the item carries the column `migration.tenant_predicate` filters on | `row_predicate`, expression = `migration.tenant_predicate` | `global_default` | `medium` — a default, not a verified fit |
| `shared-row-level`, and it does not carry that column | `unresolved` | *(empty)* | `low` |
| `global-deferred` | `unresolved` | *(empty)* | `low` |

The seed is a starting position, not an answer: every `medium`/`low` row is in the adjudication pile already.

## The read contract (consumers)

A consumer resolves one item as follows, and this order is the whole contract:

1. Read the item's registry row. If `mechanism` is one of the five, apply the row filter from the mechanism table above.
2. No row for the item, or `mechanism: unresolved` → **flag it.** Do not fall back to `migration.tenant_predicate`, and do not proceed unfiltered.
3. `mechanism: object_carve` or `inherited` → apply no row filter, and record in the output which of the two it was. The absence of a filter here is a resolved answer, not a missing one, and the two are not interchangeable in a report.

Tests mirror this resolution (`wire/tests/platform_migration/validate_tenant_predicate_registry.py`).

## The unresolved rule

An item with no established mechanism is **flagged, never compared or copied unfiltered.** Unfiltered is the one wrong answer that looks like a pass: a source-side query with no tenant filter returns every tenant's rows, so a row-count comparison against a single-tenant target fails for a reason that has nothing to do with the migration, and a bulk copy of it moves other tenants' data into the tenant's project — a residency incident, not a test failure.

Per consumer:

- `equivalency-validate` — verdict `fail`, reason `unresolved_predicate`, naming the item and that no registry mechanism exists. Not `diff_*`: nothing was compared, so there is no divergence to classify.
- `bulk-copy-migration-generate` — refuse to emit a copy step for the item. The runbook lists it under unresolved items with the registry row's state.
- `dbt-carveout-relocate-generate` — `predicate_injection: manual_review_required`, after the resolution pass in that spec has had its attempt.
- `dbt-migration-defer-build` — the tenant boundary guard has nothing to check the model's scoping against, so the model is dropped from the build set and reported, not built.

## Registry-wide checks

Any consumer, and `dbt-carveout-relocate-validate`, may assert these cheaply:

1. Every `carve_in` item in `region_tags_adjudicated.csv` has exactly one registry row.
2. `row_predicate`, `derived_expr`, and `account_cascade` rows have a non-empty `expression`; `object_carve`, `inherited`, and `unresolved` rows have an empty one.
3. Every `inherited` row's `resolving_node` names an item that exists in the registry and is not itself `unresolved` — an inheritance chain must terminate in something resolved.
4. No `inherited` cycle: following `resolving_node` from any row terminates.
5. Every row with `verified_date` set also has a non-empty `provenance`.
6. Every non-empty `expression` passes the well-formedness check above (`malformed_expression` otherwise). This one blocks in every consuming validate: fail, not warn.
