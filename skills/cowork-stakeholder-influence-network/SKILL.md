---
name: cowork-stakeholder-influence-network
description: >
  Builds an interactive stakeholder influence network for any active Rittman
  Analytics client engagement, mapping every named stakeholder's impact on
  delivery velocity and cycle times. Use whenever the user asks to analyse
  stakeholders, map influence, identify blockers, understand who to route
  around, understand who is accelerating or slowing delivery, or asks "who
  should we influence on [client]?". Also triggers on "account health",
  "stakeholder map", "who's blocking us", "delivery network", or "influence
  analysis" for any client. Output is a fully interactive full-screen HTML
  dashboard with a force-directed graph, classification filters, and a
  slide-in detail panel.
platform: cowork
connectors:
  required: [looker, slack]
  optional: [fathom]
triggers:
  - "analyse stakeholders for [client]"
  - "stakeholder map for [client]"
  - "who should we influence on [client]?"
  - "who's blocking us on [client]?"
  - "influence analysis for [client]"
  - "delivery network for [client]"
  - "account health for [client]"
---

# Stakeholder Influence Network

Produces an interactive HTML influence-network dashboard for any RA client
engagement, synthesising data from Looker (meeting records, contacts, RAG
status), Slack (internal and client channels), and Fathom (meeting transcripts)
to classify every stakeholder as Accelerator, Friction Point, Blocker, or
Peripheral — and prescribe targeted actions for each.

Each stakeholder is also classified by **velocity role**: whether they are a
causal driver of velocity outcomes, a reporter who flags issues without being
the root cause, or both.

---

## Connector guard

Before proceeding, verify:
- **Looker** is connected: attempt `Looker:query` with a minimal test query.
  If unavailable, stop and ask the user to connect Looker in Settings → Connectors.
- **Slack** is connected: attempt `Slack:search_channels`. If unavailable,
  note the gap and proceed with Looker and Fathom data only.
- **Fathom** (optional): attempt `Fathom:search_meetings`. Skip gracefully
  if unavailable.

---

## Step 0 — Identify the client

If the user has not specified a client name, ask for one before proceeding.
Derive:

| Variable | Derivation |
|----------|-----------|
| `CLIENT_NAME` | Exact name as used in Looker (e.g. "Booksy") |
| `CLIENT_DOMAIN` | Primary email domain (e.g. "booksy.com") — infer if obvious, else ask |
| `SLACK_SLUG` | Lowercase hyphenated slug — used for `#clients-{slug}` and `#clients-{slug}-internal` |

---

## Step 1 — Gather data in parallel

Run all three data-gathering steps simultaneously.

### 1a. Looker — meeting sentiment and stakeholder data

**Meeting + attendee query:**
```
Looker:query
  model: analytics
  explore: companies_dim
  fields: [
    customer_meetings.meeting_title,
    customer_meetings.meeting_summary,
    customer_meetings.contribution_sentiment_category,
    customer_meeting_attendees.contact_name
  ]
  filters: { "companies_dim.company_name": "<CLIENT_NAME>" }
  limit: 100
```

**Contacts and influencer data:**
```
Looker:query
  model: analytics
  explore: companies_dim
  fields: [
    contacts.contact_name,
    contacts.contact_influencer_score,
    contacts.contact_influencer_type,
    contacts.contact_seniority,
    contacts.contact_title
  ]
  filters: { "companies_dim.company_name": "<CLIENT_NAME>" }
  limit: 50
```

**RAG / engagement status:**
```
Looker:query
  model: analytics
  explore: companies_dim
  fields: [
    timesheet_project_engagement_rag_status_fact.engagement_name,
    timesheet_project_engagement_rag_status_fact.overall_rag_status,
    timesheet_project_engagement_rag_status_fact.schedule_rag_status,
    timesheet_project_engagement_rag_status_fact.scope_rag_status,
    timesheet_project_engagement_rag_status_fact.resourcing_rag_status,
    timesheet_project_engagement_rag_status_fact.technology_rag_status
  ]
  filters: { "companies_dim.company_name": "<CLIENT_NAME>" }
  limit: 20
```

If a 400 error occurs on the RAG query, remove the `action_point` fields and
retry. Treat null contact influencer scores as "data unavailable" — continue.

### 1b. Slack — channel messages

```
Slack:search_channels
  query: [SLACK_SLUG]
```

For each channel found (`#clients-{slug}` and `#clients-{slug}-internal`):

```
Slack:read_channel
  channel_id: [channel id]
  limit: 60
  response_format: "concise"
```

Extract: named stakeholders, blocker/friction language, positive signals,
escalation patterns. Skip gracefully if channels are not found.

### 1c. Fathom — meeting search

```
Fathom:search_meetings
  search_term: [CLIENT_NAME] stakeholder delivery
```

Skip gracefully if Fathom returns an error.

---

## Step 2 — Build the stakeholder model

From all gathered data, construct a list of named individuals. For each person
derive:

| Field | Source |
|-------|--------|
| `name` | Meeting attendees / Slack mentions |
| `role` | Meeting context / Slack intro messages |
| `type` | `"ra"` for RA staff, `"client"` otherwise |
| `meetings` | Count of distinct meetings |
| `meetings_list` | Array of `{name, sentiment}` — sentiment: POSITIVE / CONCERNED / UNENGAGED / neutral |
| `sentiment` | Modal sentiment across meetings |
| `classification` | See classification rules below |
| `velocity_role` | `"driver"`, `"reporter"`, or `"both"` |
| `influence` | 1–10 float |
| `velocity_impact` | 1–10 int |
| `cycle_impact` | 1–10 int |
| `signals` | 3–5 bullet strings — prefix ⚠️ for risks, 🔑 for key insights |
| `actions` | 2–4 recommended actions |

### Classification rules

| Classification | Criteria |
|----------------|---------|
| `accelerator` | Consistently POSITIVE sentiment, unblocks access/decisions, praised by team, approves roadmap |
| `friction` | Mixed or CONCERNED sentiment, causes rework through unclear ownership, availability gaps, or changing requirements |
| `blocker` | CONCERNED or UNENGAGED combined with high seniority/sponsorship; strategic risk if not managed; or explicitly flagged in internal Slack |
| `peripheral` | Low meeting count, UNENGAGED sentiment, limited decision authority |

RA staff are always classified as `accelerator` — their signals and actions
should reflect how to navigate the client landscape, not penalise them.

### Velocity role rules

| `velocity_role` | Criteria |
|-----------------|---------|
| `"driver"` | Their decisions or actions directly cause velocity to increase or decrease — access gatekeeper, scope approver, PR/MR reviewer, product owner |
| `"reporter"` | They observe and escalate velocity concerns but are not the root cause |
| `"both"` | They are simultaneously a causal factor AND an active reporter of the same issues |

**Key rule**: if fixing the stakeholder's concern requires acting on a
*different* node in the graph, they are a reporter. If fixing it requires
changing what *they* do, they are a driver.

RA staff are always `"driver"`.

---

## Step 3 — Generate the HTML dashboard

Produce a single self-contained HTML file using D3.js v7 from cdnjs. The graph
occupies the full browser window with floating overlays. All JavaScript is
inline; Google Fonts is the only external dependency beyond D3.

### Layout

- **Floating title card** — top-left, frosted glass (`rgba(255,255,255,0.93)` + `backdrop-filter: blur(8px)`)
- **Floating legend** — bottom-left, same frosted glass style; classification section (clickable filter) + velocity role section (read-only)
- **Slide-in modal panel** — 400px, slides from right on node click; closes via ✕ or backdrop click

### Velocity role visual encoding

| `velocity_role` | Visual |
|-----------------|--------|
| `"driver"` | Solid border (stroke-width 2), no outer ring |
| `"reporter"` | Dashed main circle only (stroke-dasharray "5,3", stroke-width 1.3), no outer ring |
| `"both"` | Solid main circle (stroke-width 2) plus a separate dashed outer ring (r+7px, stroke-dasharray "4,3", opacity 0.55) |

**Critical**: render the outer dashed ring only for `velocity_role === 'both'`,
never for `"reporter"`. The double-hatch bug occurs when both styles are
applied to the same node.

### Node colours

- Accelerator: `#16a34a`
- Friction: `#d97706`
- Blocker: `#dc2626`
- Peripheral: `#8a91a8`
- RA Team: `#2563eb`

### Modal panel content

- Name, role
- Two badges side-by-side: classification + velocity role with one-line description
- Velocity role badge colours: driver `#2563eb`, reporter `#7c3aed`, both `#0891b2`
- Three stat blocks: meetings count, velocity impact (N/10), cycle time risk (N/10)
- Delivery signals list (⚠️/🔑 prefixed)
- Recommended actions (numbered)
- Meeting history tags (colour-coded by sentiment)

### Technical requirements

- `getDims()` must use `window.innerWidth` / `window.innerHeight`, not container dimensions
- `forceLink` distance 110/140/170 by strength; `forceManyBody` −420; `forceCollide` nodeRadius+18
- Every node requires `velocity_role` field
- All link `source`/`target` IDs must exist in `nodes` — no orphaned edges
- Classification filter must work: legend items fade nodes/links, last-class guard active

---

## Step 4 — Save and present the output

Save the HTML file to the working outputs directory as
`{client-slug}-influence-network.html`.

In **Cowork**: use `mcp__cowork__present_files` to share the file with the user.
In **Claude.ai without Cowork**: present the HTML content inline or offer a
download link if file saving is available.

Follow the file with a **strategic read** in plain prose (no bullet lists):

1. **Who to influence** — top 2–3 accelerators and why they matter
2. **Who to route around** — blockers/friction points and the specific delay mechanism
3. **Reporter vs driver** — who is reporting problems they don't own vs who actually owns the fix
4. **Systemic picture** — the underlying pattern (ownership gaps, access delays, metric ambiguity)

3–5 sentences per section.

---

## Quality checklist before outputting

- [ ] Every person in meeting attendee data has a node
- [ ] Every link source/target ID exists in nodes — no orphaned edges
- [ ] No duplicate node IDs
- [ ] At least one RA team node present
- [ ] Every node has `velocity_role` of `"driver"`, `"reporter"`, or `"both"`
- [ ] Outer dashed ring rendered only for `velocity_role === 'both'`, never `"reporter"`
- [ ] Classification justified by at least one data signal
- [ ] Classification filter works — legend items fade nodes/links, last-class guard active
- [ ] Modal opens on click, closes on ✕ and backdrop click
- [ ] All recommended actions are specific and actionable
- [ ] HTML renders without console errors

---

## Common error handling

| Error | Action |
|-------|--------|
| Looker 400 on `action_point` fields | Remove those fields and rerun |
| Looker returns all-null contacts | Note "influencer scores unavailable"; infer from meeting data |
| Slack channel not found | Skip gracefully |
| Fathom error | Skip gracefully; build from Looker + Slack alone |
| Client name not found in Looker | Try partial match (e.g. `%Booksy%`); then ask user |
