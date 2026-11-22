---
wire_schema: "1.0"
command: review
artifact: delivery_roadmap
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
  - artifact: delivery_roadmap
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Sponsor review of the delivery roadmap and Release 1 scope

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Delivery Roadmap — Review

## Purpose

Sponsor sign-off on the delivery roadmap. This is the second sponsor-facing review in a SOP discovery release (after the playback). Its job is to confirm Release 1 scope and the chosen delivery option so that `/wire:release-spawn` can chain into Release 1 with confidence.

If the roadmap was bundled into the playback (inline-roadmap pattern), this review is often a 15-minute confirmatory session. If deferred (deferred-roadmap pattern), this is a full sponsor meeting with its own Fathom recording.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`
- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap_validation.md`
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read inputs. Confirm validation has passed.

### Step 2: Pull meeting context

If a Fathom recording exists for the roadmap session, fetch it via the Fathom MCP and extract:
- Sponsor's verbal confirmation of preferred Delivery Option
- Any scope changes (additions to or removals from Release 1)
- Named follow-up actions

### Step 3: Present for review

Output:
1. The chosen Delivery Option
2. The Release 1 row count and breakdown
3. The named team + go-live date
4. Any FAILs/WARNINGs from validation

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the delivery roadmap review with the sponsor?",
    "header": "Delivery Roadmap Review",
    "options": [
      {"label": "Approved — Release 1 ready to spawn", "description": "Sponsor confirmed scope, option, and go-live"},
      {"label": "Approved with scope changes", "description": "Sponsor moved items in/out of Release 1; capture and update the matrix"},
      {"label": "Delivery option changed", "description": "Sponsor changed their mind on Build/Pair/Coach; capture the new option"},
      {"label": "Needs rework", "description": "Sponsor wants substantive changes — regenerate the roadmap"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture changes

Ask:
```
Record any specific changes from the sponsor (scope, option, dates, team):
```

Apply changes:
- **Scope moves**: edit the `Phase` column for affected rows in `requirements_matrix.md`. Re-run breakdown computation if the count changed materially.
- **Option change**: update `sponsor_validation.preferred_delivery_option` and update the roadmap headline.
- **Date/team changes**: update the Release 1 plan summary directly.

### Step 5: Update status

```yaml
artifacts:
  delivery_roadmap:
    review: complete    # or "pending_rework"

sponsor_validation:
  preferred_delivery_option: "<confirmed option>"
```

### Step 6: Output review summary

```
## Delivery Roadmap Review Complete

**Outcome**: [Approved / Approved with scope changes / Option changed / Needs rework]
**Delivery Option (confirmed)**: <Build / Pair / Coach>
**Release 1 size**: <N> rows
**Go-live**: <date>

### Next Steps

[If approved]:
Spawn Release 1 from this discovery:
/wire:release-spawn $ARGUMENTS

This will:
- Create `.wire/releases/02-<release-name>/` (next sequence number)
- Seed the new release's status.md with the chosen release_type (matching the delivery option)
- Pre-populate the Jira/Linear epic from the requirements_matrix Phase 1 rows
- Link back to this discovery release

[If rework]:
/wire:delivery-roadmap-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

### Step 8: Discovery release approval

Once `delivery_roadmap.review: complete` AND the Sponsor Validation Checklist on `findings_playback` is all-true, the discovery release is **approved end-to-end**. `/wire:status` will show this release as `approved` and `/wire:release-spawn` can chain forward.

If the sponsor outcome from the playback was **no-go** (every checklist item true except Solution Initiatives confirmed: false, or sponsor explicitly chose to not proceed), the discovery release is still **approved** as a discovery — the deliverable was the go/no-go decision. Record `status.md → go_no_go_decision: no_go` and do not spawn a delivery release.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md` (if changes captured)
- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (if scope moved)
- Updated `.wire/releases/$ARGUMENTS/status.md`
