---
wire_schema: "1.0"
command: generate
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
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate the delivery roadmap with Build / Pair / Coach options
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Delivery Roadmap — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Translates the validated playback into a delivery plan. Produces the Delivery Roadmap document — the Phase 5 exit artefact — and prepares Release 1 for spawning. The roadmap is sponsor-facing.

If the playback included the Roadmap section inline (inline-roadmap pattern), this command produces a confirmatory document mirroring the deck's roadmap slides. If the playback deferred the roadmap to a separate session (deferred-roadmap pattern), this command produces the full standalone artefact.

Models Phase 5 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md` (playback held, checklist captured)
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (with MoSCoW + Phase columns set)
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `engagement/sow.md` (for commercial envelope context)

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery`.
2. Confirm `sponsor_validation.playback_held == true`. If not, stop: "Hold and review the playback first."
3. Note `sponsor_validation.preferred_delivery_option` — drives which delivery option is the headline. If null (sponsor didn't name one), the roadmap presents all three side-by-side as equal.

### Step 2: Read commercial context

Read the SoW to extract:
- Commercial envelope (contract value, sprint count if specified, target go-live)
- Named RA team and % allocations
- Client-side dependencies (named integrations, security review windows, etc.)

### Step 3: Compute the Phase 1 scope

From `requirements_matrix.md`:
- All rows with `Phase: 1` form the Release 1 backlog
- Group by `Domain` and `Hierarchy tier` for the breakdown
- Total row count = Release 1 size

If Phase 1 row count is materially larger than the SoW commercial envelope can support (rule of thumb: more than 4 rows per sprint week), surface the gap explicitly — the roadmap is the moment to force the sponsor to defer some Phase 1 items to Phase 2.

### Step 4: Draft the roadmap

**Output**: `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`

```markdown
# Delivery Roadmap: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Sponsor**: <name>
**Preferred Delivery Option**: <Build | Pair | Coach | not yet named>

## Objectives (3–5 bullets, business-outcome framed)

[What this discovery has agreed to achieve, lifted from the Vision Statement + Solution Initiatives. Use business outcome framing, not deliverable framing.]

## Scope overview

[Visual diagram of the end-to-end flow showing Release 1 in-scope (✅) vs out-of-scope (❌). Use a mermaid diagram or a simple bullet list.]

## Breakdown of Release 1 requirements

| Domain | Hierarchy tier | Row count | Top requirement | Source systems |
|---|---|---|---|---|
| Retail | Clean | 8 | Store-level conversion trust | SAP, CowHills EPOS, Footfall |
| Retail | Define & Track | 4 | UPT/ATV/Conversion definitions | — |
| ... | ... | ... | ... | ... |

**Total Phase 1 rows**: <N>

## Recommendations table

| Task | Description | Proposed Owner | Priority |
|---|---|---|---|
| Populate BigQuery with SAP source | Migrate raw SAP data via Fivetran connector | Data Engineering (Olivier) | High |
| Finalise KPI selection | Confirm Phase 1 KPI list with named sponsor | Sponsor + RA Lead | High |
| Wireframe analytical products | Lo-fi wireframes of Release 1 dashboards | RA Lead | Medium |

## Delivery Options

Three options were presented at the playback (or are presented now if the roadmap is a follow-up session). Each option delivers the same Release 1 backlog; what differs is who does the work and what the client retains at the end.

### Build (RA delivers)

| Dimension | Detail |
|---|---|
| What RA delivers | Full implementation: pipelines, dbt models, semantic layer, dashboards |
| What the client provides | Source-system access, sponsor time, end-user validation |
| Sprint count | <N> sprints of <length> |
| Time to value | Fastest — go-live in <weeks> |
| Cost (relative) | Highest |
| Knowledge transfer | Documentation + recorded sessions; client team observes |
| Risk profile | Low delivery risk; medium adoption risk if client team isn't engaged |

### Pair (RA + client co-delivery)

| Dimension | Detail |
|---|---|
| What RA delivers | 50–70% of the implementation; reviews 100% |
| What the client provides | A named data engineer / analyst pairing 3–4 days/week |
| Sprint count | <N> sprints — typically 1.5× Build option |
| Time to value | Medium |
| Cost (relative) | Medium |
| Knowledge transfer | Hands-on — paired implementation builds client capability |
| Risk profile | Medium delivery risk (depends on client capacity); low adoption risk |

### Coach (Client delivers; RA coaches)

| Dimension | Detail |
|---|---|
| What RA delivers | Architecture + reference implementations + weekly coaching sessions |
| What the client provides | A full delivery team |
| Sprint count | <N> sprints — typically 2× Build option |
| Time to value | Slowest |
| Cost (relative) | Lowest direct RA cost; highest client cost |
| Knowledge transfer | Strongest — client team owns the delivery from day one |
| Risk profile | High delivery risk (client team capability); lowest adoption risk |

### Comparison

| | Build | Pair | Coach |
|---|---|---|---|
| Time | <weeks> | <weeks> | <weeks> |
| Cost (RA) | <£> | <£> | <£> |
| Client capacity needed | Low | Medium | High |
| Knowledge retained | Low | Medium | High |
| Delivery risk | Low | Medium | Higher |

## Release 1 plan summary

- **Sprints**: <N> × <length>
- **Expected go-live**: <date>
- **RA team**: <named consultants and % allocation>
- **Key client-side dependencies**:
  - Source-system access (named systems and contacts)
  - Sponsor weekly availability
  - End-user validation window

## Discovery exit checklist

- [ ] All Stakeholder Interview pages published with all four tags
- [ ] Requirements Matrix complete and reviewed (Hierarchy, PPT, Maturity all locked)
- [ ] Discovery Findings Working Document published (per domain)
- [ ] Findings Playback Deck delivered and sponsor-validated (all 7 checklist items)
- [ ] Sponsor Validation Checklist on the Playback Meeting Notes page
- [ ] Delivery Roadmap published (this document)
- [ ] Release 1 Jira/Linear epic created with stories pre-populated
- [ ] Release 1 kick-off scheduled
- [ ] Engagement Brief updated with discovery outcomes
- [ ] Internal RA retro held

## Next steps

[Named owners + dates for everything that needs to happen between this document and the start of Release 1.]
```

### Step 5: Update status

```yaml
artifacts:
  delivery_roadmap:
    generate: complete
    file: planning/delivery_roadmap.md
    generated_date: {{TODAY}}
```

### Step 6: Sync to document store

Follow `specs/utils/docstore_sync.md`.

### Step 7: Output summary

Show: Release 1 row count, preferred delivery option, top three Phase 1 risks.

```
/wire:delivery-roadmap-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


---

## Per-deliverable owner and priority

Every deliverable in the Release 1 breakdown carries two more columns:

| Column | Values | Rule |
|---|---|---|
| `owner` | A named person, or `RA` / `client` / `joint` | Never blank. `unassigned` is allowed and appears in the review as a question |
| `priority` | `must` / `should` / `could` | Taken from the requirements matrix MoSCoW value where the deliverable traces to a matrix row; asked where it does not |

A deliverable whose priority disagrees with the matrix row it traces to is
flagged, not silently overridden: the roadmap is where a sponsor changes their
mind about priority, and that change should be visible as a change.

## Optional section: leadership view

Off by default, on for the `modelling_led` profile. A one-page view for an
audience that will not read the deliverable breakdown: initiatives grouped as
`now` / `next` / `later`, each with its business value, its indicative cost, and
the capability it unlocks.

Rules:

- An initiative groups deliverables; it is not a rename of one deliverable.
- `now` must be deliverable within the appetite the engagement brief states. An
  overloaded `now` is the most common failure of this view, and `validate` checks
  the count against the brief's stated capacity.
- Cost is indicative and labelled as such, carrying the assumption it rests on.
- Every initiative traces to at least one matrix row. An initiative with no
  requirement behind it is a proposal, and belongs in the target platform
  architecture rather than the roadmap.

## Optional section: data team recommendation

Off by default, on for the `modelling_led` profile. What the client's own team
needs to run the platform after RA leaves: roles, the skills each needs, whether
each is a hire, a reallocation or training, and the order to fill them in.

Written as a recommendation with reasons, not an org chart. Where the People axis
diagnosis exists (`diagnostic` profile), it cites it. Under `modelling_led` it
cites the appraisal's governance and ownership section instead.

## Free sections

Engagement-specific roadmap material goes in its own section, added with
`--section "<title>"`. Sizing a migration and its exposure, an acquisition
integration programme, a regulatory deadline: each matters to one engagement and
is noise everywhere else, so the framework does not name them.

A free section carries the same discipline as the standing ones: every claim
traces to a matrix row, an appraisal finding, or a named person.
