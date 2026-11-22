---
wire_schema: "1.0"
command: review
artifact: business_rules
domain: discovery
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
  - pipeline_only
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: business_rules
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
  - utils/meeting_context
  - utils/docstore_sync
description: Review the business rules register — each disputed rule settled or owned, each assumption accepted with its expiry, by the people who own the numbers
argument-hint: <release-folder>
---

# Business Rules — Review

## Purpose

The register holds decisions about what numbers mean. The right reviewers are the
people who own those numbers, not the technical lead, and usually more than one
person: gross sales belongs to finance and to retail, and they may not agree.

## Workflow

### Step 1: Meeting context

Follow `specs/utils/meeting_context.md`, searching for each rule's `name` and the
terms in its `disagreement`. Definition arguments are usually had on calls and
never written down, so a transcript hit here is often the decision itself, and
citing it saves asking the same question twice.

### Step 2: Present by consequence, not by rule

Do not read the register out. For each `disputed` and `assumed` rule, state the
consequence of each option in the reviewer's own terms:

> Gross sales can include in-store orders or exclude them. Including them makes
> the online figure roughly 12% higher than the legacy dashboard shows, and the
> legacy dashboard is what the board sees. Which is right?

The reconciliation check from generate Step 7 supplies that number. A rule
presented with its number attached usually settles in the room; a rule presented
as two SQL expressions usually does not.

### Step 3: Settle, own, or assume

Every `disputed` rule leaves the review as one of three, recorded:

1. `agreed` — with the decision, the named approver, and the date.
2. `assumed` — where the room is confident but the person who can confirm is not
   present. Requires a named confirmer and a `confirm_by` date. Validate will
   fail once that date passes, so the date is a commitment, not a formality.
3. Still `disputed` — with a named owner and a date by which they will settle it.
   The rule is then carried into the build as a known risk, and any model
   implementing it is flagged.

An `unknown` rule leaves as `unknown` with an owner, or is dropped from scope with
the reason. Both are legitimate. What is not legitimate is leaving it unowned.

### Step 4: Confirm the awkward cases out loud

For each rule being agreed, read back what it does with the cases that break
definitions: returns, cancellations, partial refunds, in-store or other secondary
channels, currency conversion, the period boundary, and the remainder that fits
nowhere. These are where the disagreement actually lives, and a rule agreed
without them will come back.

### Step 5: Record the outcome

Update `status.md`: `artifacts.business_rules.review: approved | changes_requested`,
with `reviewed_by` and `reviewed_date`. Where several people approved different
rules, record the approver per rule in the register and list all reviewers here.

Approval requires: no `disputed` rule without a named owner and a date, no
`assumed` rule without a confirmer and a date, no `unknown` rule without an owner
or an explicit scope exclusion.

Approval does **not** require every rule to be `agreed`. A register that honestly
carries three disputed rules with owners is worth more than one where they were
quietly resolved to get the review signed off.

Follow `specs/utils/docstore_sync.md`. Follow `specs/utils/execution_log.md`.
