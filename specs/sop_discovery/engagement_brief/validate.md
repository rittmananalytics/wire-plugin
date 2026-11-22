---
wire_schema: "1.0"
command: validate
artifact: engagement_brief
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
  - artifact: engagement_brief
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the engagement brief for completeness before kick-off

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Engagement Brief — Validate

## Purpose

Checks that the engagement brief is complete enough to walk into the discovery kick-off with. The brief is internal-RA, so validation is structural and specificity-focused rather than stakeholder-facing.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`

## Workflow

### Step 1: Locate the brief

Resolve release folder from `$ARGUMENTS`. Read `planning/engagement_brief.md`. If not found: "Engagement brief not found. Run `/wire:engagement-brief-generate $ARGUMENTS` first."

### Step 2: Run checks

Collect PASS / WARNING / FAIL for each.

#### Field completeness
- [ ] Client field populated (full legal name)
- [ ] SoW reference present
- [ ] Sponsor name and email present (not "TBD")
- [ ] Lead Consultant named
- [ ] Problem statement is exactly one sentence and uses the client's framing (not RA boilerplate)
- [ ] Desired outcome is exactly one sentence and is business-outcome framed (not deliverable framed)
- [ ] In-scope domains: at least one bullet
- [ ] Out-of-scope: at least one bullet (this is the most-skipped row; flag if empty)
- [ ] Success metrics: at least one measurable metric (a number, a count, or a named KPI)
- [ ] Known constraints: at least one specific constraint
- [ ] Known risks: at least one risk named
- [ ] Target dates: at least kick-off and playback dates set; Release 1 start can be `TBD`

#### Quality checks
- [ ] **Problem vs deliverable**: the problem statement does not describe a tool or deliverable (e.g. "we need Looker") — it describes a business problem
- [ ] **Outcome specificity**: the desired outcome contains either a measurable change ("reduce X by Y") or a named user behaviour change ("store managers can answer X without calling head office")
- [ ] **Out-of-scope is real**: the out-of-scope items are things that genuinely look in-scope. "World peace" doesn't count.
- [ ] **Sponsor has a personal success line**: the Sponsor field includes what success looks like for them personally, not just their title

#### Pre-discovery checklist
- [ ] SoW marked as read
- [ ] HubSpot deal record marked as reviewed (or a note explaining why not)
- [ ] Stakeholder map noted as drafted (link or status `not_started` flag)

### Step 3: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/engagement_brief_validation.md`

```markdown
# Engagement Brief Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**File**: planning/engagement_brief.md

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|---|---|---|
| Client | ✅ | |
| Sponsor present + personal success | ⚠️ | No personal success line — ask sponsor at kick-off |
| Problem statement is 1 sentence in client's words | ✅ | |
| Desired outcome is business-outcome framed | ❌ | "Build a Looker dashboard" — rewrite as a behaviour change |
| Out-of-scope present | ❌ | Empty — fill before kick-off; this is the most common cause of scope creep |
| Success metrics measurable | ⚠️ | |
| Constraints specific | ✅ | |
| Risks named | ✅ | |
| Target dates set | ✅ | |
| Pre-discovery checklist progress | ⚠️ | HubSpot deal record not yet reviewed |

## Issues to Resolve

### FAIL: Out-of-scope empty
The out-of-scope section is empty. The playbook's failure-mode table specifically calls this out as the most common cause of overrun. List at least three items that look in-scope but are not — sponsor will confirm at kick-off.

### FAIL: Desired outcome describes a deliverable
"Build a Looker dashboard" is a deliverable, not an outcome. Rewrite as a behaviour change or measurable improvement (e.g. "Store managers answer the same five conversion questions without calling head office").

## Next Steps

[If PASS or PASS WITH WARNINGS]:
1. Resolve any warnings before kick-off
2. Internal RA review (Head of Delivery sign-off): /wire:engagement-brief-review $ARGUMENTS
3. Then draft the stakeholder map: /wire:stakeholder-map-generate $ARGUMENTS

[If FAIL]:
1. Fix the issues listed
2. Re-run validation: /wire:engagement-brief-validate $ARGUMENTS
```

### Step 4: Update status

```yaml
artifacts:
  engagement_brief:
    validate: complete   # or "failed" if FAIL
```

### Step 5: Output summary

Show the result and the top issue (if any).

## Output Files

- `.wire/releases/$ARGUMENTS/planning/engagement_brief_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
