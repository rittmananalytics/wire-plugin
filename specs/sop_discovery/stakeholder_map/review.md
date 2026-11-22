---
wire_schema: "1.0"
command: review
artifact: stakeholder_map
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
  - artifact: stakeholder_map
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Confirm the stakeholder map with the sponsor

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Map — Review

## Purpose

Sponsor confirmation of the stakeholder map. This is the first sponsor-facing review in a SOP discovery release — its job is to confirm who RA will interview, lock in booking owners, and surface any politically sensitive omissions before Phase 2 starts. Usually folded into the kick-off meeting but can be run separately if the kick-off has already happened.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map_validation.md` (if present)

## Workflow

### Step 1: Locate the map

Resolve `$ARGUMENTS`. Read both files.

### Step 2: Pull meeting context

Follow `specs/utils/meeting_context.md`:
- Search Fathom for kick-off or pre-kick-off conversations referencing this release
- Look for sponsor mentions of named individuals, "definitely include X", "skip Y", "ask Z about A"

### Step 3: Present for review

Output the stakeholder table and the domain-coverage summary from the validation report. Highlight:
- Any FAIL items from validation
- Any P0/P1 marked `Sceptical` (sponsor should know who's pushing back)
- Any domains with zero coverage

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the stakeholder map review with the sponsor?",
    "header": "Stakeholder Map Review",
    "options": [
      {"label": "Approved", "description": "Sponsor confirmed the list; bookings can start"},
      {"label": "Approved with additions", "description": "Sponsor added named stakeholders or changed priorities"},
      {"label": "Approved with removals", "description": "Sponsor flagged people RA should not interview (political / scheduling)"},
      {"label": "Needs rework", "description": "Sponsor wants the map redrafted (rare — usually means scope changed)"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect detailed changes

Ask:
```
Record any specific changes (additions, removals, priority shifts):
```

For each change, update the map directly:
- Add rows for new stakeholders
- Remove (or mark `OUT - sponsor decision`) for removals — do not silently delete; note them so the audit trail is preserved
- Update priorities/booking owners as instructed

### Step 5: Update status

```yaml
artifacts:
  stakeholder_map:
    review: complete    # or "pending_rework"
```

### Step 6: Output review summary

```
## Stakeholder Map Review Complete

**Outcome**: [Approved / Approved with additions / Approved with removals / Needs rework]
**Stakeholders added**: [N]
**Stakeholders removed**: [N]
**Priorities changed**: [N]

### Next Steps

[If approved]:
Begin Phase 2 — book and run interviews. For each stakeholder:
/wire:stakeholder-interview-generate $ARGUMENTS --stakeholder <slug>

If you haven't run the kick-off yet:
/wire:kickoff-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
