---
name: cowork-pipeline-report
description: >
  Generates a CEO-level sales pipeline report for Rittman Analytics by pulling
  all active HubSpot deals, Xero confirmed revenue, Harvest time and budget
  data, and Fathom meeting signals. Produces a structured markdown report
  covering pipeline by stage, weighted forecast, at-risk deals, and deal
  momentum. Optionally creates a live Cowork artifact the user can re-open
  each week.

  Use whenever the user asks for "pipeline report", "show me the pipeline",
  "pipeline review", "where are we on sales?", "forecast", "how much pipeline
  do we have?", "at-risk deals", "new business update", or "weekly sales
  summary". Also triggers for phrases like "pipeline health", "sales numbers",
  "revenue forecast", or "what's in the funnel".
platform: cowork
connectors:
  required: [hubspot]
  optional: [xero, harvest, fathom]
triggers:
  - "pipeline report"
  - "show me the pipeline"
  - "sales forecast"
  - "where are we on new business?"
  - "weekly sales summary"
  - "how much pipeline do we have?"
  - "at-risk deals"
  - "pipeline health"
---

# Pipeline Report Skill

Generates a CEO-level pipeline report for Rittman Analytics. Pulls live deal
data from HubSpot, confirmed revenue from Xero, project burn rates from
Harvest, and meeting momentum from Fathom. Produces a structured report with
an optional live Cowork artifact for recurring weekly use.

---

## Connector guard

Before proceeding, verify:
- **HubSpot**: required — call `HubSpot:get_organization_details` to confirm.
  If unavailable, stop and ask the user to connect HubSpot in
  Settings → Connectors.
- **Xero** (optional): call `Xero:get_connected_user_organisation` to confirm.
  Note gap and continue if unavailable.
- **Harvest** (optional): call `Harvest:get_data_of_authenticated_user` to
  confirm. Note gap and continue if unavailable.
- **Fathom** (optional): call `Fathom:list_meetings` with a recent date.
  Note gap and continue if unavailable.

---

## Step 1 — Pull active HubSpot pipeline

```
HubSpot:query_crm_data
  query: "SELECT dealname, dealstage, amount, closedate,
          hs_deal_stage_probability, hubspot_owner_id,
          hs_lastmodifieddate, hs_activity_count
          FROM deals
          WHERE pipeline = 'default'
          AND dealstage != 'closedwon'
          AND dealstage != 'closedlost'"
```

Also pull recent wins and losses (last 90 days):

```
HubSpot:query_crm_data
  query: "SELECT dealname, dealstage, amount, closedate
          FROM deals
          WHERE closedate > [90 days ago]
          AND (dealstage = 'closedwon' OR dealstage = 'closedlost')"
```

---

## Step 2 — Apply stage probability weights

Load weights from `references/stage_weights.md`. Calculate for each deal:

```
weighted_value = amount × stage_probability
days_in_stage = today - last_stage_change_date
```

Flag as at risk if any of:
- No activity logged in >14 days
- Close date has passed without stage change
- Stage probability <30% and close date within 30 days
- Amount not set

---

## Step 3 — Pull Xero confirmed revenue (if available)

```
Xero:get_profit_and_loss
  fromDate: [first day of current financial year]
  toDate: [today]
```

```
Xero:get_contacts_and_receivables
```

Extract:
- YTD confirmed revenue
- Outstanding receivables (total + overdue)
- Run rate vs. prior periods

---

## Step 4 — Pull Harvest active project burn (if available)

```
Harvest:get_data_of_all_projects
  is_active: true
```

For each active project, calculate:
- Budget consumed % = budget_spent / budget_total × 100
- Days remaining vs. budget remaining

Flag projects that are >80% budget consumed but <70% timeline elapsed.

---

## Step 5 — Pull Fathom meeting momentum (if available)

```
Fathom:list_meetings
  created_after: [14 days ago]
```

For deals in the pipeline, check whether any prospect meetings occurred in the
last 14 days. A deal with a recent Fathom meeting has positive momentum. A
deal with no meeting and a close date within 30 days is a concern.

---

## Step 6 — Produce the pipeline report

```markdown
# Rittman Analytics — Pipeline Report
**Report date**: [Today]
**Data sources**: HubSpot ✅ | Xero [✅/⚠️ unavailable] | Harvest [✅/⚠️] | Fathom [✅/⚠️]

---

## Pipeline summary

| Stage | Deals | Total value | Weighted value |
|-------|-------|------------|---------------|
| [Stage 1] | N | £X | £X |
| [Stage 2] | N | £X | £X |
| ... | | | |
| **Total** | **N** | **£X** | **£X** |

**Weighted pipeline**: £[total weighted]
**Unweighted pipeline**: £[total unweighted]

---

## Confirmed revenue (Xero)

**YTD revenue**: £[figure] ([month] YTD)
**Outstanding receivables**: £[figure] (£[overdue] overdue)

[Skip this section if Xero unavailable]

---

## Active delivery (Harvest)

**Active projects**: [N]
**Projects at budget risk** (>80% budget, <70% timeline): [N]

[Skip this section if Harvest unavailable]

---

## Pipeline by deal

| Deal | Stage | Value | Weighted | Close date | Last activity | Flag |
|------|-------|-------|---------|-----------|--------------|------|
| [Name] | [Stage] | £X | £X | [Date] | [N days ago] | ⚠️ at risk / ✅ |

---

## At-risk deals

[For each flagged deal: name, risk reason, recommended action]

---

## Recent wins and losses (last 90 days)

**Won**: [List with values]
**Lost**: [List with values and brief reason if known]

---

## Deal momentum (Fathom)

[For deals with recent meetings: deal name, meeting date, key signals]
[Skip if Fathom unavailable]

---

## CEO summary

[3–5 sentences: total pipeline health, most important deals to close,
key risks, and one recommended action for the week ahead. Concrete and
specific — name the actual deal, the actual risk, the actual action.]
```

---

## Step 7 — Offer a live artifact

After producing the report, offer:

> "Would you like me to create a live pipeline dashboard you can re-open each week?"

If yes, use `mcp__cowork__create_artifact` to create a persistent HTML artifact
that calls HubSpot, Xero, and Harvest on load and renders an auto-refreshing
pipeline view.

Also offer to schedule the report weekly:

> "I can also send this to your Slack DM every Monday morning. Want me to set that up?"

If yes, use the schedule skill to create a recurring Monday task.

---

## Error handling

| Error | Action |
|-------|--------|
| HubSpot returns no open deals | Check pipeline filter; confirm with user which pipeline to use |
| Amount null on many deals | Note as data quality issue; exclude nulls from weighted totals |
| Xero unavailable | Skip revenue section; note in report header |
| Harvest unavailable | Skip delivery section; note in report header |
| Close dates all in past | Flag data quality issue; ask if pipeline needs a cleanup session |
