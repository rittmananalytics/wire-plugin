---
wire_schema: "1.0"
command: validate
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
  - artifact: metabase_carveout
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the Metabase carve-out — layer decisions recorded, filters re-derived from the predicate registry, no unfiltered card, dashcard-not-card removals, shared-card decisions explicit
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Carve-out — Validate

## Validation Checks

Ground truth is `migration/region_tags_adjudicated.csv` (the carve-in set), `migration/tenant_predicate_registry.csv` (the mechanism per card), and the actual card/dashboard state (decoy copies or serialization export) — the manifest's own claims are re-derived, never trusted, mirroring `dbt-carveout-relocate-validate`.

**Check 1 — Every carve-in item has a manifest row**
Every `metabase_card` / `metabase_dashboard` item ruled `carve_in` (within the run's scope) appears in `migration/metabase_carveout_manifest.csv` exactly once; no manifest row exists for an item without a `carve_in` ruling.
PASS/FAIL with missing/extra items.

**Check 2 — Layer decisions recorded and consistent**
Every card row carries a layer decision (`sandboxing` | `warehouse_layer` | `dashboard_parameter` | `card_edit`) with a reason; sandboxing rows have a permission-group policy spec; warehouse-layer rows name the tenant view/model; dashboard-parameter rows have per-dashcard mappings; only `card_edit` rows carry an injected filter.
PASS/FAIL with offending rows.

**Check 3 — Card-edit filters re-derive from the registry**
For every `card_edit` card, re-read the card's actual query (decoy copy / export) and independently re-derive its filter from its registry row: MBQL cards carry the filter clause; native cards carry the expression injected at the **outermost SELECT** (strip comments before re-deriving; a set operation is checked per branch). The filter must match the registry expression, not `migration.tenant_predicate`. A registry expression that is non-empty but fails the well-formedness check in `specs/utils/tenant_predicate_registry.md` is FAIL, reason `malformed_expression`, before any re-derivation (#200): a truncated rule is not a basis to check a card against.
PASS/FAIL with offending cards.

**Check 4 — No unfiltered card, no guessed mechanism**
Every card whose registry mechanism is `unresolved` (or that has no row) is `manual_review_required` and untransformed; no card was carved with a filter that has no registry provenance. An `object_carve`/`inherited` card carries no injected filter and records which of the two it was.
PASS/FAIL with offending cards.

**Check 5 — Removals are dashcard-level**
Every `remove_dashcard` action deleted dashcards only: each affected card still exists in its collection; the pruned dashboards no longer reference it.
PASS/FAIL with offending cards.

**Check 6 — Shared-card decisions explicit**
Every carved card that out-of-scope dashboards also reference (per the audit reverse index) carries an explicit `edit_in_place`/`clone` decision; every `clone` is noted as forked maintenance.
PASS/FAIL with offending cards.

**Check 7 — Dashboard parameter mappings remapped**
Every carved dashboard's filter parameter mappings resolve against the tenant connection's field ids; `dashboard_parameter`-layer dashboards carry the tenant parameter mapped on every surviving dashcard (native cards have the required field-filter tag).
PASS/FAIL with offending dashboards.

### Update status

```yaml
artifacts:
  metabase_carveout:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Output next command

```
/wire:metabase-carveout-review $ARGUMENTS
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout` as artifact, `validate` as action.
