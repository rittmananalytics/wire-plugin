---
wire_schema: "1.0"
command: generate
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
  - artifact: engagement_brief
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate the stakeholder map for a SOP discovery release

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Map — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Builds the stakeholder map: the list of people RA needs to interview in this discovery, with priority, influence/interest, sentiment, booking owner, and recommended interviewer. The map drives the interview backlog in Phase 2 of the canonical playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` (approved)

**Helpful**:
- `engagement/context.md` — named team members from `/wire:new`
- `engagement/sow.md` — named stakeholders from the SoW
- HubSpot deal record (if MCP available) — known contacts at the client
- Client org chart (`engagement/org/` if present)

## Workflow

### Step 1: Locate the release

Resolve `.wire/releases/$ARGUMENTS/`. Confirm `release_type: sop_discovery` and that the engagement brief exists. If missing: "Generate the engagement brief first."

### Step 2: Gather candidate stakeholders

Extract from:
1. SoW named stakeholders
2. Engagement brief sponsor field + RA team
3. HubSpot deal record contacts
4. Org chart attachments

Also ask the engagement lead directly:
```
Who else needs to be on the interview list? (Beyond those already named in the SoW and deal record.)
List any roles where you suspect a P0 or P1 voice is missing.
```

### Step 3: Draft the map

**Output**: `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`

```markdown
# Stakeholder Map: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}

## Interview priority guide

- **P0** — Sponsor, primary economic buyer, named end-user lead, technical owner of source systems. Week 1.
- **P1** — Domain SMEs whose requirements drive Release 1 scope. Week 1 or early week 2.
- **P2** — Adjacent stakeholders, downstream consumers, governance/security. Time-permitting or group session.

## Stakeholder list

| Slug | Name | Title | Department | Role in discovery | Influence (H/M/L) | Interest (H/M/L) | Sentiment | Priority | Booking owner | Recommended interviewer | Target week |
|------|------|-------|------------|-------------------|-------------------|------------------|-----------|----------|---------------|--------------------------|-------------|
| `firstname-lastname` | Firstname Lastname | Title | Department | Sponsor / SME / Adjacent / Governance | H | H | Positive / Neutral / Sceptical | P0 / P1 / P2 | Sponsor / RA Lead / SME | Mark / Lewis / consultant | Week 1 / 2 / 3 |

Slug convention: `firstname-lastname` (lowercase, hyphens, ASCII only). Used as the file name for the interview write-up and the `slug` key in `status.md → interviews[]`.

## Coverage check (run after the map is drafted)

- [ ] Every in-scope domain (from `engagement_brief.md → In-scope domains`) has at least one P0 or P1 stakeholder
- [ ] Sponsor is P0
- [ ] At least one technical owner of the source systems is named
- [ ] At least one end-user lead is named per in-scope domain
- [ ] Sentiment is recorded for every P0 and P1 (don't leave blank — guess if you have to, and correct after the interview)

## Gaps and risks

[List any domains where coverage looks thin, or any stakeholder you expect will be hard to book. These become the sponsor confirmation asks at the kick-off.]
```

### Step 4: Update status

```yaml
artifacts:
  stakeholder_map:
    generate: complete
    file: planning/stakeholder_map.md
    generated_date: {{TODAY}}
```

### Step 5: Sync to document store (if configured)

Follow `specs/utils/docstore_sync.md`.

### Step 6: Output summary

Show: count of stakeholders by priority (P0/P1/P2), domains covered vs in-scope-domains-with-no-stakeholder, the top gap to chase with the sponsor.

Next:
```
/wire:stakeholder-map-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
