---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
  - utils/meeting_context
  - utils/docstore_sync
description: Review the current state appraisal with the client's technical lead — facts corrected, gaps assigned an owner, contradictions resolved or accepted
argument-hint: <release-folder>
---

# Current State Appraisal — Review

## Purpose

The appraisal is a factual document, so its review is a correction pass rather
than an approval of judgment. The right reviewer is the person who knows the
platform, usually the client's technical lead or data engineer, not the sponsor.

## Workflow

### Step 1: Meeting context

Follow `specs/utils/meeting_context.md`, searching for the sources, tools and
reports named in the appraisal. A fact contradicted on a call after the document
was written is the most common correction, and it is cheaper to find here than
in the playback.

### Step 2: Present for correction

Present Sections 1 to 9 as a list of factual claims, grouped by section, each
with its evidence and confidence. Ask three questions per section:

1. Is anything here wrong?
2. Is anything missing that a delivery team would trip over?
3. For each `reported` row: can you confirm it, and does that make it
   `confirmed`?

Record every correction with who made it and the date. A `reported` row the
reviewer confirms becomes `confirmed` and cites them.

### Step 3: Assign the gaps

Walk Section 10's first list. Every outstanding fact leaves the review with a
named owner and a date, or an explicit decision that it is not worth chasing,
recorded with the reason. An unassigned gap at the end of the review is the one
thing that blocks approval, because the roadmap that follows will be costed
against it.

### Step 4: Resolve or accept contradictions

For each contradiction in Section 10's second list, one of three outcomes,
recorded: resolved (one version is right, named), both true (they describe
different things, and the document is corrected to say so), or unresolved and
accepted with the reason and the risk it carries.

### Step 5: Record the outcome

Update `status.md`: `artifacts.current_state_appraisal.review: approved | changes_requested`,
with `reviewed_by` and `reviewed_date`.

Approval requires: every correction applied, every Section 10 gap owned or
explicitly dropped, every contradiction resolved or accepted.

Follow `specs/utils/docstore_sync.md` to publish the reviewed document.
Follow `specs/utils/execution_log.md`.
