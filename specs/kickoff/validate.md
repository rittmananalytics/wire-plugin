---
wire_schema: "1.0"
command: validate
artifact: kickoff
domain: kickoff
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: kickoff
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate kick-off deck JSON structure and content completeness
argument-hint: "[release-folder]"

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Kickoff Deck — Validate

## Purpose

Checks that the generated kickoff deck is structurally sound and content-complete before the internal review. Produces a PASS/FAIL report. Failures must be resolved before the deck can be reviewed.

## Inputs

- Engagement-level: `.wire/kickoff-deck.html`
- Release-enriched: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

If neither path resolves to an existing file: stop — "Run `/wire:kickoff-generate` first."

## Workflow

### Step 1: Locate the deck file

Resolve in order:
1. If `<release-folder>` is supplied: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`
2. Else: `.wire/kickoff-deck.html`

Read the file. Extract the EDITMODE block (content between `/*EDITMODE-BEGIN*/` and `/*EDITMODE-END*/`).

### Step 2: JSON structure checks

**FAIL if any of the following**:

| Check | Failure message |
|-------|----------------|
| EDITMODE block is missing | "EDITMODE block not found — template may have been corrupted. Re-run generate." |
| Content between delimiters fails `JSON.parse()` | "EDITMODE block is not valid JSON: [error detail]. Fix and re-run." |
| `slide6Problems` length ≠ 8 | "slide6Problems must have exactly 8 entries (has [n])." |
| `slide8Outcomes` length ≠ 5 | "slide8Outcomes must have exactly 5 entries (has [n])." |
| `slide12W1Items` length ≠ 6 | "slide12W1Items must have exactly 6 entries (has [n])." |
| `slide12W2Items` length ≠ 6 | "slide12W2Items must have exactly 6 entries (has [n])." |
| `slide14Categories` length ≠ 4 | "slide14Categories must have exactly 4 entries (has [n])." |
| `slide6Count` > 8 or < 0 | "slide6Count out of range (must be 0–8)." |
| `slide8Count` > 5 or < 0 | "slide8Count out of range (must be 0–5)." |
| `slide12W1Count` > 6 or < 0 | "slide12W1Count out of range (must be 0–6)." |
| `slide12W2Count` > 6 or < 0 | "slide12W2Count out of range (must be 0–6)." |
| `slide14Count` > 4 or < 0 | "slide14Count out of range (must be 0–4)." |
| Count field > non-empty array entries | "slide6Count claims [n] items but only [m] entries have content." |
| `accentColor` not matching `#[0-9A-Fa-f]{6}` | "accentColor is not a valid hex colour." |
| `slide10Direction` is non-empty and not `"LR"` or `"TB"` | "slide10Direction must be LR or TB." |
| `engagementDate` is non-empty and not matching `YYYY-MM-DD` | "engagementDate is not a valid ISO date." |

### Step 3: Content completeness checks

**WARN (not FAIL) if**:

| Check | Warning message |
|-------|----------------|
| `clientName` is empty or `"CLIENT NAME"` | "clientName is still a placeholder — update before presenting." |
| `engagementDate` is empty | "engagementDate is empty — add a date before presenting." |
| `slide6Count` is 0 | "Problems slide (slide 07) has no content — fill in or the slide will be blank." |
| `slide8Count` is 0 | "Outcomes slide (slide 09) has no content." |
| `slide12W1Count` is 0 and `slide12W2Count` is 0 | "Two-week timeline (slide 13) has no content." |
| `slide14Count` is 0 | "Access requirements (slide 15) has no content." |
| `presenters` is empty or all names are `""` | "Presenter list is empty — add at least one presenter." |
| `slide5Number` is empty | "Big-number slide (slide 05) has no metric — this slide will render empty." |
| `titlePhoto` is empty | "Title slide has no background photo — will render a gradient from accentColor (this is fine)." |

### Step 4: Output the report

```
KICKOFF DECK VALIDATION — [release-folder or "engagement-level"]

PASS / FAIL
-----------
✅ JSON structure valid
✅ Array lengths correct
[or]
❌ slide6Problems must have exactly 8 entries (has 7) — fix before review

WARNINGS
--------
⚠️  clientName is still a placeholder — update before presenting
⚠️  slide14Count is 0 — access requirements slide will be blank

RESULT: PASS with [n] warnings
[or]
RESULT: FAIL — fix [n] errors before proceeding to review
```

### Step 5: Update status

If PASS (even with warnings), update status to:
```yaml
kickoff_deck:
  validate: "complete"
```

If FAIL, leave `validate: "not_started"` and list the errors in the report.
