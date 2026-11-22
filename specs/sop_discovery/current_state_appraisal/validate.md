---
wire_schema: "1.0"
command: validate
artifact: current_state_appraisal
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: current_state_appraisal
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the current state appraisal — every claim sourced and confidence-rated, sources reconcilable against the logical model, gaps named rather than empty
argument-hint: <release-folder>
---

# Current State Appraisal — Validate

## Validation Checks

Ground truth is the input documents and interview write-ups, not the appraisal's
own claims. Where a check can re-derive a fact from the interviews, it does.

**Check 1: Standing sections present**
Sections 1 to 10 all present and non-empty, except Section 8 (personal and
regulated data), which may record "not discussed" with a named follow-up owner.
An empty section elsewhere is FAIL: the shape is the checklist, and a section
with nothing in it means the question was not asked.

**Check 2: Every row sourced**
Every row of every table in Sections 1 to 9 carries a non-blank `Evidence`
value. A row with no evidence is FAIL, listed by section and row. This is the
check that stops the appraisal drifting into assertion.

**Check 3: Confidence values valid and used**
Every row's `Confidence` is one of `confirmed`, `reported`, `unknown`. FAIL on
any other value.

Then: if every row in the document reads `confirmed`, FAIL with reason
`implausible_confidence`. This appraisal is written without system access. A
document claiming every fact is confirmed has either had system access (in which
case say so in Section 1 and re-run) or has not distinguished what it was told
from what it verified. Naming this as FAIL rather than a warning is deliberate:
the distinction between told and verified is the document's main value.

**Check 4: Gaps section is real**
Section 10's first list (facts not established) is non-empty, or the document
states in one sentence why nothing is outstanding and names who confirmed that.
An empty Gaps list with no statement is FAIL, reason `no_gaps_declared`.

**Check 5: Sources reconcile with the interviews**
For each source named in Section 2, confirm it appears in at least one interview
write-up or input document. A source in the appraisal that appears nowhere in the
evidence set is FAIL, named. This catches a source carried in from a prior
engagement or a template.

The reverse is a WARN, not a FAIL: a source named in an interview but absent from
Section 2 is listed as `unappraised_source`, because a deliberate scope
exclusion is legitimate and the reviewer can confirm it.

**Check 6: Contradictions carry both sides**
Every entry in Section 10's second list names two or more attributed versions. A
contradiction recorded with one side only is FAIL — it is a gap, not a
contradiction, and belongs in the first list.

**Check 7: No target-state content**
The appraisal describes what exists. Scan for proposal language in Sections 1 to
9: "we recommend", "should be", "the target", "we propose", "migrate to". A hit
is WARN with the line quoted, naming `pipeline_design`'s target platform
architecture section as the right home. WARN rather than FAIL because a factual
sentence can legitimately contain "should" ("the nightly load should finish by
06:00, and does not").

**Check 8: Reference legibility**
Run the `reference_legibility` check from `specs/utils/reference_legibility.md`.

**Check 9: Free sections carry the standing discipline**
Any section after Section 10 has the same Evidence and Confidence columns on its
tables. FAIL naming the section otherwise. A free section is free in subject, not
in rigour.

## Output

Write the PASS/FAIL report to `.wire/releases/$ARGUMENTS/validation/current_state_appraisal_validation.md`.

Update `status.md`: `artifacts.current_state_appraisal.validate: pass | fail`.
Follow `specs/utils/execution_log.md`.
