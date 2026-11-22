---
wire_schema: "1.0"
command: generate
artifact: bi_migration_plan
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: document
    path: "migration/bi_migration_plan.md"
    description: "Usage-ranked inventory, the director's rulings, PDT disposition, permission map, topic architecture, parallel-run window and batches"
  - type: report
    path: "migration/bi_migration_batches.csv"
    description: "One row per in-scope object with its batch, kind, usage rank, ruling and batch dependency"
  - type: report
    path: "migration/migration_register.csv"
    description: "Register bootstrapped with one pending row per in-scope BI object"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Build the Looker to Omni migration plan: rank content by usage, capture the director's rulings, set PDT disposition and permission mapping, cut model and content batches, bootstrap the register"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding. The gate resolves this command's preconditions from `release-types/bi_migration.yaml`: `looker_audit` review approved (blocking), `business_rules` review approved (advisory), `omni_audit` review approved (advisory). An advisory gate that is unmet asks for a skip reason, or reads one already recorded as a ruling in `decisions.md`, and continues.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: bi_migration_plan` and `artifact_file_path: migration/bi_migration_plan.md` before proceeding.

---

# BI Migration Plan: Generate

## Purpose

Turns the approved Looker audit into a plan the rest of the release executes: which content moves, in what order, under what ruling, and what the Omni model will look like. It replaces three warehouse-migration artifacts (`migration_inventory`, `migration_strategy`, `migration_batching`) with one, because a BI migration has fewer object types and the decisions belong together.

Five things happen here:

1. **Rank by usage.** Dashboards and Looks are ranked by `views_90d`. The plan records the set that carries 80% of views (the Omni migration guide's observation: 20% of content gets 80% of use) and the set with no views in the stale window.
2. **Capture rulings.** The release director decides, per dashboard tier, parity or redesign; what to drop; what happens to each PDT; how Looker groups and user attributes map to Omni; the topic architecture; the parallel-run window; the parity scope. A ruling that has not been made is written as a parked decision, never guessed.
3. **Cut batches.** Model batches follow explore dependency order (a topic's views before the topic). Content batches follow usage rank, highest first. A content batch depends on the model batch that carries every explore its dashboards reference.
4. **Bootstrap the register.** One `pending` row per in-scope object in `migration/migration_register.csv`, so every downstream command has a row to advance.
5. **Write the plan** as one document plus the batches CSV.

## Prerequisites

- `looker_audit review: approved`
- `business_rules review: approved` if the business rules phase was run (advisory: skipping is allowed with a recorded reason)
- `omni_audit review: approved` if the target Omni instance already holds content (advisory)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/omni_audit.md` (if present: existing Omni topics and content to reuse or avoid colliding with)
- `.wire/releases/$ARGUMENTS/artifacts/business_rules.yaml` (if present: agreed metric definitions the Omni measures must implement)
- `.wire/releases/$ARGUMENTS/decisions.md` (rulings already recorded)
- `.wire/releases/$ARGUMENTS/status.md` (`bi_migration.stale_after_days`, `bi_migration.parallel_run_days`, `bi_migration.parity_scope`)
- `wire/bi_pairs/looker_to_omni/translation_guide.md` and `content_mapping.md`

## Pair: tableau_to_looker

This pair is experimental (see `specs/migration/tableau_audit/generate.md`).

When `bi_pair: tableau_to_looker`, the gate resolves this command's preconditions from the profile: `tableau_audit` review approved (blocking), `business_rules` review approved (advisory). The workflow applies with these differences:

- **Inputs.** `audit/tableau_audit.md`, `audit/bi_model_catalog.csv`, `audit/bi_content_catalog.csv`, `audit/datasource_fingerprints.csv`.
- **Step 3 (rulings).** Add a **data source consolidation** ruling per fingerprint group ("Build one shared explore for these N embedded data sources?", default: yes for groups of two or more) and an **extract disposition** per extract-backed data source ("Rebuild as a dbt model, read the warehouse live, or drop?", no default). LOD expressions and table calculations take a per-field ruling (derived table, Looker table calculation, or drop).
- **Step 5 (batches).** Model batches are fingerprint groups in dependency order; content batches are Tableau dashboards by usage, each depending on the model batches of the data sources its sheets use.
- **Step 6 (register).** Identities from the audit (`tableau:<site>:workbook:<luid>`, `.../sheet:<name>`, `.../dashboard:<name>`, `tableau:<site>:datasource:<luid>`); `source_updated_at` from `inventory.json` `updated_at` (or the SHA-256 in files mode); no `last_migrated_commit`.
- **Step 6b (baseline).** Record the snapshot (`exported_at`, edition, API version, SHA-256 per object) in place of `lookml_commit`, and the converter version from `twb_to_lookml.py`.

## Pair: metabase_to_looker

This pair is experimental (see `specs/migration/metabase_source_audit/generate.md`).

When `bi_pair: metabase_to_looker`, the gate resolves this command's preconditions from the profile: `metabase_source_audit` review approved (blocking), `business_rules` review approved (advisory). The workflow applies with these differences:

- **Inputs.** `audit/metabase_source_audit.md`, `audit/bi_model_catalog.csv`, `audit/bi_content_catalog.csv`, `audit/needs_human.json`.
- **Step 3 (rulings).** A **SQL view** ruling per native SQL question and model ("Remodel onto shared views, or keep as a view on its SQL?", default: keep for models used by one question, remodel otherwise), a **lift** ruling per native question the converter lifted ("Keep the lifted fields on the table's view?"), and a per-question ruling for every question not converted (binning by number of bins: choose a width; multi-stage questions: derived table or drop). Content on a database Looker cannot connect to (Metabase's Sample Database) is ruled drop or move.
- **Step 5 (batches).** Model batches are Metabase databases (one connection per LookML model); content batches are dashboards by view count, each depending on the model batch of its database.
- **Step 6 (register).** Identities from the audit (`metabase:<instance>:card:<id>`, `metabase:<instance>:dashboard:<id>`, `metabase:<instance>:table:<id>`); `source_updated_at` from `inventory.json` `updated_at`; no `last_migrated_commit`.
- **Step 6b (baseline).** Record the snapshot (`exported_at`, Metabase version, SHA-256 per object) in place of `lookml_commit`, and the converter version from `mb_to_lookml.py`.

## Pair: omni_to_looker

This pair is experimental (see `specs/migration/omni_source_audit/generate.md`).

When `bi_pair: omni_to_looker`, the gate resolves this command's preconditions from the profile: `omni_source_audit` review approved (blocking), `business_rules` review approved (advisory). The workflow applies with these differences:

- **Inputs.** `audit/omni_source_audit.md`, `audit/bi_model_catalog.csv`, `audit/bi_content_catalog.csv`, `audit/needs_human.json`.
- **Step 3 (rulings).** A ruling per tile on a workbook-only field (move the field into the shared model before the snapshot, or rebuild in Looker), per query view built from a topic query and per view with Mustache in its SQL (native derived table, Liquid rewrite, or a dbt model), per topic default filter (an `always_filter`, or nothing), and per SQL tile (a view on its SQL, or rebuild on an explore).
- **Step 5 (batches).** Model batches are groups of topics with the views they join; content batches are dashboards by visits, each depending on the model batch of the topics its tiles query.
- **Step 6 (register).** Identities from the audit (`omni:<instance>:view:<name>`, `omni:<instance>:topic:<name>`, `omni:<instance>:document:<id>`, `.../query:<key>`); `source_updated_at` from `inventory.json` `updated_at` for documents and the SHA-256 for model files; no `last_migrated_commit`.
- **Step 6b (baseline).** Record the snapshot (`exported_at`, Omni CLI version, model id, SHA-256 per object) in place of `lookml_commit`, and the converter version from `omni_to_lookml.py`.

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. The preconditions, inputs, rulings, batches and register identities are those of `tableau_to_looker` and `metabase_to_looker` above, with Omni as the target and these differences:

- **Rulings.** Name the Omni alternative in each ruling: an LOD expression becomes a query view or is dropped, a table calculation becomes an Omni table calculation on the tile or is dropped, a parameter becomes an Omni templated filter or a dashboard control. Add a **view naming** ruling: the prefix for every view and topic (`--prefix`, default none) and the binding (`--bind query`, the default, files each view as a query view so it cannot collide with Omni's generated schema view; `--bind schema` uses `schema` and `table_name`).
- **Baseline.** Record the converter versions of the reader (`twb_to_lookml.py` or `mb_to_lookml.py`) and of `bi_to_omni.py`.

## Pair: looker_studio_to_looker

This pair is experimental (see `specs/migration/looker_studio_audit/generate.md`). The preconditions, inputs and rulings are those of `looker_studio_to_omni` below, with Looker as the target, and these differences:

- **Model route.** Charts on BigQuery tables and custom SQL convert to LookML views; charts on Looker Studio's Looker connector point at the existing Looker explore and need no model work. Rule each data source: convert, rebuild on the warehouse model (a linked `dbt_development` release), or drop.
- **Rulings.** Add a ruling per blend (the join keys and grain for an explore, or drop) and per chart whose own date range ends today (accept Looker's nearest filter, or add a filter on the date).
- **Batches and baseline.** Model batches are report families; record the converter version from `ls_to_lookml.py` in the baseline.

## Pair: looker_studio_to_omni

This pair is experimental in 4.2.2 (see `specs/migration/looker_studio_audit/generate.md`).

When `bi_pair: looker_studio_to_omni`, the gate resolves this command's preconditions from the profile: `looker_studio_audit` review approved and `metric_catalogue` review approved (blocking), `business_rules` review approved (advisory). The workflow below applies with these differences, step by step:

- **Inputs.** Read `audit/looker_studio_audit.md`, `audit/looker_studio/content_catalog.csv`, `audit/looker_studio/datasource_catalog.csv` and the ruled `audit/metric_catalogue.csv` in place of the Looker catalogs. A `conflict` still parked in the catalogue stops the plan: the model has nothing agreed to build.
- **Step 2 (usage).** Rank reports by Route A job counts per report (`jobs` summed over its components). With `usage_source: unavailable`, park the ranking decision as for Looker.
- **Step 3 (rulings).** Add two rulings: "Merge each report family into one Omni dashboard with a filter (families listed)?" (default: merge) and "Carry hidden pages?" (default: no).
- **Step 4 (model scope and route).** Group the in-scope data sources into subject areas (one per business process: paid media, web analytics, ecommerce, email and so on). For each subject area record a **model route**:
  - `map`: every data source is `map` (or `assisted` custom SQL) and the warehouse already has modelled tables for it, and the metric catalogue's rulings can be written as measures over those tables. The Omni model is built directly.
  - `build`: the warehouse has no model for it, or the source tables are wide per-source exports that need reshaping (one column per source and metric). Spawn a linked `dbt_development` release with `/wire:release-spawn`, scoped to that subject area, with the metric catalogue as its business rules. The model batch for that subject area depends on that release's warehouse models passing validation.
  - Every `pipeline` data source is listed as a **pipeline task** (what must land in the warehouse, and where) with an owner. Its charts stay `blocked_by: pipeline` until the task closes; they are not parity gaps found at the end.
- **Step 5 (batches).** Model batches are subject areas in dependency order. Content batches are report families, highest usage first; each depends on the model batches its data sources map to.
- **Step 6 (register).** Register rows use the audit's identities: `report:<id>`, `page:<report_id>/<page_id>`, `component:<report_id>/<component_id>`, `datasource:<id>`, with `source_layer` `lookerstudio_content` or `lookerstudio_datasource`, and `source_updated_at` from the report's `modified_date`. There is no `last_migrated_commit`.
- **Step 6b (baseline).** Record the captures in place of `lookml_commit`: per report, `captured_at`, `app_version` and revision read; the extractor, catalog and metrics script versions; and `parity_as_of` set to the latest capture time, because Route C recordings are the expected results and they reflect the data at capture.


### Step 1: Load the audit and existing rulings

Read both catalogs and the audit report. Read `decisions.md` and collect every ruling whose `Applies to:` line names `bi_migration_plan` or one of the ruling kinds in Step 3. Read `bi_migration.stale_after_days` (default 180) and `bi_migration.parity_scope` (default `prioritised`) from `status.md`.

### Step 2: Rank content by usage

For every `dashboard` and `look` row:

- Sort by `views_90d` descending. Assign `usage_rank` (1 = most viewed). Rows with `views_90d: unknown` sort last and carry `usage_rank: unknown`.
- Compute the cumulative share of views. Mark the smallest set of rows that reaches 80% of total views as **tier 1**. The remainder with any views in the window is **tier 2**. Rows with zero views and `last_viewed` older than `stale_after_days` are **stale**.
- Record in the plan: tier 1 count and share, tier 2 count, stale count, unknown count.

If `usage_source: unavailable` in `status.md`, every row is `usage_rank: unknown`, no tiers can be computed, and the plan records a parked decision: "Usage is unavailable. Rank by hand, or accept all content as tier 1."

### Step 3: Capture the director's rulings

Each ruling below is read from `decisions.md` if present. If absent, write a `parked_decisions` entry in `status.md` (kind `ruling`, artifact `bi_migration_plan`, the question as worded here) and record `ruling: parked` in the plan. Do not invent a default for any of them except where a default is stated.

| Ruling | Question | Default |
|---|---|---|
| Parity or redesign, per tier | "Tier 1: rebuild each dashboard as-is in Omni (parity), or redesign against the Omni model? Tier 2: same question." | none |
| Drop list | "Drop the stale set (N dashboards, M Looks, no views in {{stale_after_days}} days)? Any exceptions?" | none |
| PDT disposition | For each PDT in the redesign register: "Move this PDT's logic into a dbt model, rebuild it as an Omni query view, or drop it?" | none |
| Permission mapping | "Map these Looker groups and user attributes to Omni groups, user attributes and access grants as listed?" (the plan proposes a one-to-one map; the director confirms or amends) | proposed one-to-one map, pending confirmation |
| Topic architecture | "One Omni topic per Looker explore, or a schema, shared and workbook layering?" | one topic per explore |
| Parallel-run window | "Run Looker and Omni side by side for {{parallel_run_days}} days?" | `bi_migration.parallel_run_days` |
| Parity scope | "Compare every tile, or only tier 1 dashboards' tiles?" | `bi_migration.parity_scope` |

A dashboard the director rules `redesign` still gets a register row and a content batch; its tiles are built against the redesigned topic rather than mapped field by field, and `bi_equivalency` compares only the measures the director names as the redesign's acceptance set.

### Step 4: Decide the model scope

The in-scope model is every view and explore referenced by any dashboard or Look that is not dropped, plus every view those explores join. A view referenced by nothing in scope is **out of scope** and listed under "Model not carried" with the reason `no in-scope content references it`. Fields inside an in-scope view are all carried unless the director rules otherwise; hidden fields are carried hidden.

Every `redesign` model row in scope gets a disposition here: `redesign in Omni` (rebuild by hand on the branch), `drop` (no content needs it), or `defer` (carried as a `needs_human` item into the model batch). PDTs take the ruling from Step 3.

### Step 5: Cut batches

**Model batches** (`batch_kind: model`): group in-scope explores by shared views. Order batches so that a batch's views are all emitted before any topic that uses them; a view shared by several explores goes in the earliest batch that needs it. Target 5 to 15 views per batch. Name batches `b01`, `b02`, ...

**Content batches** (`batch_kind: content`): tier 1 dashboards first, ordered by `usage_rank`, then tier 2, then Looks. Target 5 to 10 dashboards per batch. Each content batch's `depends_on_batch` is the last model batch that carries any explore in its dashboards' `explore_refs`. Schedules and alerts join the batch of the dashboard they belong to. Groups form one `permissions` batch (`batch_kind: model`, first in order) so access grants exist before content is published.

Write `migration/bi_migration_batches.csv` with columns, in this order: `batch_id`, `batch_kind` (`model` | `content`), `object_type`, `object_id`, `object_name`, `explore_or_topic`, `usage_rank`, `ruling` (`parity` | `redesign` | `drop`), `depends_on_batch`. Dropped objects appear with `batch_id` empty and `ruling: drop`, so the drop list is in the same file as the plan.

### Step 6: Bootstrap the register

If `migration/migration_register.csv` does not exist, create it from `TEMPLATES/migration/migration_register.csv`. Insert one row per in-scope object (not dropped) with:

| Column | Value for BI rows |
|---|---|
| `model` | `view:<name>`, `topic:<explore>`, `dashboard:<id>`, `tile:<dashboard_id>/<element_id>`, `look:<id>`, `schedule:<id>`, `group:<name>` |
| `object_type` | `view` | `topic` | `dashboard` | `tile` | `look` | `schedule` | `group` |
| `source_path` | the `lkml_file` for model rows; the Looker URL path for content rows |
| `source_layer` | `looker_model` or `looker_content` |
| `bq_target` | empty until `omni_model` or `omni_content` writes the Omni reference (model id, branch and file, or document identifier). BI rows are exempt from the three-segment physical-path rule, like `metabase_card` rows |
| `state` | `pending` |
| every other column | `null` |

Every `view` and `topic` row carries `last_migrated_commit` = `looker_audit.lookml_commit` (the LookML commit the audit classified from; `omni-model-generate` advances it when the batch is emitted), and every `dashboard` and `look` row carries `source_updated_at` from the content catalog. These are the baselines `migration-drift-generate` compares against; a row without them cannot be drift-checked and is reported as `not_applicable`.

Rows that already exist are left as they are. Record `register_rows` in `status.md`.

### Step 6b: Write the baseline and the evidence file

`migration/baseline.yaml` records what every later verdict is measured against. A verdict that does not name a baseline is not evidence.

```yaml
baseline_id: b001                       # increments on every re-baseline
written_at: "{{TODAY}}"
written_by: <consultant>
lookml_commit: <migration_sources.lookml.last_commit>
looker_deployed_revision: <the production LookML commit Looker reports for the project, when it differs from lookml_commit>
looker_base_url: <bi_migration.looker_base_url>
omni_model_id: <bi_migration.omni_model_id>
omni_branch: <bi_migration.omni_branch>
warehouse: <bi_migration.warehouse>
converter_version: <from scripts/lookml_to_omni.py, recorded in conversion_summary.json>
pair_ruleset_sha: <SHA-256 over bi_pairs/looker_to_omni/*.md plus the engagement's overrides directory>
comparator_version: <from scripts/bi_parity.py>
parity_as_of: <bi_migration.parity_as_of>   # pinned here; bi-equivalency-validate refuses to run unpinned
```

Set `bi_migration.parity_as_of` now if it is null: the end of the last complete day before the first model batch, in the warehouse's timezone. Moving it later is a re-baseline (new `baseline_id`, every standing verdict invalidated), which is the point: a parity result at one instant is not evidence at another.

`migration/parity/evidence.csv` starts here with one row per `tile` and `view` register row. Compute `evidence_fingerprint` with `python3 <plugin-root>/scripts/bi_evidence.py fingerprint --components <json>` from the seven components; at bootstrap only `source_definition` (lookml_commit plus the object's `.lkml` file hash), `dependencies` (the object's closure from `audit/dependencies.jsonl`), `policy_context` (hash of the access filters, grants and user attributes the object is under), `data_context` (`parity_as_of`) and `adapters` (converter, pair ruleset and comparator versions) are known; `target_definition` and `test_contract` are the literal `absent` until `omni-model-generate` and `bi-equivalency-validate` fill them. `stale_kinds` is empty. `migration-drift-generate` is the only command that writes `stale_kinds`; `bi-equivalency-validate` is the only one that clears it.

### Step 7: Write the plan

**Output location**: `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`

Sections:
- Summary: in scope by object type, dropped by object type, batches by kind, rulings made and parked
- Usage ranking: the tier table and the 80% cut
- Rulings: one subsection per ruling in Step 3, with the decision, who made it and when (from `decisions.md`), or `parked`
- Model scope: carried views and explores per batch; model not carried, with reasons; redesign dispositions; PDT dispositions
- Permission map: Looker group or user attribute to Omni group, user attribute or access grant
- Topic architecture: the chosen design and the resulting topic list
- Batches: the batch table with dependencies, and the order they run in
- Parallel run and parity: window, `parity_scope`, the tiles that will be compared, the pinned as-of once set
- Reference key: every code used (batch ids, ruling ids) with its meaning and defining document, per `specs/utils/reference_legibility.md`

### Step 8: Update status

```yaml
artifacts:
  bi_migration_plan:
    generate: complete
    file: migration/bi_migration_plan.md
    data_file: migration/bi_migration_batches.csv
    generated_date: "{{TODAY}}"
    batch_count: N
    objects_in_scope: N
    objects_dropped: N
    register_rows: N
    rulings_parked: N
    generated_files:
      - migration/bi_migration_plan.md
      - migration/bi_migration_batches.csv
      - migration/migration_register.csv
```

### Step 9: Output summary

Print the scope totals, the batch count by kind, the rulings made and parked (with their questions), and the next command:

```
/wire:bi-migration-plan-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv`
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (created or extended)
- `.wire/releases/$ARGUMENTS/migration/baseline.yaml`
- `.wire/releases/$ARGUMENTS/migration/parity/evidence.csv` (created)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact_id, `BI Migration Plan` as artifact_name, and the `file` value from `artifacts.bi_migration_plan` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bi_migration_plan` as artifact, `generate` as action.
