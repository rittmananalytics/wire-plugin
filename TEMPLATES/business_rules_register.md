# Business Rules Register — {{CLIENT_NAME}}

**Release**: {{RELEASE_ID}}
**Domains covered**: {{DOMAINS}}
**Generated**: {{GENERATED_DATE}}
**Machine-readable**: `artifacts/business_rules.yaml`

One entry per rule. Every competing definition is recorded with where it came
from, whether or not it is the one chosen. A rule nobody has decided is recorded
as `unknown`, not left out: this register exists as much to say what has not been
agreed as what has.

## Summary

| Status | Count | Meaning |
|---|---|---|
| `agreed` | {{N_AGREED}} | Decided, with a named approver and a date |
| `disputed` | {{N_DISPUTED}} | Two or more definitions exist, none chosen yet |
| `assumed` | {{N_ASSUMED}} | Chosen without confirmation, with a confirmer and an expiry |
| `unknown` | {{N_UNKNOWN}} | Nobody has decided, and no existing definition is authoritative |

## Reference key

| Code | Meaning | Defined in |
|---|---|---|
| `BR-n` | Business rule n | This document |

---

## BR-1 — {{RULE_NAME}}

**Domain**: {{DOMAIN}}
**Status**: {{STATUS}}
**Statement**: {{ONE_SENTENCE_IN_PLAIN_WORDS}}

### Definitions found

| Source | Object | Expression | Export date |
|---|---|---|---|
| {{SOURCE}} | {{FILE_OR_OBJECT}} | `{{EXPRESSION}}` | {{EXPORT_DATE_OR_DASH}} |

Every row names where it came from. A definition with no source does not enter
the register.

### What they disagree on

{{STATED_EXPLICITLY_NOT_AS_DEFINITIONS_VARY}}

### Decision

| | |
|---|---|
| Decision | {{CHOSEN_DEFINITION_OR_NONE_YET}} |
| Approved by | {{NAMED_PERSON}} |
| Date | {{DATE}} |
| Owner, if still disputed | {{NAME_AND_DATE}} |
| Confirmer and expiry, if assumed | {{NAME_AND_CONFIRM_BY}} |

### The awkward cases

What the rule does with the cases that break definitions. Each answered, or
recorded as open.

| Case | Treatment |
|---|---|
| Returns | {{IN_OR_OUT}} |
| Cancellations | {{IN_OR_OUT}} |
| Partial refunds | {{TREATMENT}} |
| Secondary channels (in-store orders, marketplace, third party) | {{IN_OR_OUT}} |
| Currency conversion | {{RATE_AND_DATE_BASIS}} |
| Period boundary | {{BASIS}} |
| The remainder that fits nowhere | {{WHERE_IT_GOES}} |

### Implemented by

| Object | Cites |
|---|---|
| {{DBT_MODEL_OR_LOOKML_MEASURE}} | `meta.wire_business_rule: BR-1` |

### Reconciliation check

`checks/br_1_{{SLUG}}.sql` — compares both readings against the legacy source.

| Reading | Result | Matches legacy |
|---|---|---|
| {{OPTION_A}} | {{FIGURE}} | {{YES_OR_NO}} |
| {{OPTION_B}} | {{FIGURE}} | {{YES_OR_NO}} |

---

## Open items

| Rule | Status | Owner | By |
|---|---|---|---|
| {{BR_N}} | {{disputed_or_unknown}} | {{NAME}} | {{DATE}} |

Every `disputed` and `unknown` rule appears here with an owner, or with an
explicit note that it has been dropped from scope and why. An unowned open item
is what blocks the review.
