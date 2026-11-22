---
wire_schema: "1.0"
command: review
artifact: findings_playback
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
  - artifact: findings_playback
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Sponsor playback session — the canonical client-facing review gate

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Findings Playback — Review

## Purpose

**The canonical client-facing review gate of a SOP discovery release.**

This is not an internal review. The review action *is* the sponsor playback meeting — the deck is presented live (by Lewis or Mark per the playbook), the meeting is recorded via Fathom, and the **Sponsor Validation Checklist** is captured at the close.

State transitions:
- `complete` after the deck has been generated and validated
- `reviewed` after the playback meeting has been held (Fathom recording attached)
- `approved` **only when every item on the Sponsor Validation Checklist is `true`**

If any checklist item is `no`, the release stays at `reviewed` and a 30-minute follow-up sponsor session is scheduled (explicit in the playbook's failure modes).

Models Phase 4 (playback meeting + Sponsor Validation Checklist) of the Canonical Discovery Playbook.

## Inputs

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md` (must be PASS or PASS WITH WARNINGS)
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm validation has passed. If FAIL, stop: "Resolve validation failures before holding the playback."
2. Confirm `status.md → sponsor_validation.vision_statement_excerpt` is set. If null, prompt the consultant to set it now from the deck's Vision Statement slide. The playback is partly about the sponsor signing off on this — it needs to exist.

### Step 2: Capture playback meeting context

Ask the consultant:

```
Has the playback meeting been held?

(a) Yes — recorded via Fathom, ready to capture the Sponsor Validation Checklist
(b) Not yet — confirm date and presenter
```

If (b): record the planned date and presenter under `status.md → sponsor_validation.playback_date` and `sponsor_validation.preferred_delivery_option: null`, then stop with: "Re-run this command after the playback has been held."

If (a): proceed.

### Step 3: Pull Fathom transcript

Ask for the Fathom URL for the playback recording. Use the Fathom MCP server to pull:
- Full transcript
- Meeting summary
- Sponsor's verbal endorsements (or refusals) on each of the seven Sponsor Validation Checklist items

This is the most important Fathom integration in Wire — the sponsor's verbal "yes, this is what we want" against the Vision Statement is, per the playbook, the most important artefact in the engagement after the SoW itself.

### Step 4: Pre-fill the checklist from the transcript

For each of the seven Sponsor Validation Checklist items, walk the transcript and propose a value (`true` / `false` / `unclear`). Surface the supporting quote (verbatim) for each.

Then present each item to the consultant for confirmation:

```
For each of the 7 Sponsor Validation Checklist items, confirm the value based on the Fathom transcript and your in-room recall.

1. **Maturity Curve pin agreed.**
   Proposed: <true/false/unclear> based on quote: "<verbatim>"
   Confirm? (yes / no / change to false / change to unclear)

2. **Hierarchy of Needs diagnosis agreed.** ...
3. **PPT diagnosis agreed.** ...
4. **Vision Statement endorsed (both paragraphs).** ...
5. **Solution Initiatives confirmed.** ...
6. **Preferred Delivery Option named (Build / Pair / Coach).** ...
7. **Open conflicts resolved (or follow-up scheduled).** ...
```

For item 6, also capture the named delivery option ("build" / "pair" / "coach" / null) under `sponsor_validation.preferred_delivery_option`.

For any `unclear` or `false`, ask:

```
What follow-up action is needed for this item?
```

### Step 5: Determine the review outcome

If every item is `true`, outcome = **Approved (playback signed off)**.

If any item is `false` or `unclear`, outcome = **Reviewed — follow-up required**. Schedule a 30-min sponsor follow-up session within 1 week. Record the follow-up date under `sponsor_validation.follow_up_session`.

### Step 6: Record the result

Update `status.md`:

```yaml
sponsor_validation:
  playback_held: true
  playback_date: <YYYY-MM-DD>
  playback_fathom_url: <URL>
  maturity_pin: "<confirmed pin>"
  vision_statement_excerpt: "<first 200 chars of vision statement>"
  preferred_delivery_option: "<build|pair|coach|null>"
  checklist:
    maturity_pin_agreed: <true|false>
    hierarchy_diagnosis_agreed: <true|false>
    ppt_diagnosis_agreed: <true|false>
    vision_statement_endorsed: <true|false>
    solution_initiatives_confirmed: <true|false>
    delivery_option_named: <true|false>
    conflicts_resolved: <true|false>
  follow_up_session: <YYYY-MM-DD or null>

artifacts:
  findings_playback:
    review: complete       # = playback held and checklist captured
                           # Note: this is "reviewed" in workflow terms,
                           # not "approved". Approved = checklist all true.
```

### Step 7: Write the Playback Meeting Notes

**Output**: `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`

```markdown
# Findings Playback — Meeting Notes

**Date**: <YYYY-MM-DD>
**Presenter**: <Lewis / Mark>
**Fathom recording**: <URL>
**Sponsor**: <name>
**Outcome**: <Approved (signed off) | Reviewed — follow-up required>

## Sponsor Validation Checklist

| # | Item | Result | Supporting quote |
|---|---|---|---|
| 1 | Maturity Curve pin agreed (<pin>) | ✅ / ❌ | "<quote>" |
| 2 | Hierarchy of Needs diagnosis agreed | ✅ / ❌ | "<quote>" |
| 3 | PPT diagnosis agreed | ✅ / ❌ | "<quote>" |
| 4 | Vision Statement endorsed | ✅ / ❌ | "<quote>" |
| 5 | Solution Initiatives 1–5 confirmed | ✅ / ❌ | "<quote>" |
| 6 | Preferred Delivery Option named (<option>) | ✅ / ❌ | "<quote>" |
| 7 | Open conflicts resolved | ✅ / ❌ | "<quote>" |

## Decisions taken

[Bullet list — what the sponsor decided in the meeting]

## Concerns raised (and how they were addressed)

[Bullet list]

## Follow-ups

- [ ] Owner — action — due date

## Next session

[If approved]: Delivery Roadmap session (or release-spawn directly).
[If follow-up required]: 30-min sponsor session on <date> to resolve <items>.
```

### Step 8: Sync to document store

Follow `specs/utils/docstore_sync.md`. The Playback Meeting Notes go to the Confluence "Playback Meeting Notes" page named in the playbook folder structure (`5. Findings Playback / Playback Meeting Notes`).

### Step 9: Output review summary

If approved:
```
## Findings Playback Review — Approved ✅

All 7 Sponsor Validation Checklist items signed off.

**Maturity pin**: <pin>
**Preferred Delivery Option**: <build/pair/coach>
**Vision Statement endorsed**: yes

### Next Steps

1. Generate the Delivery Roadmap:
   /wire:delivery-roadmap-generate $ARGUMENTS

2. Or spawn Release 1 directly:
   /wire:release-spawn $ARGUMENTS
```

If follow-up required:
```
## Findings Playback Review — Follow-up Required ⚠️

Items not yet endorsed:
- [list]

**Follow-up session**: <date>

The release will remain at `reviewed` until every checklist item is true. Do not start Release 1 until the playback is approved — the playbook's failure-mode table specifically calls out the catastrophic cost of skipping this.
```

### Step 10: Approval gate

The release-level "approved" state is only set when:
- `sponsor_validation.playback_held == true`, AND
- every `sponsor_validation.checklist.*` is `true`

This is checked by `/wire:status` and surfaced as a hard gate before `/wire:release-spawn` can chain into a delivery release.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/playback/findings_playback.html` (no body changes, but the review captures Fathom URL etc)
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


---

## Recording the sign-off under `modelling_led`

The playback is the sign-off gate, and under this profile it signs off five
artifacts at once. Record the outcome per item, not once for the deck:

```yaml
sponsor_validation:
  profile: modelling_led
  held_date: YYYY-MM-DD
  sponsor: <name>
  items:
    current_state_accepted:     accepted | accepted_with_changes | rejected | not_applicable
    conceptual_model_signed_off: ...
    logical_model_signed_off:    ...
    data_flow_accepted:          ...
    roadmap_agreed:              ...
```

An item recorded `accepted_with_changes` names the changes and the artifact they
land in, and that artifact returns to `review: changes_requested`. The playback
itself is `approved` only when every item is `accepted`, `accepted_with_changes`
with the changes recorded, or `not_applicable` with a reason.

A rejected item blocks the playback. The roadmap that follows a rejected
conceptual or logical model would be costed against a model the client does not
accept.
