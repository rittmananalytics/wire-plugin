---
wire_schema: "1.0"
command: validate
artifact: migration_batching
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
  - artifact: migration_batching
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared, parallel-safe claims hold

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Batching — Validate

## Purpose

Independently re-derives the ground truth for every check — the inventory object list, the object-level dependency graph, the macro flags — rather than trusting generate's self-report. This independence is the entire point: it is what catches a batch plan that has drifted out of sync with the real dependency graph.

## Validation Checks

Read `migration/migration_batching.csv`, `migration/migration_batching.md`, `migration/migration_inventory.md`, `audit/dbt_audit.csv`, and status.md.

**Read the partition mode first.** Take `artifacts.migration_batching.partition_mode` from status.md (`domain`, `build_ordered_waves`, or `readiness_waves`; treat absent as `domain` for backward compatibility). The mode changes what Checks 2b, 3, 5, 8, 9, 10, and 11 expect — Checks 1, 2, 4, 6, 7 are identical in every mode. All modes must still pass C2 (acyclic) and C3 (every cross-batch edge declared); the two wave modes satisfy both trivially via the full-prefix dependency. Check 8 runs only in `build_ordered_waves`; Checks 10 and 11 only in `readiness_waves`; Check 9 in both wave modes. Readiness mode also reads `migration/tenant_predicate_registry.csv`, `migration/region_tags_adjudicated.csv`, the parent register at `.wire/releases/<migration.parent_release>/migration/migration_register.csv`, and this release's own `migration/migration_register.csv`.

**Check 1 — Every inventory object classified exactly once**
Rebuild the union of objects from `migration_inventory.md`'s unified catalog. Confirm a 1:1 match against `migration_batching.csv` rows — no object missing, none duplicated, no CSV row without a matching inventory object. A row with `batch_id: NO-DEP` counts as classified — it is a deliberate, named bucket for objects with no model consumer (Check 3 confirms none exist), not a gap. Do not flag `NO-DEP` rows as missing, duplicate, or orphaned on that basis alone. In readiness mode, `B00` and `PEN-*` rows count as classified on the same terms.
PASS: one-to-one match. Report the `NO-DEP` count alongside the pass (e.g. "168 objects, 1:1 match, 12 routed to NO-DEP"), and in readiness mode the `B00` and per-pen counts too, so they're visible in the check output, not just the narrative.
FAIL: list missing objects, duplicates, and orphan CSV rows, with counts of each.

**Check 2 — Batch dependency DAG is acyclic**
Rebuild the batch-level dependency graph from the CSV's `depends_on_batches` column alone. Confirm no cycles.
PASS: acyclic.
FAIL: list the cycle (the sequence of batch_ids).

**Check 2b — `batch_id` token form (v3.11.7)**
Every row's `batch_id` matches the canonical form in `specs/utils/wave_resolution.md`: zero-padded upper-case `B` plus digits (`B01`, `B02`, … `B10`), or the reserved `NO-DEP`. In `readiness_waves` mode the reserved readiness tokens are also canonical: `B00`, and `PEN-<NAME>` (upper-case letters and hyphens, starting and ending with a letter). In the other two modes `B00` and `PEN-*` are token-form failures: only readiness mode mints them. Nothing else, in any mode.
PASS: every row canonical for the mode. FAIL: list each offending row with the value found and the expected form.

This check exists because the form was documented here and in 18 consuming specs, agreed on by all of them, and then a produced CSV carried `b1..b10` anyway (wire#192). Every `--wave` command downstream aborted with "no rows found" for a wave that existed, and a lane agent was blocked. The consumers now normalise case- and pad-insensitively as defence in depth, but the file is still wrong and this is the gate that says so. A validation that only checks what `batch_id` *means* (coverage, cycles, cross-batch edges) and never what it *is* leaves the cheapest failure to be found by the most expensive reader.

**Check 3 — Every real cross-batch graph edge is declared**
Independently rebuild the object-level dependency graph from `migration_inventory.md`'s adjacency list plus `dbt_audit.csv`'s manifest-derived model dependencies. Do **not** read `migration_batching.md`'s own DAG as ground truth. For every graph edge whose two endpoints land in different batches (per the CSV's `batch_id` assignments), confirm the dependency direction is represented in `depends_on_batches` for the dependent batch. This is the check that directly answers "does this batch plan actually hold against the real dependencies."

For every object classified `NO-DEP`, independently confirm it genuinely has **zero** graph edges to any model in the Check 3 graph. `NO-DEP` is for objects with no real consumer, not an escape hatch for skipping a batch/wave assignment on an object that does have one — a `NO-DEP` object with an actual model edge is a FAIL on this check, same as an undeclared cross-batch edge.

Readiness-mode `PEN-*` rows are different: a pen member is expected to have edges (its rule, not its graph position, is what parks it), and a pen is not a batch, so edges touching a pen are exempt from the edge-declaration requirement above. Check 11 is what polices them (pen readers confined to the residue wave).

PASS: every cross-batch edge declared, and every `NO-DEP` object confirmed edge-free.
FAIL: list every undeclared cross-batch edge — the two objects, their batches, and the correct direction — and separately list any `NO-DEP` object that in fact has a model consumer (the object, the model, and the edge).

**Check 4 — Batch-zero macro dependency present where required**
For every batch containing a model with a non-empty `platform_macros` value (re-read from `dbt_audit.csv`, not from generate's output), confirm the narrative declares the batch-zero macro translation pass as a prerequisite of that batch.
PASS: all affected batches declare it.
FAIL: list batches missing the prerequisite.

**Check 5 — Parallel-safe claims hold**
For every batch pair listed as parallel-safe in the narrative, confirm zero graph edges (either direction) between their member objects, per the Check 3 graph.
PASS: no parallel-safe claim contradicted.
FAIL: list each contradicted claim with the edge (objects, batches, direction) that breaks it.
In `build_ordered_waves` and `readiness_waves` modes the parallel-safe set must be **empty** (full-prefix dependencies make every wave sequential) — a non-empty parallel-safe list in either wave mode is a FAIL. `NO-DEP` must never appear in a parallel-safe grouping in any mode — it is a holding pen, not a batch, and having zero edges to everything is not evidence it's safe to schedule; a parallel-safe claim naming `NO-DEP`, or a readiness `PEN-*` id, is a FAIL.

**Check 6 — Every CSV row complete**
Each row has a non-empty `object_id`, `object_type`, `source_audit`, `domain`, `batch_id`, and `batch_name`. `depends_on_batches` may be empty. A row with `batch_id: NO-DEP` and `batch_name: "No model dependency — review"` is complete on the same terms as any other row — `NO-DEP` is a valid classification, not a placeholder for a missing one, and must not be flagged incomplete on that basis. `depends_on_batches` empty on a `NO-DEP` row is expected, not a defect. Readiness-mode `B00` and `PEN-*` rows are complete on the same terms, with `depends_on_batches` empty by design.
PASS/FAIL with incomplete rows listed.

**Check 7 — Candidates only, no premature lock-in**
Neither `migration_batching.md` nor `status.md` marks any batch "approved" or "final", and no batch carries a committed date or owner — that is `/wire:migration-batching-review`'s job.
PASS: no lock-in language.
FAIL: quote the offending lines.

**Check 8 — Build-ordered waves are well-formed (only when `partition_mode: build_ordered_waves`)**
Skip in `domain` and `readiness_waves` modes (readiness waves have their own Check 10). When the SCC fallback fired, independently confirm the waves are a valid build order:
- **Fallback is justified and recorded** — re-derive the domain-level SCC condition from the Check 3 object graph (a single SCC spanning the domains). Confirm the narrative and status (`scc_fallback: true`) record it. A build-ordered partition emitted when a viable acyclic *domain* partition existed is a FAIL (the fallback should only fire when it must).
- **Topological order holds** — for every object edge, the dependency's wave id ≤ the dependent's wave id (0 forward references across waves).
- **Full-prefix dependencies** — each wave `Bk`'s `depends_on_batches` is exactly `B01;…;B(k-1)` (wave 1 empty). A missing or partial prefix is a FAIL.
- **Domain tag retained** — every CSV row still carries a non-empty `domain` value for rollup.
PASS/FAIL with the specific violation(s) listed.

**Check 9 — Cutover partition present (only in the wave modes: `build_ordered_waves` or `readiness_waves`)**
Skip in `domain` mode. Confirm `migration_batching.md` has a non-empty `### Cutover partition (secondary view)` section: a domain-grouped rollup, independently re-derivable from the CSV's `domain` and `batch_id` columns, showing which wave(s) each domain's objects actually landed in. Confirm it states — in words, not just implied by the table — that build order and cutover/domain order diverge (because the SCC fallback fired, or because readiness waves are readiness bands rather than domains), and names at least the domains whose objects are split across the most waves. An empty or missing section, or one that just repeats the wave DAG without the domain rollup, is a FAIL — this is the check that stops a reader from mistaking a wave number for a client milestone grouping.
PASS: section present, non-empty, domain/wave mapping independently reproducible from the CSV, divergence stated explicitly.
FAIL: state which of the above is missing.

**Check 10 — Readiness waves are well-formed (only when `partition_mode: readiness_waves`)**
Skip in the other modes. Independently re-derive every model's readiness class from the ground-truth inputs (the registry's rule states and approval groups, the adjudicated `defer`/`split` rulings, the parent register's `delivery_stage` with a live repo read when reachable, this release's own register, and the dependency-closure fixpoint), following `migration-batching-generate` Step 4d exactly, and confirm the CSV agrees. Specifically:

- **Selection is justified and recorded**: status.md carries `migration.scope: tenant_carveout` and a non-null `migration.parent_release`, or the narrative records the `--partition-mode` override. A readiness partition emitted for a non-carve-out release with no override is a FAIL.
- **Every model's wave matches the re-derived class**: shipped models (own register `merged`/`production_verified`, or prior-`B00` preservation) in `B00` and nowhere else; unresolved or row-less registry items in `PEN-UNRESOLVED`; `defer`/`split`-ruled items in `PEN-EXCLUSION-PENDING`; parent-unmerged models (or their transitive dependents, per the fixpoint) no earlier than the waiting-on-parent wave; pen readers and mixed-gate closures in the residue wave.
- **Each gated wave is exactly one approval group and self-contained**: every member's pending-approval closure lies within that one group (plus ready/shipped upstreams). A member whose closure touches a second pending group belongs in residue.
- **Full-prefix dependencies**: each numbered wave's `depends_on_batches` is the full prefix of numbered waves including `B00`; empty on `B00`, pens, and `NO-DEP`.
- **Domain tag retained** on every row for rollup.
PASS/FAIL with each mismatched model listed: the CSV wave, the re-derived class, and the input that decides it.

**Check 11 — No forward-wave or holding-pen reads (only when `partition_mode: readiness_waves`)**
Skip in the other modes. Over the Check 3 object graph and the CSV's wave assignments:

- **Zero forward-wave reads**: for every model edge, the dependency's numbered wave ≤ the dependent's. A model in a shippable wave (the ready and gated waves, `B01` through the last gated wave) reading a model in any later wave is the schedule-breaking case: it would ship a model before its input exists on target.
- **Holding-pen readers are confined to the residue wave**: no model in any numbered wave except residue has an upstream in a `PEN-*` pen. A shippable-wave model reading a pen member is a FAIL, same as a forward read.
- **`B00` is history, not schedule**: exempt `B00` rows from both rules, but report any `B00` model whose upstream now sits in a pen or a numbered wave as an advisory for `/wire:migration-drift-generate`: shipped state has drifted against the current readiness inputs, which is that command's problem, not a batching failure.
PASS: no violations (state the advisory count, 0 included).
FAIL: list each violation (the two models, their waves, the direction) and, per violating model, the downstream closure it would drag forward, so the reader sees the size of the cascade, not just its first edge. On the reference engagement this check caught a real 7-model forward-read cascade during generation.

### Update status

```yaml
artifacts:
  migration_batching:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `validate` as action.
