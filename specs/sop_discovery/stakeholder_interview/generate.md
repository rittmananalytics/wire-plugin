---
wire_schema: "1.0"
command: generate
artifact: stakeholder_interview
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
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate a stakeholder interview write-up with the mandatory four-tag template
argument-hint: "[release-folder] --stakeholder <slug> | --workshop <slug>"

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Interview — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Creates **one** stakeholder interview write-up for a specific stakeholder from the stakeholder map. This command is **repeatable per stakeholder** — call it once per interview, ideally within 24 hours of the call, while the conversation is fresh.

The write-up is the source-of-truth for what a stakeholder said and is the input to the consolidation step. Every theme bullet on the write-up carries the **mandatory four-tag set**: a domain tag, a type tag, a Hierarchy of Needs tier, and a PPT axis. Validation (`/wire:stakeholder-interview-validate`) enforces those four tags mechanically — they cannot be retrofitted from the consolidated matrix without losing diagnostic signal.

Models Phase 2 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md` (reviewed and approved)
- `--stakeholder <slug>` — the slug from the stakeholder map; uniquely identifies the row

**Helpful**:
- Fathom recording URL for this stakeholder's interview (highly recommended — generate fills from the transcript)
- Any documents the stakeholder shared (named dashboards, spreadsheets, decision trees)

## Workflow

### Step 1: Locate the release and stakeholder

1. Resolve `.wire/releases/$ARGUMENTS/`. Confirm `release_type: sop_discovery`.
2. Parse `--stakeholder <slug>` from arguments. If missing: ask the consultant for the slug, listing all P0/P1 slugs from the stakeholder map.
3. Read the stakeholder's row from `planning/stakeholder_map.md`. If the slug is not found in the map, stop — "Add this stakeholder to the map first via `/wire:stakeholder-map-generate`, or pick an existing slug from: [list]."
4. Compute the target write-up path: `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`. If it already exists, ask the consultant whether to **re-generate** (overwrite) or **append** new content.

### Step 2: Source the interview content

Ask:
```
Provide the Fathom recording URL for this interview (or paste the transcript directly, or type "no recording" to scaffold a blank template):
```

If a Fathom URL is provided, use the Fathom MCP server to pull the transcript and meeting summary. Extract:
- A verbatim quote that best captures what this person needs the sponsor to remember
- The role, day-to-day, painful things, decisions/workflows, KPIs lived by, existing assets, risks raised, scope notes

If a transcript is pasted, do the same extraction on the pasted content.

If "no recording", scaffold the template with empty sections — the consultant fills them in by hand.

### Step 3: Draft the write-up

**Output**: `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`

```markdown
---
slug: <slug>
stakeholder_name: "<Firstname Lastname>"
title: "<Title>"
department: "<Department>"
priority: <P0|P1|P2>
interview_date: <YYYY-MM-DD>
interviewer: "<RA name>"
fathom_url: <URL or null>
related_documents: []
---

# {{stakeholder_name}} — {{department}} Discovery

## Stakeholder quote (their words)

> "The single sentence or short paragraph that best captures what this person needs the sponsor to remember. Verbatim. Use the quote that would change a sponsor's mind if they read nothing else."

## Meeting summary

- Their role and how data fits into it
- The single most painful thing about today's analytics for them
- The decision or workflow they want to do better
- The KPIs or measures they live by
- Existing assets they rely on (named dashboards, sheets, sources)
- Risks or concerns they raised
- What they would flag as out-of-scope or low priority

## Themes

Every theme bullet below carries all four tags:

1. `#<domain>` — one of the in-scope domains (e.g. `#retail`, `#fulfillment`, `#finance`)
2. `#<type>` — one of: `#pain` | `#requirement` | `#kpi` | `#risk` | `#existing-asset`
3. `#<hierarchy>` — one of: `#collect` | `#clean` | `#define-track` | `#analyse` | `#optimise-predict`
4. `#<ppt>` — one of: `#people` | `#process` | `#technology`

Classification rules:
- Hierarchy tier: **the lowest tier whose absence is blocking it**. A predictive-modelling ask blocked by unreliable customer data is a `#clean` requirement until the foundations are fixed.
- PPT axis: **the axis whose absence is causing it**. Pick the binding constraint — refusing to choose is refusing to diagnose.

Examples:
- `#retail #pain #clean #process` — Store managers cannot trust footfall numbers because the SAP/EPOS reconciliation runs weekly and breaks silently
- `#retail #kpi #define-track #people` — UPT, ATV, Conversion definitions vary by region; no agreed business owner
- `#retail #existing-asset #analyse #technology` — Looker dashboard 520, currently the most-used dashboard for store conversion

### Theme list

- [theme bullet text] `#<domain> #<type> #<hierarchy> #<ppt>`
- [theme bullet text] `#<domain> #<type> #<hierarchy> #<ppt>`

## Follow-ups required

- [ ] Outstanding question, owner, due date

## Documentation referenced

- List of attached or linked source documents the stakeholder shared
```

When generating from a Fathom transcript, **propose** the four tags for each theme but explicitly mark uncertain classifications with a `?` suffix (e.g. `#process?`) so the consultant can confirm. Do not leave any tag missing.

### Step 4: Update status

In `status.md`, append (or update) the entry in `interviews:` for this slug:

```yaml
interviews:
  - slug: <slug>
    stakeholder_name: "<Firstname Lastname>"
    title: "<Title>"
    priority: <P0|P1|P2>
    interviewer: "<RA name>"
    interview_date: <YYYY-MM-DD>
    file: "planning/interviews/<slug>.md"
    fathom_url: <URL or null>
    generate: complete
    validate: not_started
    review: not_started
    themes_tagged: 0
```

Also update the aggregate `stakeholder_interview` artifact state to `generate: in_progress` if it was `not_started`. It becomes `complete` only when every P0 and P1 stakeholder from the map has a write-up.

### Step 5: Sync to document store

Follow `specs/utils/docstore_sync.md` — this creates the per-stakeholder Confluence/Notion page.

### Step 6: Output summary

Show: the file path, the count of theme bullets, the count of themes with uncertain tags (`?` suffix), and the next command:

```
/wire:stakeholder-interview-validate $ARGUMENTS --stakeholder <slug>
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


---

## `--workshop <slug>` mode

A modelling-led discovery gathers most of its material in group workshops rather
than one-to-one interviews: a domain session with six people in a room, or a
model walkthrough with the data team. The four-tag discipline still applies, but
the write-up needs a different shape, because attribution and agreement work
differently in a group.

Invoked as `/wire:stakeholder-interview-generate <release> --workshop <slug>`.
Writes `interviews/workshop_<slug>.md`.

### What changes

| | `--stakeholder` | `--workshop` |
|---|---|---|
| Attendees | One person | A list, each with role, and each marked present or apologised |
| Tagged findings | Attributed to the interviewee | Attributed to the named speaker. A finding nobody will own is recorded as `attributed: room` |
| Agreement | Not applicable | An explicit Agreed list, each with who agreed and who was in the room |
| Disagreement | Not applicable | An explicit Unresolved list, with both positions and both names |
| Open items | Follow-ups for that person | Follow-ups with a named owner and a date |

### Required sections

1. **Attendees** — name, role, present or apologised. An apologised invitee whose
   domain was discussed anyway is flagged, because their absence is a risk to
   anything agreed about their area.
2. **Tagged findings** — the same four mandatory tags, each attributed to a named
   speaker or to `room`.
3. **Agreed** — one line per decision, with who agreed. This is the section that
   makes a workshop write-up worth writing: a decision taken in a room and never
   recorded is the most expensive kind of lost work.
4. **Unresolved** — one line per disagreement, both positions, both names, and who
   will settle it.
5. **Open items** — owner and date each.

### What `validate` checks in this mode

The four-tag rule applies unchanged. Additionally: every attendee marked present
appears at least once as an attributor or is explicitly noted as having not
spoken to the record; every Unresolved entry has two attributed positions and a
named settler; every Open item has an owner and a date. A workshop write-up with
an empty Agreed list and an empty Unresolved list is FAIL, reason
`no_outcomes_recorded` — a session that produced neither agreement nor
disagreement did not happen as recorded.
