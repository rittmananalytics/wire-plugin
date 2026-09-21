---
engagement_name: "{{ENGAGEMENT_NAME}}"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
engagement_lead: "{{ENGAGEMENT_LEAD}}"
repo_mode: "{{REPO_MODE}}"  # combined | dedicated_delivery

# If repo_mode is dedicated_delivery, provide client repo details:
client_repo:
  github_url: null
  local_path: null
  default_branch: "main"

docstore:
  provider: null  # confluence | notion | both | null
  confluence:
    space_key: null
    parent_page_url: null
  notion:
    parent_page_url: null

data_model_registry:
  vertical: null  # any directory name under the registry's verticals/ (13 at the time
                  # of writing). Run `ls ~/.wire/data-model-registry/verticals/` for
                  # the current set, or leave null.
                  # May be a confident match, or the closest adjacent match when no vertical is an
                  # exact industry fit (e.g. subscription-commerce for a SaaS client's MRR/NRR model).
                  # Advisory only — see wire/schemas/data-model-registry.md. null (the default)
                  # means data_model-generate/validate behave exactly as if this didn't exist.
  cross_vertical_schemas: []  # e.g. [crm_identity_resolution, finance_revenue_recognition] — accepted independently
                  # of any vertical match; a client can need these whether or not `vertical` above is set.

# How Wire is driven on this engagement (specs/utils/director_operating_model.md).
#   orchestrated — the release-director skill turns your direction into Wire
#                  command runs, dispatches lanes, and stops at decisions. The
#                  default on Claude Code. Typed commands keep working.
#   manual       — today's behaviour: /wire:start prints the next action and
#                  stops, you type the commands. Use it for client-side teams
#                  and regulated engagements.
# Per-session override: say "you drive" to hand control back for that session.
# Gemini CLI resolves to manual regardless: it has no skills or agents.
orchestration:
  mode: orchestrated  # orchestrated | manual

fathom_sync:
  enabled: {{FATHOM_SYNC_ENABLED}}  # true | false — resolved at /wire:new Step 2 from the client domain given;
                  # false if no domain was given, or if the domain/client_name looked like an internal RA
                  # engagement (Fathom Sync refuses to enable itself in that case — see fathom_sync.md).
  client_domain: {{FATHOM_SYNC_CLIENT_DOMAIN}}  # required for enabled: true — matches calendar invitees on each
                  # call, so only meetings this specific client attended get pulled in. Never rittmananalytics.com.
  last_synced: null    # ISO date; updated automatically after each sync, drives the incremental --after window
---

# Engagement Context: {{ENGAGEMENT_NAME}}

**Client**: {{CLIENT_NAME}}
**Engagement Lead**: {{ENGAGEMENT_LEAD}}
**Created**: {{CREATED_DATE}}
**Repo mode**: {{REPO_MODE}}

---

## Engagement Overview

[1–3 paragraphs describing the engagement: what the client does, why they engaged Rittman Analytics, and what the broad goal is.]

## Business Objectives

1. [Primary objective]
2. [Secondary objective]
3. [Additional objective if applicable]

## Key Stakeholders

| Name | Role | Responsibilities | Contact |
|------|------|------------------|---------|
| [name] | [role] | [what they are accountable for] | [email or Slack] |
| [name] | [role] | [what they are accountable for] | [email or Slack] |

## Current State Architecture

[Brief description of the client's current data infrastructure — what they have today. Include key systems, data volumes, and any known constraints.]

**Key systems**:
- [System 1]: [brief description]
- [System 2]: [brief description]

## Engagement Releases

| # | Release Name | Type | Status | Start | End |
|---|-------------|------|--------|-------|-----|
| 01 | Discovery | discovery | In progress | {{CREATED_DATE}} | |

## SOW Reference

Statement of Work: `engagement/sow.md` (if available)

[Note any key contract terms, budget ceiling, payment milestones, or compliance requirements.]

## Working Agreements

[Any working patterns, meeting cadence, communication preferences, or team norms agreed with the client.]

- **Meeting cadence**: [e.g. Weekly status call, Tuesday 10am]
- **Primary contact**: [who to reach for decisions]
- **Code review**: [process for reviewing and approving deliverables]
- **Access provisioning**: [how the team gets access to client systems]

## Client Repo Details

{{#if repo_mode == "dedicated_delivery"}}
This engagement uses a dedicated delivery repo. The client's code repo is separate:

- **GitHub URL**: {{client_repo.github_url}}
- **Local path**: {{client_repo.local_path}}
- **Default branch**: {{client_repo.default_branch}}

Wire commands that need to reference or modify client code should use this repo path.
{{else}}
This engagement uses the combined client + delivery repo. The `.wire/` folder lives directly in the client's code repo.
{{/if}}

## Notes

[Any other context relevant to the engagement that doesn't fit the sections above.]
