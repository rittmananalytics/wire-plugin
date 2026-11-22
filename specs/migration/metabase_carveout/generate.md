---
wire_schema: "1.0"
command: generate
artifact: metabase_carveout
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
  - artifact: metabase_audit
    action: review
    outcome: approved
  - artifact: region_tagging
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Tenant carve-out of the Metabase estate — scope the adjudicated card and dashboard set to the tenant, choosing the scoping layer per card set (sandboxing, warehouse view, dashboard parameter, or card edit), with a manifest review gate before any write
argument-hint: <release-folder> [--collection <id> | --dashboard <id>]

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout` and `artifact_file_path: migration/metabase_carveout_manifest.csv` before proceeding.

---

## Data Safety — Read Before Proceeding

All transformations apply to decoy-collection test copies (or a serialization export) until the review gate signs the manifest off. Production cards, dashboards, and the production database connection are never touched during generation. A card whose tenant mechanism is `unresolved` is **flagged, never carved unfiltered** — an unfiltered card shows every tenant's rows to the carved-out audience, which is a data-exposure incident, not a rendering bug.

---

# Metabase Carve-out — Generate

## Purpose

Scopes the Metabase estate to the extracted tenant (#184): which reports and dashboards move, and how each becomes tenant-only. Gated to `migration.scope == tenant_carveout`. The card and dashboard set comes from the region-tagging adjudication (`item_type: metabase_card` / `metabase_dashboard`, `adjudicated_ruling: carve_in`), never from a fresh guess — the estate's carve-in/exclude rulings were made once, at the gate built for them.

**The mechanical card edit is the last resort.** The tenant boundary can sit at three better layers, and the command's first job is to record which layer each card set uses — as strategy, reviewed like strategy:

| Layer | What it is | When it is right |
|---|---|---|
| **Data sandboxing** | Metabase row-level filter per permission group — zero card edits | The requirement is "this audience only ever sees tenant X", enforced |
| **Warehouse layer** | A tenant-filtered view/model, with the connection or card sources repointed | One change covers N cards; the warehouse already carries the tenant mechanism |
| **Dashboard parameter** | A dashboard filter mapped per dashcard — card SQL untouched (native cards need a field-filter tag present to accept the mapping) | The need is interactive, not enforced |
| **Card edit** | Per-card filter injection | Only when none of the above fits the card set |

Under a carve-out staged after the parent migration, the tenant project is single-tenant by construction — cards repointed at the tenant connection see only tenant rows, and the layer decision records that as `warehouse_layer` with no edits. The card-edit path exists for the shared-instance cases (a shared Metabase, a shared warehouse, an interim period before cutover). When the tenant runs on its own, separately-hosted Metabase deployment, the layer decision still governs how each card becomes tenant-only; `/wire:metabase-carveout-transport` is what then creates the signed-off objects on that instance (#203).

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_audit review: approved` (the catalog, reverse index, and sandboxing inventory)
- `region_tagging review: approved` — Metabase items adjudicated
- `migration/tenant_predicate_registry.csv` present (the per-card tenant mechanism source)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md` — catalog, reverse index, permission/sandboxing inventory
- `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` — the carve-in card/dashboard set
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` — per-card mechanism and expression
- `.wire/releases/$ARGUMENTS/status.md` — scope, tenant project/connection

## Workflow

### Step 1: Resolve the carve-in set

From `region_tags_adjudicated.csv`, take every `metabase_card` and `metabase_dashboard` item ruled `carve_in`. `--collection <id>` / `--dashboard <id>` narrows within that set (a dashboard resolves to its deduped `dashcards[].card_id` set — dashboards hold no SQL; they are selectors over cards). An item in scope with no `carve_in` ruling is skipped and reported, mirroring the dbt relocate rule.

### Step 2: Choose the scoping layer per card set

Group the carve-in cards by connection and source model family, and record a **layer decision** per group in the manifest: `sandboxing` | `warehouse_layer` | `dashboard_parameter` | `card_edit`, with the reason. The decision set is strategy — `metabase-carveout-review` adjudicates it before anything is transformed. Sandboxing decisions produce the permission-group policy spec (group, table, filter expression from the predicate registry); warehouse-layer decisions name the tenant view/model and the repoint; dashboard-parameter decisions name the parameter and its per-dashcard mappings.

### Step 3: Detect cards with no tenant data (the removal branch)

Per card, establish whether the tenant boundary is even present, using the three methods in order of reliability:

| Card type | Method | Reliability |
|---|---|---|
| MBQL | Walk the source table and joins; check field metadata for the tenant column | High |
| Native SQL | Parse the SQL, resolve table lineage, look for the column | Medium |
| Either | Read the card's `result_metadata` (output columns from the last run) | Medium — shows what the card outputs, not what is filterable at source |

A card with no tenant data (a global reference table, another tenant's regional report) routes to the **removal branch**: **delete the dashcard, not the card** — the card stays in its collection, the tenant's dashboards stop showing it. Recorded per card in the manifest as `action: remove_dashcard`.

### Step 4: Card edits, only where the layer decision says so

For `card_edit` groups, resolve each card's filter from the tenant predicate registry (the same read contract as every other consumer — `specs/utils/tenant_predicate_registry.md`):

- **MBQL** — add a filter clause programmatically. Safe: MBQL is structured.
- **Native SQL** — **never string-append `WHERE`.** Parse to AST, locate the outermost `SELECT`, inject the predicate there, re-render. CTEs, unions, aggregate wrappers, and existing `GROUP BY`s all break naive string approaches — the dbt relocate ladder's lessons apply verbatim (comments stripped before scanning; existing `WHERE` body parenthesized; a set operation classified per branch).
- **`unresolved` mechanism, or no registry row** — the card is **flagged `manual_review_required` and not carved**. It blocks the review gate exactly as an unresolved model blocks the relocate review.
- **`object_carve` / `inherited`** — no filter; the card's sources are tenant-only already; recorded as resolved-without-edit.

Shared cards follow the audit reverse index: a `card_edit` on a card that out-of-scope dashboards also use forces the edit-vs-clone decision into the manifest (`clone` keeps the original for the out-of-scope dashboards and is recorded as forked maintenance) — never a silent fork.

### Step 5: Carve the dashboards

Per carve-in dashboard: prune the dashcards the removal branch flagged; remap the dashboard's filter parameter mappings to the tenant connection's field ids; where the layer decision was `dashboard_parameter`, add the tenant parameter and its per-dashcard mappings. The dashboard's own record in the manifest derives from its cards — a dashboard is done when its surviving cards are.

### Step 6: Write the manifest and update the register

`migration/metabase_carveout_manifest.csv` — one row per card and per dashboard: id, name, query type, layer decision, mechanism, filter applied (or `not_applicable` / `manual_review_required`), dashboards affected, shared-card decision, action, status (`proposed` → `signed_off` → `applied` → `validated`). **Nothing is written to any card or dashboard until its row is signed off** at `metabase-carveout-review`.

Upsert register rows (`object_type: metabase_card` for carved native cards, `metabase_dashboard` for carved dashboards) with `state: pending` until applied and validated; `notes` carry `origin: carveout` and the layer decision. Skip silently if the register does not exist.

### Step 7: Update status

```yaml
artifacts:
  metabase_carveout:
    generate: complete
    file: migration/metabase_carveout_manifest.csv
    generated_date: "{{TODAY}}"
    cards_in_scope: N
    dashboards_in_scope: N
    layer_decisions: {sandboxing: N, warehouse_layer: N, dashboard_parameter: N, card_edit: N}
    dashcards_removed: N
    manual_review_required: N
    shared_cards_cloned: N
```

### Step 8: Output next command

```
/wire:metabase-carveout-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout` as artifact_id, `Metabase Carve-out` as artifact_name, and the `file` value from `artifacts.metabase_carveout` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout` as artifact, `generate` as action.
