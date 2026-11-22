---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the business rules register — statuses consistent with their required fields, assumptions unexpired, every variant sourced, and rules and implementations citing each other
argument-hint: <release-folder>
---

# Business Rules — Validate

## Validation Checks

Ground truth is the register's own `variants` plus the repository. Where a claim
can be re-derived from the dbt or LookML source, it is.

**Check 1: Status is one of the four**
Every rule's `status` is `agreed`, `disputed`, `assumed` or `unknown`. Any other
value is FAIL, reason `invalid_status`.

**Check 2: Each status carries its required fields**

| Status | Required | Failure reason |
|---|---|---|
| `agreed` | `decision`, `approver`, `agreed_date` | `agreed_without_approver` |
| `disputed` | Two or more `variants`, and a non-blank `disagreement` | `disputed_without_conflict` |
| `assumed` | `decision`, `confirmer`, `confirm_by` | `assumed_without_confirmer` |
| `unknown` | Nothing beyond `id`, `name`, `statement` | — |

A rule marked `agreed` with a decision and no approver is the most common way a
register goes soft, so it is a FAIL rather than a warning: an unattributed decision
cannot be revisited with the person who made it.

**Check 3: Assumptions have not expired**
For every `assumed` rule, `confirm_by` is in the future. An expired assumption is
FAIL, reason `assumption_expired`, naming the rule, the confirmer and the date. The
point of an assumption is that somebody agreed to come back to it.

**Check 4: Every variant is sourced**
Every entry in every `variants[]` has a non-blank `source` and `object`. A variant
without provenance is FAIL, reason `unsourced_variant`: a definition with no
provenance is an opinion.

**Check 5: Imports carry their freshness fields**
Every variant whose `source` is not a repository-readable system (anything reached
through `--import`) has `export_date` and `exported_by`. Missing either is FAIL.

Then: an `export_date` older than the register's own `generated_date` by more than
90 days is WARN, reason `stale_import`, naming the days elapsed. The source system
may have changed and nothing here would know.

**Check 6: Rules and implementations cite each other**
Two directions, and this is the check that keeps the register true rather than
decorative:

1. Every `agreed` rule has at least one `implemented_by` entry, **once the release
   has reached its development phase**. Before that, an empty `implemented_by` is
   expected and not a failure.
2. Every dbt model or LookML measure carrying `meta.wire_business_rule: BR-n`
   names a rule that exists in the register. A citation to a rule id that is not
   there is FAIL, named — it usually means a rule was renumbered, which the
   register forbids.

Direction 2 runs whether or not the release has reached development.

**Check 7: `unknown` never fails on its own**
A rule with status `unknown`, no variants and no decision is PASS. Stated as an
explicit check so a future edit does not quietly turn the register back into an
inventory of the already-known.

`unknown` rules are counted and listed in the report, and they appear in the review
as the open items. Counted, not failed.

**Check 8: Reconciliation checks exist where a legacy variant does**
Every rule with a variant from a legacy source has a non-blank `check` path, and
the file at that path exists. Missing is FAIL, reason `no_reconciliation_check`:
the check is what turns a stated definition into a testable one.

**Check 9: Ids are stable**
Compare against the previous register in git history, where one exists. A rule id
whose `name` has changed, or a name whose `id` has changed, is FAIL, reason
`id_reused`. The build cites these ids, so reuse silently repoints an
implementation at a different rule.

**Check 10: Reference legibility**
Run the `reference_legibility` check from `specs/utils/reference_legibility.md`.

## Report

Write to `.wire/releases/$ARGUMENTS/validation/business_rules_validation.md`,
including a summary table:

| Status | Count |
|---|---|
| agreed | N |
| disputed | N |
| assumed | N (of which expired: N) |
| unknown | N |

A register whose rules are all `agreed` on a first run is worth a second look and
the report says so: it usually means the disagreements were resolved by whoever
wrote the document rather than by the people who own the numbers.

Update `status.md`: `artifacts.business_rules.validate: pass | fail`.
Follow `specs/utils/execution_log.md`.
