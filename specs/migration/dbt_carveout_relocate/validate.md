---
wire_schema: "1.0"
command: validate
artifact: dbt_carveout_relocate
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: dbt_carveout_relocate
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate relocated carve-out dbt models — every carve_in model present, predicates independently re-derived from file contents, no bucket misclassification, target compiles
argument-hint: <release-folder> [--wave id | --batch N | --select selector] --target-dbt-project-path <path>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Carveout Relocate — Validate

## Purpose

Validates a `dbt-carveout-relocate-generate` run. Every check re-derives its answer independently from the adjudicated CSV and the files actually on disk under `--target-dbt-project-path` — it does not trust the manifest's (`dbt_carveout_relocate_manifest.md`, or `_{wave_id}.md` under `--wave`) own claims about what it did.

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — same scope this generate run was invoked with; resolved identically (see `dbt-carveout-relocate-generate` Step 1). If omitted, validate every model recorded under `artifacts.dbt_carveout_relocate` in status.md across all prior runs for this release.
- `--target-dbt-project-path <path>` — **required.** The dbt project relocated models were written into.

## Validation Checks

Read `migration/region_tags_adjudicated.csv`, filter to `item_type == "dbt_model" AND adjudicated_ruling == "carve_in"`, intersected with the resolved scope — this is the ground-truth set every check below validates against, independent of what the manifest claims was relocated.

**Check 1 — Every carve_in model resolves to a file that exists**
For every model in the ground-truth set, confirm the corresponding `.sql` file exists under `--target-dbt-project-path` at the expected mirrored path.
PASS: every model has a file. FAIL: list models with no file — a silent drop during relocation.

**Check 2 — Every shared-row-level model actually contains the injected predicate**
For every model in the ground-truth set with `bucket == shared-row-level` whose `predicate_injection` is `injected`, read the relocated `.sql` file directly and independently confirm it contains a `WHERE` clause carrying that model's filter **from its registry row** (`migration/tenant_predicate_registry.csv`, not `migration.tenant_predicate` — from v3.11.3 the filter is per model) on the outermost `SELECT`. Do not read this from the manifest's own claim; re-derive it from the file text. Strip SQL comments before re-deriving, for the same reason generate does: a commented-out filter is not a filter.
PASS: filter confirmed present in the file for every such model. FAIL: list models where the manifest claims injection but the file doesn't show it (or shows it on the wrong query level).

**Check 2b — Inherited models carry no filter, and their resolving node does (v3.11.3)**
For every model whose `predicate_injection` is `not_applicable_inherited`, confirm two things independently of the manifest: the relocated file contains no injected filter, and the registry row's `resolving_node` names an item whose own registry row carries a mechanism other than `unresolved`. Follow `resolving_node` transitively and confirm the chain terminates — an inheritance chain that loops, or that ends at an unresolved node, means the model is unscoped while claiming to be resolved.
PASS: every inherited model's chain terminates at a resolved node. FAIL: name the model, the chain walked, and where it broke.

**Check 2c — Registry completeness and internal consistency (v3.11.3)**
Run the registry-wide checks in `specs/utils/tenant_predicate_registry.md` over `migration/tenant_predicate_registry.csv`: one row per `carve_in` item; expression present exactly for `row_predicate`/`derived_expr`/`account_cascade` and empty for the rest; `inherited` rows resolving to something; no inheritance cycle; `verified_date` accompanied by `provenance`; every non-empty expression well-formed (balanced parentheses, closed quotes, no dangling `{{`, per that spec's well-formedness check, #200).
PASS: all six hold. FAIL: list each violation with its row. A `malformed_expression` violation blocks like the rest (fail, not warn): a truncated expression parses as a valid row while carrying half a rule.

**Check 2d — Derived predicates carry a recorded semantics check (#219)**
For every injected model whose registry row is derived (`resolved_by` other than `adjudication`/`manual`, mechanism with a `tenant_column`), confirm the row records a semantics-check result (the measured `distinct_values`/`tenant_share` figures and a verdict in `provenance`/`notes`, with `verified_date` set) per `specs/utils/tenant_predicate_registry.md`. A row whose recorded verdict is `implausible_zero_share` or `implausible_dispersed` must not have been injected at all.
PASS: every derived injected row carries a recorded `plausible` verdict. FAIL: list rows injected with no recorded check, and any row injected over an implausible verdict (the worse of the two: a filter applied against its own evidence).

**Check 2e — SCD-shaped models carry the entity-grain form (#219)**
Independently re-classify every relocated model against the SCD-shape signals in `specs/utils/tenant_predicate_registry.md` (snapshot materialisation, `dbt_valid_from`/`dbt_valid_to`, a `valid_from`+`valid_to` pair, an `is_current` flag), from the relocated file and its companion YAML, not from the manifest. For every SCD-shaped model with an injected predicate, confirm the injected form is entity grain (a semi-join over the entity key), not the raw row expression.
PASS: every SCD-shaped injected model carries the entity-grain form. FAIL: name each SCD-shaped model carrying a row-grain predicate; a row-grain predicate on a history table truncates version history silently.

**Check 2f — Expected-empty markers present and reasoned (#219)**
For every model the manifest records as `expected_empty: true`, confirm the relocated file's first line is the `-- EXPECTED EMPTY (<tenant>): ...` header and that the header carries a non-empty reason with the measured source figures. Conversely, a file carrying the marker must appear in the manifest's expected-empty list.
PASS: markers and manifest agree, every marker reasoned. FAIL: list models with a missing, reason-less, or manifest-orphaned marker.

**Check 3 — No confident-region model carries an injected predicate**
For every model in the ground-truth set with `bucket == confident-region`, confirm its relocated `.sql` file does **not** contain a `WHERE` clause referencing `migration.tenant_predicate` that wasn't already present in the source file. A predicate showing up on a `confident-region` model indicates a bucket misclassification upstream (in `region-tagging-generate`/`-review`), not something this command should silently accept.
PASS: no unexpected predicate found. FAIL: list models with an unexpected predicate, flagged for region-tagging re-adjudication, not for re-running this command.

**Check 4 — Manual-review-required list is empty, or every entry is explicitly signed off**
Read the manifest's manual-review-required list. For each entry, confirm either it no longer applies (the file has since been hand-edited and Check 2 now passes for it) or `dbt-carveout-relocate-review` recorded an explicit sign-off for that specific model (see that spec's Step 3).
PASS: list is empty, or every entry has a matching sign-off record. FAIL: list any entry with neither.

**Check 4b — Proposed dispositions are not treated as rulings (v3.11.3)**
For every registry row with `resolved_by: row_distribution_probe` and `confidence: medium` (a Rung 4 proposal), confirm `dbt-carveout-relocate-review` recorded a ruling for it. A proposal is evidence for a decision, not the decision, and a model shipped on one has been scoped by a query nobody approved.
PASS: every proposal has a ruling, or there are none. FAIL: list each unruled proposal with its evidence query.

**Check 5 — Target project compiles cleanly**
Run `dbt parse` (or `dbt compile`) against `--target-dbt-project-path` for the ground-truth model set, via the same scratch-directory pattern as generate's Step 4.
PASS: all models compile without errors. FAIL: list compilation errors per model.

**Check 6 — Every sources.yml entry is read by at least one enabled model (#219)**
Parse every `sources.yml` (and any `*.yml` declaring `sources:`) under `--target-dbt-project-path`, and build the set of `source()` references across the project's enabled models (from the compiled manifest, or a comment-stripped scan of the model files). Every declared source table entry must be read by at least one enabled model.
**The rule is fail-on-any: one unread entry fails the check**, with every unread entry listed (`<source_name>.<table_name>`, defining file). A sources.yml copied verbatim from the parent project carries entries no model in the new project reads (547 of 631 on the engagement that motivated this check), and each unread entry is a wrong answer somewhere else: freshness checks on tables the project never uses, lineage that claims reads that do not happen, and data-protection (DPIA) answers derived from a source list that overstates what the project touches. Sources accrue with the models that read them: an entry a later wave will need belongs in that wave's relocation, not copied ahead.
PASS: zero unread entries. FAIL: list every unread entry.
Tests mirror the unread-entry derivation (`wire/tests/platform_migration/validate_carveout_hygiene.py`).

**Check 7 — Every enabled model resolves to an explicitly configured dataset/schema (#219)**
For every enabled model, resolve its target dataset/schema the way dbt does: in-file `{{ config(schema=...) }}`, companion YAML config, or a `+schema` on a configured path in `dbt_project.yml`. Every model must resolve through at least one explicit configuration. A model that falls through to the profile default (typically a model sitting at the project root, outside every configured path) would materialise into a stray default dataset (`_unset` or the profile's own) in the sovereign project.
PASS: every enabled model's dataset/schema traces to an explicit config. FAIL: name each model resolving to the profile default, with its path and the configured paths it falls outside.
Tests mirror the fall-through classification (`wire/tests/platform_migration/validate_carveout_hygiene.py`).

### Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    wave_validate:                # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `validate` as action.
