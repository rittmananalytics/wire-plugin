---
wire_schema: "1.0"
command: generate
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
preconditions: []
description: Generate the engagement brief for a SOP discovery release

---

# Engagement Brief — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Drafts the internal RA Engagement Brief at the start of a SOP discovery release. The brief is a two-page internal document that captures the commercial and scope context the consultant must walk into the kick-off already knowing. It is not a sponsor deliverable — it exists so that pre-discovery work is grounded in what the deal record and SoW already say, before any of the sponsor's time is spent.

Models Phase 0 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- Release folder: `.wire/releases/$ARGUMENTS/` with `release_type: sop_discovery` in `status.md`

**Helpful (read if present)**:
- `engagement/context.md` — engagement overview created by `/wire:new`
- `engagement/sow.md` (or `sow.pdf`, or any file under `engagement/references/`)
- `engagement/calls/` — Fathom transcripts from the sales process (preceding kick-off)
- HubSpot deal record — if the Atlassian/HubSpot MCP is available, fetch the deal owner's notes

## Workflow

### Step 1: Locate the release

1. Resolve `.wire/releases/$ARGUMENTS/`. Confirm `status.md` has `release_type: sop_discovery`. If not, stop — "This command only applies to SOP discovery releases."
2. If the brief already exists at `planning/engagement_brief.md`, ask whether to **re-generate** (overwrite) or **update** (preserve existing fields and only fill gaps).

### Step 2: Gather source material

Read in order, summarising what each contributes to the brief:

1. `engagement/sow.md` — in-scope domains, contractual deliverables, named success metrics, named stakeholders, target go-live, explicit out-of-scope statements
2. `engagement/context.md` — anything captured by `/wire:new`
3. `engagement/calls/` — meeting notes and Fathom transcripts from the sales process. Look for: stated problems, expressed desired outcomes, named stakeholders, sensitivities
4. HubSpot deal record (if MCP available) — `mcp__claude_ai_HubSpot__get_crm_objects` for the deal; pull meeting notes and engagement objectives
5. Any files in `engagement/references/` (annual reports, investor decks, careers page snapshots)

If sources are thin, ask the engagement lead the missing questions directly — one at a time.

### Step 3: Draft the engagement brief

**Output location**: `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`

Template:

```markdown
# Engagement Brief: {{ENGAGEMENT_NAME}}

**Status**: Draft (internal RA)
**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}

| Field | Content |
|---|---|
| **Client** | Full legal name (and trading name if different) |
| **Engagement** | SoW reference, signature date, contract value, payment terms |
| **Sponsor** | Name, title, email, what success looks like for them personally |
| **Lead Consultant** | RA owner |
| **RA Team** | Named consultants and % allocation |
| **Problem statement (1 sentence)** | What is broken today that the client is paying us to fix — in their words |
| **Desired outcome (1 sentence)** | What "done" looks like in business terms, not deliverable terms |
| **In-scope domains** | Bullet list. Be precise. |
| **Out-of-scope (explicit)** | Bullet list of things that look in-scope but are not |
| **Success metrics** | KPI definitions, dashboard count, model count, user count, target adoption rate |
| **Known constraints** | Tech stack lock-in, regulatory, regional, security, existing contracts, budget caps |
| **Known risks** | Sponsor turnover, internal politics, data access blockers, parallel programmes |
| **Commercial structure** | Direct / PSF-funded / mixed. Invoicing schedule. |
| **Target dates** | Kick-off, playback, Release 1 start, Release 1 go-live |

## Pre-discovery checklist progress

- [ ] SoW read in full
- [ ] HubSpot deal record reviewed (sales-process meeting notes and Fathom recordings)
- [ ] Slack `#sales` and any client channel scanned
- [ ] Client public materials reviewed (annual report, careers page, conference talks)
- [ ] Confluence space (or Discovery folder) set up
- [ ] Google Drive folder set up following the standard structure
- [ ] Findings Playback deck template copied to engagement Drive
- [ ] Stakeholder Map drafted with gaps identified (see `/wire:stakeholder-map-generate`)
- [ ] Sponsor confirmation requested: discovery scope, stakeholders, time commitment, target playback date

## Notes
[Anything that didn't fit a row above — historical context, surprises from the sales record, etc.]
```

### Step 4: Update status

```yaml
artifacts:
  engagement_brief:
    generate: complete
    file: planning/engagement_brief.md
    generated_date: {{TODAY}}
```

### Step 5: Sync to document store (if configured)

Follow `specs/utils/docstore_sync.md` to mirror the brief to Confluence or Notion.

### Step 6: Output summary

Print: artifact location, top three gaps the consultant needs to chase (typically: target playback date, sponsor confirmation of stakeholders, budget/timeline specificity), and the next command:

```
/wire:engagement-brief-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
