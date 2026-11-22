---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
  - utils/meeting_context
  - utils/docstore_sync
description: Review the logical model — precedence and attribution decisions confirmed by the people who own them, open questions closed or owned
argument-hint: <release-folder>
---

# Logical Model — Review

## Purpose

The logical model holds decisions that look technical and are not. Which source
wins for a customer record, and how a conversion is attributed, are business
decisions with money attached. This review puts them in front of the people whose
decisions they are.

In a `modelling_led` `sop_discovery` release this is a client sign-off gate, and
the approved document is one of the deliverables the playback presents.

## Workflow

### Step 1: Meeting context

Follow `specs/utils/meeting_context.md`, searching for the entities, sources and
attribution terms in the document. Precedence and attribution are the decisions most
often settled verbally on a call and never written down, so a transcript hit here is
often the decision itself.

### Step 2: Present by decision, not by section

Do not walk the document top to bottom. Group what needs agreeing by who has to
agree it:

1. **For the business owner of each entity**: the grain ("one record means one
   ..."), the natural key, and the ownership assignment in Section 7.
2. **For whoever owns customer or product data across systems**: every Section 4
   precedence order and tie-break, stated as a consequence rather than a rule —
   "when the same customer exists in both, the CRM name wins and the shop name is
   discarded. Is that right?"
3. **For whoever owns the numbers**: every Section 6 attribution rule, stated with
   its remainder — "conversions outside the 30-day window are counted as
   unattributed and excluded from channel totals, so channel figures will not sum
   to the overall total. Is that acceptable?"
4. **For the technical lead**: Section 5's normalisation calls and Section 2's
   surrogate key strategy.

Record each decision with the name of the person who made it and the date.

### Step 3: Close the open questions

Walk Section 8. Every entry leaves the review either answered, with the answer
folded into the relevant section, or owned by a named person with a date. An
`undetermined` cardinality or an `assumed` uniqueness claim that survives the
review is carried forward as a known risk into the roadmap, and named as such.

### Step 4: Record the outcome

Update `status.md`:

```yaml
logical_model:
  review: approved        # or: changes_requested
  reviewed_by: [name]
  reviewed_date: [today]
```

Approval requires: every Section 4 precedence and Section 6 rule confirmed by a
named person, every Section 8 entry answered or owned, and every `assumed`
uniqueness claim either evidenced or accepted as a risk.

Follow `specs/utils/docstore_sync.md`. Follow `specs/utils/execution_log.md`.
