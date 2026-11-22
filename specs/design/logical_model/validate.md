---
wire_schema: "1.0"
command: validate
artifact: logical_model
domain: design
release_types:
  - sop_discovery
  - full_platform
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: logical_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
  - utils/mml_import
description: Validate the logical model — every conceptual entity accounted for, every key and cardinality decided or explicitly open, sources reconciled against the appraisal, attribution rules complete
argument-hint: <release-folder>
---

# Logical Model — Validate

## Validation Checks

Ground truth is the approved `conceptual_model.md`, the appraisal's source list
where present, and the external model where `model_source` names one. The logical
model's own claims are re-derived, never trusted.

**Check 1: Every conceptual entity is accounted for**
Every entity in `conceptual_model.md` Section 1 appears in logical model Section 1,
or is listed in Section 8 with a reason. An entity that appears in neither is FAIL,
named. This is the coverage check that stops a domain being quietly dropped between
the two documents.

**Check 2: No entities invented here**
Every entity in Section 1 traces to a conceptual entity. An entity present here and
absent from the conceptual model is FAIL, named, with the fix being to add it to the
conceptual model and re-review — the client signed off an entity list, and adding to
it downstream bypasses that sign-off.

Associative entities introduced by Check 5's many-to-many resolution are the one
exception, and must be marked `derived: associative` with the relationship they
resolve.

**Check 3: Keys decided or open, never blank**
Every Section 1 entity has a Section 2 row. Every Section 2 row states a natural key
and a surrogate strategy, or names the entity in Section 8. A blank key field with no
open question is FAIL, reason `undeclared_key`.

**Check 4: Uniqueness claims are testable**
Every natural key asserted as unique carries either evidence (a source constraint, a
profiling result, a named person confirming) or the marker `assumed`. An unevidenced,
unmarked uniqueness claim is FAIL: it becomes a dbt `unique` test that fails on first
run, and the cost of finding out then is higher than asking now.

**Check 5: Cardinality complete or explicitly undetermined**
Every relationship in `conceptual_model.md` Section 2 appears in Section 3 with a
cardinality that is either a real value or `undetermined` with a named person in
Section 8. A relationship missing from Section 3 entirely is FAIL.

A cardinality of `many-to-many` with no associative entity named is FAIL, reason
`unresolved_many_to_many`.

**Check 6: Cardinality from an external model is cited, not restated**
Where `model_source` names an external model, every cardinality this document
carries is either cited to that model or marked as added here. An uncited,
unmarked cardinality is WARN, reason `unattributed_cardinality`: it is the shape a
stale second copy takes.

**Check 7: Identity resolution complete per multi-source entity**
Every entity with more than one source row in Section 1 has a Section 4 entry, and
every Section 4 entry states matching keys, precedence, a tie-break, and no-match
handling. A missing field is FAIL, naming the entity and the field. An entity with
one source and a Section 4 entry is WARN, reason `unnecessary_resolution`.

**Check 8: Precedence is attributed**
Every Section 4 precedence order names who decided it. An unattributed precedence is
FAIL: it is the decision most likely to be wrong and least likely to be revisited.

**Check 9: Attribution rules handle the remainder**
Every Section 6 rule states its window, its precedence, and what happens to records
it cannot attribute. A rule with no remainder handling is FAIL, reason
`incomplete_attribution_rule`.

**Check 10: Sources reconcile with the appraisal**
Where `planning/current_state_appraisal.md` exists, every source named in Section 1
appears in its Section 2. A source here and not there is FAIL, named: either the
appraisal is incomplete or the logical model has invented a source, and both need
resolving before build.

Where no appraisal exists (a `full_platform` release, typically), this check reports
SKIP with the reason, not PASS.

**Check 11: Normalisation stated per entity group**
Every conceptual domain has a Section 5 entry with a shape and a one-sentence
trade-off. A missing entry is FAIL, named.

**Check 12: Ownership assigned**
Every Section 1 entity has a Section 7 owner and approver, or is named in Section 8.

**Check 13: Reference legibility**
Run the `reference_legibility` check from `specs/utils/reference_legibility.md`.

## Output

Write the PASS/FAIL report to `.wire/releases/$ARGUMENTS/validation/logical_model_validation.md`.

Update `status.md`:

```yaml
logical_model:
  validate: pass          # or: fail
  validated_date: [today]
```

Follow `specs/utils/execution_log.md`.


---

## Check: `modality_coverage`

Runs only when `status.md` has `model_source: modality`. Skipped with the reason
recorded otherwise, never reported as PASS.

Both directions, per `specs/utils/mml_import.md`, "The `modality_coverage` check":

1. Every conceptual entity in the `.mml` files appears in this document or in its
   explicitly-excluded list with a reason. Unaccounted entities are FAIL, named.
2. Every entity in this document maps to an MML entity or to a requirement. An
   entity in neither is FAIL, named.

Entities with `type = metric` are outside direction 1: they are semantic-layer
measure candidates, not conceptual entities.

**A missing `entity_resolutions.mml` is never a failure of this check.** The
Modality specification does not define that block, so a model written to the
specification never has one. Treating its absence as a gap would fail every
hand-authored model.

The same applies to a missing `logical_relationships.mml`: cardinality falls
through to the `relationship` block and then the inline verb, and only a
relationship that yields nothing in all three places is `undetermined`.
