---
name: cowork-deal-qualify
description: >
  Runs a structured MEDDIC qualification on any HubSpot deal, pulling the
  current deal record and filling gaps through conversation. Identifies which
  MEDDIC elements are confirmed, weak, or missing, then updates the HubSpot
  deal with a qualification summary and recommended next actions.

  Use whenever the user asks to "qualify a deal", "run MEDDIC on [deal]",
  "how qualified is [prospect]", "check deal health", "is [company] real
  pipeline?", or "what do we still need to find out on [deal]". Also triggers
  on phrases like "update deal notes", "qualification check", "deal review",
  or when the user names a company and asks whether to pursue it.
platform: cowork
connectors:
  required: [hubspot]
  optional: [fathom]
triggers:
  - "qualify [deal/company]"
  - "run MEDDIC on [deal]"
  - "how qualified is [prospect]?"
  - "check deal health for [company]"
  - "is [company] real pipeline?"
  - "what do we still need to find out on [deal]?"
  - "deal review for [company]"
---

# Deal Qualification Skill — MEDDIC Framework

Runs a structured MEDDIC qualification assessment on a named HubSpot deal.
Pulls the live deal record and any available Fathom discovery call transcripts,
maps findings to the six MEDDIC elements, identifies gaps, asks targeted
questions to fill them, then writes a qualification summary back to HubSpot.

---

## Connector guard

Before proceeding, verify:
- **HubSpot**: required — call `HubSpot:get_organization_details` to confirm.
  If unavailable, stop and ask the user to connect HubSpot in
  Settings → Connectors.
- **Fathom** (optional): call `Fathom:search_meetings` with a test query.
  If unavailable, proceed with HubSpot data only and note the gap.

---

## Step 1 — Identify the deal

Extract the company or deal name from the user's request. If not given, ask
which deal to qualify.

```
HubSpot:search_crm_objects
  objectType: deals
  query: [company or deal name]
  limit: 5
```

If multiple matches, show them and ask the user to confirm which deal.

Retrieve the full deal record:

```
HubSpot:get_crm_objects
  objectType: deals
  objectId: [deal id]
  properties: [dealname, dealstage, amount, closedate, description, hs_deal_stage_probability, hubspot_owner_id]
```

Also retrieve the associated contact and company:

```
HubSpot:get_crm_objects
  objectType: contacts
  associations: deals:[deal id]
```

---

## Step 2 — Retrieve discovery call signals (Fathom)

If Fathom is available, search for meetings with this prospect:

```
Fathom:search_meetings
  search_term: [company name]
  limit: 5
```

For any matches, retrieve the transcript:

```
Fathom:get_meeting_transcript
  recording_id: [meeting id]
```

Extract signals for each MEDDIC element: pain statements, budget mentions,
timeline commitments, stakeholder names and titles, decision process clues,
and champion indicators.

---

## Step 3 — Map to MEDDIC elements

For each of the six MEDDIC elements, assign a status based on all available
evidence:

| Status | Criteria |
|--------|---------|
| ✅ Confirmed | Clear, specific evidence in HubSpot notes or Fathom transcript |
| ⚠️ Partial | Some evidence, but ambiguous or incomplete |
| ❌ Missing | No evidence found |

### MEDDIC element definitions

**M — Metrics**: Quantified business impact of solving the problem. Specific
numbers: revenue uplift, cost reduction, time saved, error rate reduced.

**E — Economic Buyer**: Named individual with budget authority. Not just a
sponsor or champion — the person who can sign the PO without further approval.

**D — Decision Criteria**: The explicit criteria the prospect will use to
select a partner. What matters to them: methodology, team experience, cost,
references, tooling expertise.

**D — Decision Process**: The steps and timeline from proposal to signed
contract. Who approves, who reviews, procurement involvement, legal review,
board sign-off.

**I — Identify Pain**: The specific business problem and the consequences of
not solving it. Why now? What happens if they don't act?

**C — Champion**: An internal contact who wants the engagement to succeed,
has access to the economic buyer, and will advocate for RA internally.

---

## Step 4 — Ask targeted gap-filling questions

For each ❌ Missing or ⚠️ Partial element, ask the user to provide what they
know — or flag it as a question to raise in the next call.

Present the gap questions as:
> "To complete the MEDDIC picture, I need to know: [question]"
> "If you don't know yet, I'll flag this as a discovery action for your next call."

Typical gap questions:

| Missing element | Question |
|----------------|---------|
| Metrics | "Have they quantified what solving this is worth to them — revenue, cost, time?" |
| Economic Buyer | "Who actually holds the budget? Have you spoken to them, or only to a champion?" |
| Decision Criteria | "Have they told you how they'll choose a partner — price, methodology, references?" |
| Decision Process | "What's the path from our proposal to a signed contract? Who's involved in sign-off?" |
| Identify Pain | "What's the specific trigger — why are they looking now rather than 6 months ago?" |
| Champion | "Is there someone internal who's actively pushing for this and has the ear of the buyer?" |

Accept the user's answers and update the MEDDIC mapping accordingly.

---

## Step 5 — Produce the qualification summary

```markdown
## MEDDIC Qualification: [Deal Name]
**Date**: [Today]
**Deal stage**: [Stage]
**Amount**: [£X or TBD]

### MEDDIC scorecard

| Element | Status | Evidence |
|---------|--------|---------|
| Metrics | ✅/⚠️/❌ | [1-line summary or "Not established"] |
| Economic Buyer | ✅/⚠️/❌ | [Name and title, or "Not identified"] |
| Decision Criteria | ✅/⚠️/❌ | [Key criteria or "Not stated"] |
| Decision Process | ✅/⚠️/❌ | [Timeline and steps, or "Unknown"] |
| Identify Pain | ✅/⚠️/❌ | [Pain statement or "Not articulated"] |
| Champion | ✅/⚠️/❌ | [Name and role, or "Not identified"] |

### Overall health: [Strong / Moderate / At Risk / Unqualified]

- **Strong**: 5–6 elements confirmed ✅
- **Moderate**: 3–4 elements confirmed ✅
- **At Risk**: 1–2 elements confirmed ✅
- **Unqualified**: 0 elements confirmed ✅

### Recommended next actions
[Numbered list — each gap maps to a specific discovery action or question to
ask in the next call. Max 5 actions. Be specific: "Ask [name] directly
whether they are the budget holder" not "Identify economic buyer".]
```

---

## Step 6 — Write summary to HubSpot

Once the summary is produced, offer to update the HubSpot deal:

> "Shall I write this qualification summary to the HubSpot deal notes?"

If yes:

```
HubSpot:manage_crm_objects
  objectType: deals
  action: update
  objectId: [deal id]
  properties:
    description: "[Full MEDDIC summary as plain text]"
    hs_deal_stage_probability: [adjust if health assessment suggests a change]
```

Confirm the update to the user.

---

## Error handling

| Error | Action |
|-------|--------|
| Deal not found in HubSpot | Try partial match on company name; ask user to confirm |
| No Fathom meetings found | Proceed with HubSpot data only; note gap |
| User can't answer gap questions | Flag them as discovery actions for next call |
| Amount not set on deal | Note as a commercial qualification gap |
