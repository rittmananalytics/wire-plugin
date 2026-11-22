---
wire_schema: "1.0"
command: validate
artifact: metabase_equivalency
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
delegates_to:
  - utils/precondition_gate
description: Card-level equivalence — prove a migrated or carved Metabase card returns the same rows, in the model verdict taxonomy, gating the connection cutover
argument-hint: <release-folder> [--cards id1,id2 | --dashboard <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

## Data Safety — Read Before Proceeding

All card executions for comparison run against the decoy collection's test copies (or directly as read-only queries against the two warehouse connections). No production card is repointed or edited to compare. Source-platform reads are SELECT only.

---

# Metabase Equivalency — Validate

## Purpose

`metabase-migration`'s decoy validation confirms cards **run**; nothing proved they return the **same rows** (#184). This command closes that with card-level verdicts in the model taxonomy — the reporting-layer analogue of `reverse-etl-equivalency-validate` — and it is the gate the Stage 2 connection cutover consumes: **every in-scope card must hold `pass` or `pass_qualified` before the production connection repoints.**

Like `equivalency-validate`, this is a repeatable loop command, not a generate/validate/review artifact.

## Prerequisites

- `metabase_audit review: approved`
- The migrated (or carved) card versions exist as decoy test copies, or the manifest rows are `applied`

## Workflow

### Step 1: Resolve scope and comparison sides

Scope: every in-scope card from the migration manifest (and the carve-out manifest under `tenant_carveout`); `--cards id1,id2` or `--dashboard <id>` (its deduped card set) narrows. Comparison sides are scope-dependent:

| Scope | Source side | Target side |
|---|---|---|
| `full_migration` (or absent) | The card's **source-dialect query** on the **source connection** | The **translated query** on the **target connection** |
| `tenant_carveout` | The **parent connection's** result with the card's **resolved registry filter** applied (`migration.parent_target_project` connection) | The **tenant connection's** result, unscoped (single-tenant by construction) |

**MBQL cards** compare by executing the same MBQL against both connections — there is no translated SQL to distrust, but the two databases' data still has to match at the card grain. **Native cards** compare the source text against the manifest's proposed/applied text. Under `tenant_carveout`, a card whose registry mechanism is `unresolved` is **verdict `fail`, reason `unresolved_predicate`** — never compared unfiltered (the source side would return every tenant's rows and the comparison would fail for a reason unrelated to the carve). A card whose registry expression is non-empty but fails the well-formedness check in `specs/utils/tenant_predicate_registry.md` is likewise **verdict `fail`, reason `malformed_expression`** (#200): a truncated filter applied to the parent side compares a row set nobody ruled on.

**Separately-hosted tenant instance (#203).** When the carve-out transported objects onto their own Metabase deployment (`/wire:metabase-carveout-transport`), the target side executes on the target instance: resolve each card's target copy through the transport manifest's recorded `source_id -> target_id` mapping (`migration/metabase_carveout_transport_manifest.csv`), never by name. A card with no recorded target id is verdict `fail`, reason `not_transported`; it blocks the go-live gate like any other fail.

**Same-instance repoint (#255).** When the carve-out repointed a card on the same instance instead (`/wire:metabase-carveout-repoint`), both sides execute on `MB_HOST` and the target copy resolves through the repoint manifest's recorded ids (`migration/metabase_carveout_repoint_manifest.csv`), never by name. For a `duplicate` row the target is the recorded `repointed_id`; for an `in_place` row it is the card's own id, compared against the recorded rollback baseline query as the source side, because the pre-change query is the only surviving definition of what the card used to return. A card recorded `staged` is compared as its `staged_card_id`: the verdict is what `--promote` requires, so a staged card must be checkable before promotion. A card with no recorded id is verdict `fail`, reason `not_repointed`; it blocks the go-live gate like any other fail.

### Step 2: Compare at the card grain

Both sides run under the pinned-vintage discipline (a pinned as-of, or the baseline `T`). Compare the result sets: row count, the row set keyed by the card's grain columns, and column-value hashes over the card's `result_metadata` columns (canonicalised per the equivalency edge-case rules). Parameterised cards (field-filter template tags) compare at a declared parameter binding recorded in the report — an unbound field filter compares the card's unfiltered default.

### Step 3: Verdicts

The model taxonomy applies unchanged: `pass`, `pass_qualified` (the pair type allow-list, or a known-differences entry on the card's underlying tables — the declared-window rules apply where the underlying tables carry them), `diff_*` with a named mechanism, `fail`. Explanations qualify a fail; they never upgrade it.

### Step 4: Verdict log and register

Each card's verdict appends to `migration/migration_verdict_log.csv` (`object_type: metabase_card`, same single-writer merge as every lane — `specs/migration/equivalency/verdict_schema.md`) and updates the card's register row where one exists. Carve-out verdicts carry `scope` and the resolved predicate hash like every other carve-out verdict.

### Step 5: The cutover gate

`metabase-migration`'s Stage 2 (production connection repoint) requires every in-scope card at `pass`/`pass_qualified` from this command; under `tenant_carveout`, so does the tenant instance's go-live. A `fail` or unresolved card blocks the repoint — a dashboard that renders wrong numbers after cutover is discovered by the client, which is the most expensive place to find it.

### Step 6: Report and status

`.wire/releases/$ARGUMENTS/migration/metabase_equivalency_report_{run_number}.md`: per card — query type, comparison sides, parameter bindings, counts both sides, differing keys/columns (named), verdict. Update status:

```yaml
artifacts:
  metabase_equivalency:
    last_run_date: "{{TODAY}}"
    cards_checked: N
    passing: N
    failing: N
    unresolved: N          # tenant_carveout only — unresolved predicate, never compared
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_equivalency` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_equivalency` as artifact, `validate` as action.
