# Client Directory

Quick-reference mapping of active Rittman Analytics client engagements to their data sources. Use this to avoid asking Mark to clarify which channel or domain to look in.

When a client is mentioned that isn't on this list, ask Mark to confirm the domain and Slack channel pattern, then proceed.

## Active engagements (as of May 2026)

### Client A
- **Domain:** Confirm via Mark
- **External Slack channel:** Confirm via `slack_search_channels`
- **Internal Slack channel:** Confirm via `slack_search_channels`
- **Jira project key:** Confirm via Mark
- **Delivery lead:** Confirm via Mark
- **Engagement summary:** Legacy BI platform → GCP / BigQuery / dbt / Looker migration. Phase 2 in progress. Six-month engagement with two cycles, four primary milestones (Sales & Trading, Customer Acquisition, Lifetime Value, Core Trading Migration).
- **Key stakeholders:** Confirm via Mark.

### Client B
- **Domain:** Confirm via Mark
- **External Slack channel:** Confirm via `slack_search_channels`
- **Internal Slack channel:** Confirm via `slack_search_channels`
- **Jira project key:** Confirm via Mark
- **Delivery lead:** Confirm via Mark
- **Engagement summary:** Existing analytics work, currently extending. Wire Framework rolled out to internal team. Renewal under discussion.
- **Key stakeholders:** Confirm via Mark.

### Client C (Project Alpha)
- **Domain:** Confirm via Mark
- **External Slack channel:** Confirm via search
- **Internal Slack channel:** Confirm via search
- **Jira project key:** Confirm via Mark
- **Delivery lead:** Lewis Baker is the commercial owner; contractor staffing confirmed separately.
- **Engagement summary:** Large-scale cloud data migration. Snowflake → BigQuery, Tableau/Metabase → Looker. 1500+ dbt models, 134 Fivetran connectors. Major engagement. Multiple discovery sessions scheduled.
- **Notes:** This is currently in mobilisation. Delivery status reports may be premature; sprint cadence not yet established.

### Client D
- **Domain:** Confirm via Mark
- **External Slack channel:** Confirm via `slack_search_channels`
- **Internal Slack channel:** Confirm via `slack_search_channels`
- **Delivery lead:** Confirm via Mark
- **Engagement summary:** Customer acquisition funnel build across two platforms. Discovery completed late March 2026. **Engagement suspended by client on 15 May 2026 with four-week notice period.** Closeout work in progress: Braze ingestion, Zendesk and Dialpad ingestion, knowledge transfer to client engineering, gap-analysis write-up.
- **Key stakeholders:** Confirm via Mark.

### Client E / Boost
- **Domain:** Confirm via Mark
- **Slack channels:** Confirm via search
- **Delivery lead:** Confirm
- **Engagement summary:** Boost revenue analysis, provider portfolio, category mix. Mark uses the `boost-revenue-analyst` skill for ad-hoc analysis here.

### Barton Peveril
- **Domain:** client-bp.example (confirm)
- **Slack channels:** Confirm via search
- **Engagement summary:** Active. Confirm scope.

### Client F
- **Domain:** Confirm via Mark
- **Slack channels:** Confirm via search
- **Delivery lead:** Confirm via Mark
- **Engagement summary:** Active. 4-week delivery plan in motion.

### Client H
- **Slack channels:** Confirm via search
- **Delivery lead:** Confirm via Mark
- **Engagement summary:** Active. Backlog refinement in progress.

### Client I
- **Status:** Possibly kicking off as of mid-May 2026.

### Client J
- **Status:** Workshop planning in progress as of mid-May 2026.

## Internal Slack channels worth checking for any client

- **#shopfloor** — End-of-day updates from delivery leads, structured Move / Stuck / Watch. Always mention client work.
- **#delivery-and-invoicing** — Mark probes ETAs, milestone completion, invoicing readiness here.
- **#tech-discussions** — Methodology questions, cross-team requests for input on technical approach.

## Tool notes

**Fathom is split across two MCP connectors.** This is intentional and not a redundancy:

- `Fathom (Custom)` (the n8n-hosted server) provides `list_meetings` and any other listing/search operations. This is the one to call when you need to find meetings by domain, date range, attendee, or team.
- `Fathom` (the official api.fathom.ai server) provides `get_meeting_transcript`, `get_meeting_summary`, `get_recording_by_url`, `get_recording_by_call_id`, `find_person`, and `list_teams`. This is the one to call once you have a recording_id.

If `list_meetings` errors with a schema mismatch, the wrong connector is being addressed. Use `tool_search` with query "Fathom list meetings" to load both. Both need to be active for the skill to work end-to-end.

## Standard team roster

Knowing who's who avoids confusion when reading transcripts:

- **Mark Rittman** — CEO. The user.
- **Lewis Baker** — Co-director, executive relationships, commercial expansion.
- **Lydia Blackley** — Delivery lead.
- **Olivier Dupuis** — Senior data engineer.
- **Tim Griew** — Senior delivery.
- **Lukasz Aszyk** — Contractor (onboarded mid-May 2026).
- **Saverro Suseno** — Senior data engineer.
- **Alex Caldwell** — Delivery lead.
- **Jordan Ilyat** — Technical lead.
- **Victor** — Data engineer.
- **Ron Sibayan** — Contractor (rolled off mid-May 2026).
- **George Sanderson** — Former team member, left earlier in 2026.

Update this file when Mark mentions new engagements or team changes.
