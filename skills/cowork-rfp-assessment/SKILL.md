---
name: cowork-rfp-assessment
description: >
  Scores an incoming RFP or new business enquiry against Rittman Analytics'
  Ideal Customer Profile to produce a structured go/no-go recommendation.
  Accepts uploaded PDFs, Google Drive links, or pasted text. Cross-references
  HubSpot won/lost deal history for comparable engagements. Outputs a scored
  assessment report with optional HubSpot deal creation.

  Use whenever the user shares an RFP, tender, or new business enquiry and
  asks: "is this a fit?", "should we bid?", "score this RFP", "qualify this
  deal", or "assess this opportunity". Also triggers on phrases like "new RFP",
  "proposal request", "tender document", or "prospect brief".
platform: cowork
connectors:
  required: [google-drive, hubspot]
  optional: [fathom]
triggers:
  - "score this RFP"
  - "is this a fit for us?"
  - "should we bid on this?"
  - "assess this opportunity"
  - "qualify this new prospect"
  - "go/no-go on this RFP"
  - "run ICP scoring on [company]"
---

# RFP Assessment Skill

Scores an incoming RFP or business enquiry against Rittman Analytics' Ideal
Customer Profile (ICP) and produces a structured go/no-go recommendation with
rationale. Designed for use in Cowork — it reads uploaded documents, queries
HubSpot for comparable won/lost deals, and optionally creates a new deal record.

---

## Connector guard

Before proceeding, verify:
- **Google Drive**: optional — used only if the user provides a Drive URL.
  Call `GoogleDrive:list_recent_files` to confirm availability. Skip gracefully
  if unavailable.
- **HubSpot**: required for comparable deal lookup and deal creation.
  Call `HubSpot:get_organization_details` to verify. If unavailable, note the
  gap and proceed with document analysis only.
- **Fathom**: optional — used to retrieve prospect call transcripts.
  Call `Fathom:search_meetings` with a test query. Skip gracefully if
  unavailable.

---

## Step 1 — Ingest the RFP document

Obtain the document content via the first available route:

1. **Uploaded file** — Claude reads PDF natively from the conversation context.
   For DOCX, use the `Read` tool on the uploaded file path.
2. **Google Drive URL** — extract the file ID and call
   `GoogleDrive:read_file_content` with that ID.
3. **Pasted text** — proceed directly with the text provided.

If none of these yields content, ask the user to attach the document, share a
Drive link, or paste the key sections.

---

## Step 2 — Extract structured signals from the document

From the RFP content, extract:

| Signal | Notes |
|--------|-------|
| Company name and domain | For HubSpot lookup |
| Industry / sector | Map to RA sector categories |
| Tech stack mentioned | dbt, Looker, BigQuery, Snowflake, Databricks, Tableau, Power BI, etc. |
| Project type | Build, migrate, augment, train, assess, operate |
| Team profile | Data team size, maturity indicators, in-house vs outsourced |
| Budget or fee range | Explicit or inferred from scope |
| Timeline | Start date, duration |
| Engagement model | Fixed price, T&M, retainer, staff aug |
| Geography | UK, EU, US, APAC, other |
| Delivery location | Remote, on-site, hybrid |
| Infrastructure | Cloud (which), on-prem requirement |
| Tooling mandate | Any mandated tools (especially Tableau, Power BI) |
| Public sector flag | Government, NHS, local authority, etc. |
| Decision criteria | How they will select a partner |

Flag "Not stated" for any field with no evidence in the document.

---

## Step 3 — Check HubSpot for comparable deals

Search for similar won and lost deals to calibrate the scoring:

```
HubSpot:search_crm_objects
  objectType: deals
  query: [company name or sector keyword]
  limit: 10
```

Look at closed-won and closed-lost deals in the same sector and project type.
Note: what similar deals were won at, what caused losses, and any recurring
patterns in deal characteristics.

If HubSpot is unavailable, skip this step and note it in the report.

---

## Step 4 — Score against the ICP

Load and apply the ICP criteria from `references/icp_criteria.md`.

Score each of the six dimensions 0–10 based on the evidence extracted:

| Dimension | Weight | Score (0–10) | Weighted score |
|-----------|--------|-------------|---------------|
| Tech stack fit | 25% | | |
| Commercial fit | 20% | | |
| Project type fit | 20% | | |
| Company / team profile | 15% | | |
| Sector fit | 10% | | |
| Geography | 10% | | |
| **Total** | 100% | | **/10** |

Calculate: `weighted_total = sum(score_i × weight_i)`

**Overall rating:**
- 7.5–10: Strong Fit — recommend pursuing
- 5.5–7.4: Moderate Fit — pursue with conditions
- 3.5–5.4: Weak Fit — significant concerns; consider pass or scoped pilot
- 0–3.4: Poor Fit — recommend declining

---

## Step 5 — Check hard disqualifiers

Before producing the recommendation, check for any of the following. Each is
an automatic no-go regardless of ICP score:

1. Tableau or Power BI mandate (and client will not consider Looker)
2. On-premises infrastructure only — no cloud deployment permitted
3. Public sector or government (UK, EU, or international)
4. Budget below £25,000 total (or equivalent)
5. Staff augmentation only — no advisory or build component
6. Requires permanent placement or IR35-inside contracting
7. Competing with a panel of 10+ agencies with no evaluation criteria

If any disqualifier applies: flag it clearly in the report, set recommendation
to **Decline**, and note the specific disqualifier.

---

## Step 6 — Produce the assessment report

```markdown
# RFP Assessment: [Company Name]
**Assessment date**: [Today's date]
**Document**: [File name or "Pasted text"]
**Assessor**: Rittman Analytics ICP v1.0

---

## Recommendation: [PURSUE / PURSUE WITH CONDITIONS / DECLINE]

[2–3 sentences stating the recommendation and the 1–2 most decisive factors.]

---

## ICP Scorecard

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|---------|
| Tech stack fit | 25% | X/10 | X.XX |
| Commercial fit | 20% | X/10 | X.XX |
| Project type fit | 20% | X/10 | X.XX |
| Company / team profile | 15% | X/10 | X.XX |
| Sector fit | 10% | X/10 | X.XX |
| Geography | 10% | X/10 | X.XX |
| **Total** | | | **X.XX/10** |

---

## Signal analysis

### Strengths
[Evidence-backed bullets for each dimension that scored well]

### Concerns
[Evidence-backed bullets for each dimension that scored poorly or is ambiguous]

### Hard disqualifiers
[None identified] OR [List each with specific evidence from the document]

---

## Comparable deals from HubSpot
[2–3 comparable won/lost deals and what they tell us about this opportunity]
OR [HubSpot unavailable — comparable deal analysis skipped]

---

## Key unknowns
[Fields flagged "Not stated" and why they matter for the decision]

---

## Recommended next steps
[If pursuing: specific questions to ask, what to validate in discovery]
[If declining: brief note on why, and whether to refer elsewhere]
```

---

## Step 7 — Optional: create HubSpot deal

If the recommendation is PURSUE or PURSUE WITH CONDITIONS, offer:

> "Would you like me to create a HubSpot deal for this prospect?"

If yes:

```
HubSpot:manage_crm_objects
  objectType: deals
  action: create
  properties:
    dealname: "[Company Name] — [Project type from RFP]"
    pipeline: "default"
    dealstage: "appointmentscheduled"
    amount: [budget figure if stated, else leave blank]
    closedate: [expected close if stated]
    description: "ICP score: [score]/10. [1-sentence summary of fit.]"
```

Confirm the deal URL to the user once created.

---

## Error handling

| Error | Action |
|-------|--------|
| PDF unreadable | Ask user to paste key sections: scope, budget, timeline, tech stack |
| Google Drive file not found | Ask user to check sharing permissions or paste content |
| HubSpot unavailable | Skip Steps 3 and 7; note in report |
| No budget stated | Score commercial fit conservatively; flag as key unknown |
| Ambiguous tech stack | Score conservatively; flag for discovery call |
