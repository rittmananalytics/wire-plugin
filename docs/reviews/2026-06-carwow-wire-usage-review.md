# Wire Framework & Claude Code Usage Review — Carwow

**Engagement:** Carwow — data_migration (BigQuery/Looker Migration Programme)
**Review Date:** June 2026 (updated 2026-06-12)
**Period Covered:** 2026-05-18 – 2026-06-11
**Consultants:** Mark Rittman, Lydia Blackley, Alex Caldwell

---

## Contents
1. Executive Summary
2. Engagement Overview
3. Wire Framework Adoption — Quantitative Summary
4. Wire Plugin Version Availability During the Engagement
5. Discovery Phase: Actual vs. Canonical Wire
6. Release-by-Release Wire Usage Analysis
7. Claude Code Prompt Patterns: Before, During and After Wire Commands
8. Gap Analysis: Wire Commands Never Used but Applicable
9. Recurring Manual Patterns — Candidates for New Wire Commands
10. New Activity Since Previous Review (June 12 cut-off context)
11. Recommendations
Appendix: Data Sources

---

## 1. Executive Summary

Wire was adopted on Carwow 24 days into a live engagement, starting on the first day of the paid discovery sprint (2026-05-18). Across 424 Claude Code prompts over 12 active days, 67 were Wire command invocations — a headline adoption rate of **15.8%**. Before using that number to judge adoption quality, one critical context applies: the `platform_migration` release type — the entire command set for audits, migration inventory, strategy, and target setup — did not exist until Wire v3.7.0, released **2026-06-01**. The first 14 active days of this engagement predate the commands that would have been most applicable to it.

The updated dataset (424 rows, up from 372 in the previous review) adds 52 prompts from the afternoon and evening of June 11 — the day v3.8.2 shipped. Those 52 prompts include the clearest Wire signal in the entire dataset: Mark ran the full migration strategy generate → validate → review cycle cleanly, then ran `/wire:upgrade` twice to fix the Jira null-key problem that had plagued the audit phase. Six new Wire command names appear for the first time: `migration-strategy-generate`, `migration-strategy-validate`, `migration-strategy-review`, and `upgrade`. The migration strategy artifact, which the previous review flagged as `not_started`, is now complete and reviewed.

Splitting the period at June 8 makes the adoption picture clearer. Pre-June 8, the team ran 102 prompts across largely discovery sprint work, invoking 14 Wire commands (13.7%). Post-June 8, the rate climbed to 16.5% across 322 prompts and 53 Wire commands — a modest headline change but a step-change in depth. June 11 specifically saw 17 Wire invocations in 81 prompts (21.0%), the highest single-day rate in the dataset, driven by Lydia batching all six audit reviews in under 20 minutes and Mark completing the migration strategy lifecycle.

The persistent issue throughout June 8–11 is Jira and Confluence integration. Across the four-day audit and strategy phase, 61 prompts explicitly requested Jira status transitions or Confluence publication — up from 50 in the previous count, with June 10 alone accounting for 29 of them. The root cause is known: all Jira artifact keys in the release 03 and 04 status.md files were `null`, because the status.md files were created with v3.7.0 before the schema change in v3.7.2 landed. The fix — `/wire:upgrade` — became available on June 11 and was used the same day. The Jira overhead should not recur on new releases created after v3.8.2.

The most notable new finding from the extended data: at 23:00 on June 11, Mark was running an actual data migration test — reading from Carwow's Snowflake, writing to a GCS bucket (`ra_cw_test`) in RA's GCP project. The dataset captures the beginning of that session, including the explicit safety guardrail (`'DO NOT, UNDER ANY CIRCUMSTANCES, WRITE DATA TO CARWOW'S SNOWFLAKE DB, OR THEIR GCP PROJECT'`). The engagement has moved from audit and planning into active data movement. No Wire command for dbt migration execution existed at the time; that remains a framework coverage gap.

Top three recommendations remain unchanged but with updated evidence: fix Jira auto-sync by enforcing key population at `/wire:new` time (the `/wire:upgrade` command now provides a retrospective fix but should not be needed for new releases); add `/wire:lineage-generate` to the migration playbook template (18 prompts of manual HTML iteration, still not resolved); surface `/wire:findings-playback-generate` as a required next step when `discovery_analyses.validate = complete`.

---

## 2. Engagement Overview

### Client & Scope

Carwow Limited is migrating a 210–240 TB Snowflake warehouse to BigQuery as part of a Google-funded Professional Services Fund deal. The project has two parallel tracks: a "lift and shift" of the existing gold layer to meet the August 2026 Snowflake contract renewal deadline, and a longer-horizon reimagination of the platform with a governed semantic layer and Looker BI. Rittman Analytics holds the engagement under a fixed-price Supply of Services Agreement dated 8 May 2026, with Becky Allsop (Director of Analytics & Data Science) as the client representative.

The engagement is technically complex: ~1,800 dbt models, 544 Hightouch reverse-ETL syncs, Airflow orchestration on Heroku, and a private-network connectivity requirement served via MCP tunnel. Discovery revealed significant internal misalignment at Carwow — no central data team, no canonical KPI definitions, and fragmented ownership across 17 business domains — which prompted a 10-day discovery sprint to stabilise scope before build began.

### Technology Stack

| Layer | Technology |
|---|---|
| Data Warehouse (source) | Snowflake (AWS-hosted, 210–240 TB) |
| Data Warehouse (target) | Google BigQuery |
| Transformation | dbt Core (current: ~1,800 models) |
| Ingestion | Fivetran (~169 connectors), Airflow custom pipelines |
| Reverse ETL | Hightouch (544 syncs, 3-tier classification) |
| Orchestration | Apache Airflow (Heroku-hosted) → Cloud Composer |
| BI | Metabase (current) → Looker (target) |
| Infrastructure | GCP (pilot-grade BigQuery project in progress) |
| Wire connectivity | Private network MCP tunnel (Fivetran MCP Server on Cloud Run) |

### Delivery Releases

| # | Name | Type | Status | Scope |
|---|---|---|---|---|
| 01-discovery | Initial Discovery | discovery | Partial — problem_definition done, pitch/brief/sprint_plan pending | Problem definition, pitch prep, initial SOW |
| 02-discovery_sprint | Discovery Sprint | sop_discovery | In progress — engagement_brief, stakeholder_map, requirements_matrix, discovery_analyses done; findings_playback and delivery_roadmap pending | 6 domain workshops, 131 requirements, discovery analyses |
| 03-phase_1_lift_and_shift | Phase 1 Migration | platform_migration | Created, all 13 migration artifacts not_started, Jira not connected | Full Snowflake → BigQuery migration (created as placeholder) |
| 04-lift-and-shift-pilot | Pilot | platform_migration | Active on feature branch — all 6 audits done/reviewed, migration_inventory done, migration_strategy generate/validate/review complete as of 2026-06-11 | 3-week pilot covering a representative slice of models and Hightouch syncs |

### Key Stakeholders

| Name | Role | Organisation |
|---|---|---|
| Becky Allsop | Director of Analytics & Data Science | Carwow |
| Steph Giles | Data Lead / Platform Owner | Carwow |
| Jairo Reyes | Data Engineer (Carwow-side GCP setup) | Carwow |
| Mark Rittman | Engagement Lead / Tech Lead | Rittman Analytics |
| Lydia Blackley | Dev Lead | Rittman Analytics |
| Alex Caldwell | Analytics Engineer | Rittman Analytics |
| Mike Howarth | Contract PM | Rittman Analytics (contractor) |

---

## 3. Wire Framework Adoption — Quantitative Summary

### Overall Statistics

| Metric | Value |
|---|---|
| Total prompts | 424 |
| Active days | 12 |
| Date range | 2026-05-18 → 2026-06-11 |
| Distinct consultants | 3 (Mark Rittman, Lydia Blackley, Alex Caldwell) |
| Wire command invocations | 67 |
| **Wire adoption % (full period)** | **15.8%** |
| Jira/Confluence manual prompts | 61 |
| Git commit/push manual prompts | 17 |
| Plugin install/reload prompts | 48 |

### Consultant-Level Breakdown

| Consultant | Total prompts | Wire commands | Wire % |
|---|---|---|---|
| Mark Rittman | 267 | 39 | 14.6% |
| Lydia Blackley | 140 | 21 | 15.0% |
| Alex Caldwell | 17 | 7 | 41.2% |

Alex's 41.2% rate is not a large sample (17 prompts, single session on June 9), but the pattern is instructive: he came in cold on an active engagement, ran `/wire:new`, then executed a full security-audit generate → validate cycle, followed by `/wire:status`, `/wire:start`, and `/wire:plan`. Seven Wire commands in one session, mostly in sequence, with minimal non-Wire overhead. That is the target pattern.

### Pre/Post-June 8 Split

June 8 marks the start of team-wide, parallel Wire usage for the migration audit phase and the release of Wire v3.7.7 (Snowflake + Hightouch support).

| Period | Dates | Prompts | Wire commands | Adoption % | Active consultants |
|---|---|---|---|---|---|
| **Pre-June 8** | 2026-05-18 → 2026-06-07 | 102 | 14 | 13.7% | Lydia (primary), Mark |
| **June 8–11** | 2026-06-08 → 2026-06-11 | 322 | 53 | 16.5% | Mark, Lydia, Alex |

The June 8–11 column now reflects the full picture: 52 prompts were added in the updated telemetry cut (afternoon/evening of June 11), adding 8 new Wire commands. The pre-June 8 figures are unchanged.

**Pre-June 8 breakdown**: Of the 88 non-Wire prompts, the split by category is:

| Category | Prompts | Wire command available? |
|---|---|---|
| Plugin install/reload loop | 34 | No command — UX issue |
| Migration planning / Gantt CSV iteration | 27 | **No** — `/wire:delivery-roadmap-generate` is a sop_discovery artifact; no migration execution planning command existed in any version |
| SOW/technical design doc drafting | 18 | Partial — `/wire:requirements-generate` existed but for a different artifact type |
| Discovery analyses review (Lydia) | 5 | **Yes** — `/wire:status` and `/wire:discovery-analyses-validate` both available; missed |
| MCP connection verification (pre-audit) | 4 | No command |
| Total | 88 | |

**Post-June 8 breakdown**: Of the 269 non-Wire prompts in this period:

| Category | Prompts | Wire command available? |
|---|---|---|
| Jira ticket management | 61 | **Yes** — `/wire:utils-jira-sync` existed; auto-sync broken due to null keys in status.md (fixed by `/wire:upgrade` on June 11) |
| Git commit/push | 17 | **No** — Wire never auto-commits |
| Lineage HTML iteration | 18 | **Yes** — `/wire:lineage-generate` released June 6; command existed but unused |
| Plugin/MCP state checks | 15 | No command — diagnostic prompts |
| Pilot scope & SOW decisions | 42 | Partial — judgement calls |
| Post-Wire enrichment (playbook, plans) | 30 | Partial — content quality, not missing commands |
| Migration strategy discussion (Lydia, morning Jun 11) | 9 | **Yes** — available, formatting errors prevented recognition |
| Target setup investigation (Lydia, afternoon Jun 11) | 15 | **Yes** — `/wire:target-setup-generate` available since v3.7.0 |
| Data migration test prep (Mark, evening Jun 11) | 9 | Partial — no Wire command for dbt migration execution |
| Misc context / questions | 53 | No |
| Total | 269 | |

### Wire Commands Actually Used

| Command | Count | Notes |
|---|---|---|
| /wire:engagement-brief-validate | 5 | Multiple runs including re-runs after install issues |
| /wire:migration-inventory-generate | 5 | Run twice on 06-09 (project ID correction), regenerated 06-11 |
| /wire:status | 4 | Used correctly by Alex on first day; underused by Lydia |
| /wire:new | 3 | Releases 02, 03, and 04 |
| /wire:security-audit-generate | 3 | Alex ran this correctly on first session |
| /wire:start | 3 | Alex (orientation sequence, 06-09); Mark (06-11, twice) |
| /wire:stakeholder-map-generate | 2 | Lydia, 05-18 and 05-21 |
| /wire:stakeholder-map-validate | 2 | One clean, one without project ID |
| /wire:playbook-generate | 2 | Releases 03 and 04 |
| /wire:dbt-audit-generate | 2 | Including one with wrong release ID (corrected) |
| /wire:dbt-audit-validate | 2 | |
| /wire:orchestration-audit-validate | 2 | |
| /wire:db-object-audit-generate | 2 | |
| /wire:db-object-audit-validate | 2 | |
| /wire:security-audit-validate | 2 | |
| /wire:migration-inventory-validate | 2 | |
| /wire:security-audit-review | 2 | |
| /wire:migration-strategy-validate | 2 | Mark, 06-11 (validate → review → re-validate sequence) |
| /wire:upgrade | 2 | Mark, 06-11 (21:26 and 23:07 — both targeting release 04) |
| /wire:engagement-brief-review | 1 | |
| /wire:discovery-analyses-generate | 1 | |
| /wire:requirements-matrix-review | 1 | |
| /wire:orchestration-audit-generate | 1 | |
| /wire:orchestration-audit-review | 1 | |
| /wire:reverse-etl-audit-generate | 1 | |
| /wire:reverse-etl-audit-validate | 1 | |
| /wire:ingest-audit-generate | 1 | Wrong command name — should be ingestion-audit-generate |
| /wire:ingestion-audit-generate | 1 | Correct command, after correction |
| /wire:db-audit-generate | 1 | Wrong command name — should be db-object-audit-generate |
| /wire:ingestion-audit-review | 1 | |
| /wire:dbt-audit-review | 1 | |
| /wire:db-object-audit-review | 1 | |
| /wire:reverse-etl-audit-review | 1 | |
| /wire:orchestration-review | 1 | Wrong name — should be orchestration-audit-review |
| /wire:migration-strategy-generate | 1 | Mark, 06-11 (17:20 — third attempt, first clean invocation) |
| /wire:migration-strategy-review | 1 | Mark, 06-11 (17:36) |
| /wire:plan | 1 | Alex, orientation sequence |

**Total unique command names used**: 37 (of which 4 were wrong/deprecated names). New since previous review: `migration-strategy-generate`, `migration-strategy-validate`, `migration-strategy-review`, `upgrade`.

### Observations on Command Namespace

Three naming errors appear: `/wire:ingest-audit-generate` (correct: ingestion-audit-generate), `/wire:db-audit-generate` (correct: db-object-audit-generate), `/wire:orchestration-review` (correct: orchestration-audit-review). Mark corrected the first two immediately. The `audit` infix is not recalled reliably under pressure.

Two formatting failures prevented command recognition: Lydia's backtick-wrapped `` `/wire:migration-strategy-validate 04-lift-and-shift-pilot` `` and plain `/wire:migration-strategy-generate` without a project ID were not executed as Wire commands. The second of these was then successfully re-run by Mark in the same afternoon session, with the correct project ID and a note about the updated plugin.

---

## 4. Wire Plugin Version Availability During the Engagement

The Carwow delivery repo's `.claude/settings.json` carries no version pin (`"wire@wire": true`), meaning the team ran whatever was the current published plugin at each session. The Wire framework was released frequently during this engagement — 18 versions between May 12 and June 11 — and several of those releases added commands directly applicable to Carwow work.

| Wire version | Release date | Key addition relevant to Carwow | Available for Carwow sessions |
|---|---|---|---|
| v3.4.21 | 2026-05-12 | Fixed install docs: `/reload-plugins` (not "restart Claude Code") | Pre-engagement; explains Lydia's install loop — docs had been wrong until 6 days before kickoff |
| v3.5.0 | 2026-05-14 | `sop_discovery` release type: 21 commands including findings-playback, delivery-roadmap | From 2026-05-18 onwards ✓ |
| v3.5.2 | 2026-05-14 | `/wire:playbook-generate` | From 2026-05-18 onwards ✓ |
| v3.5.3 | 2026-05-16 | `/wire:adopt` | From 2026-05-18 onwards ✓ |
| **v3.7.0** | **2026-06-01** | **`platform_migration` release type — 42 new commands** | **From 2026-06-01 onwards** — not available for any pre-June session |
| v3.7.2 | 2026-06-05 | Jira single-issue structure option; changed `jira_sync.md` transition logic | From 2026-06-08 onwards — status.md for release 03 was created on 2026-06-01 *before* this shipped |
| v3.7.5 | **2026-06-06** | **`/wire:lineage-generate`** | Available from 2026-06-08 ✓ — but 18 prompts of manual lineage work done on 2026-06-08/09 |
| **v3.7.7** | **2026-06-08** | **Hightouch reverse-etl-audit as sixth audit type**; Snowflake skills | Released same day as first team-wide audit session — adopted same day ✓ |
| v3.7.8 | 2026-06-08 | Hightouch Git repo as audit data source | Same day — used immediately |
| v3.7.9 | 2026-06-10 | platform_migration hardening: row-level checksums, AI-translation safeguards | Available 2026-06-10 |
| **v3.8.2** | **2026-06-11** | **`/wire:upgrade`** — schema migration for existing releases; fixes null Jira keys | Released 2026-06-11; used twice that evening |

### Key implications

**The platform_migration command set was available for only 10 of the 25 engagement days captured.** Pre-June 8 non-Wire prompts for migration audit, inventory, and planning work are not evidence of adoption failure — the commands didn't exist.

**The reverse-etl-audit commands (v3.7.7) were adopted within hours of release.** The Hightouch audit ran on June 8, the same day v3.7.7 shipped.

**The `/wire:upgrade` command resolved the Jira null-key problem the same day it shipped.** Mark ran it at 21:26 and again at 23:07 on June 11. Whether those two runs fixed the keys for all artifacts is not confirmed in the telemetry — there are follow-up prompts around 23:00 that suggest the schema migration was still being worked through — but the command was found and used immediately.

**`/wire:lineage-generate` is the one genuine post-June 8 miss.** It shipped June 6, two days before the lineage HTML work began. The playbook was generated June 1, before the command existed, so it had no lineage step. When the audit phase began, consultants worked from the playbook and missed the command entirely.

---

## 5. Discovery Phase: Actual vs. Canonical Wire

### What Was Produced

The following discovery artifacts exist in the delivery repo across releases 01 and 02:

- `problem_definition.md` — generated and validated (01-discovery, 2026-05-12)
- `engagement_brief.md` — generated and validated (02-discovery_sprint)
- `stakeholder_map.md` — generated, validated (failed), reviewed by Becky Allsop (02-discovery_sprint)
- Six stakeholder interview documents — generated and validated across five P1 domain stakeholders
- `requirements_matrix.md` — 131 requirements captured, generated, validated, reviewed
- `discovery_analyses.md` — generated, validated; maturity pinned at "Data Chaos"; 80 Phase 1 must-haves identified

Not produced: `findings_playback.md`, `delivery_roadmap.md` (both `pending` in status.md). No `pitch.md`, `release_brief.md`, or `sprint_plan.md` were generated for release 01.

### Canonical Wire Discovery Flow vs. What Happened

| Wire Artifact | Wire Command | Status | What Actually Happened |
|---|---|---|---|
| problem_definition | /wire:problem-definition-generate | Done (05-12) | Generated before Wire was in active use; no BigQuery telemetry for this date |
| pitch | /wire:pitch-generate | Not started | Created manually as a slide deck (in-person workshop 04-03-2026) |
| release_brief | /wire:release-brief-generate | Not started | SOW served as the release brief |
| sprint_plan | /wire:sprint-plan-generate | Not started | Plan iterated manually in CSV/Mermaid format across 27 prompts |
| engagement_brief | /wire:engagement-brief-generate | Done (05-14) | Run correctly; validated 5 times |
| stakeholder_map | /wire:stakeholder-map-generate | Done (05-18/21) | Validate failed first run; re-run and reviewed |
| stakeholder_interview | /wire:stakeholder-interview-generate | Done (×6) | All six sessions generated and validated |
| requirements_matrix | /wire:requirements-matrix-generate | Done (05-21) | Generated, validated, reviewed |
| discovery_analyses | /wire:discovery-analyses-generate | Done (05-29) | Generated; validate had leading-space formatting issue |
| findings_playback | /wire:findings-playback-generate | Pending | Never run — CAR-234 open |
| delivery_roadmap | /wire:delivery-roadmap-generate | Pending | Never run — 27 prompts of manual plan work instead |

### Root Cause of Discovery Phase Gap

Release 01 predates active Wire adoption. The `context.md` was created on 2026-05-12 and the paid discovery sprint did not start until 2026-05-18. The first six days of Wire telemetry are entirely discovery sprint work. Before that, pitch preparation, SOW negotiation, and initial planning were done without Wire.

Within the telemetry period, the two remaining gaps — `findings_playback` and `delivery_roadmap` — are not timing excuses. Both commands exist, both were applicable, and the manual equivalents consumed significant prompt budget.

### Specific Discovery Phase Gaps

**Findings Playback**: The discovery playback meeting took place on 2 June 2026 (confirmed by Fathom: "CarWow | Discovery Playback | 2026-06-02") but `/wire:findings-playback-generate` was never run. CAR-234 remains open. Given the meeting has happened, this is now retrospective — but the session history should still be captured for the migration strategy artifact.

**Delivery Roadmap**: On 2026-05-31, Mark spent 19 consecutive prompts building a project plan in CSV format, cycling through versions v8–v14 with contingency, resource levelling, and weekly cost breakdowns. He referenced the dbt audit timeline explicitly: `'the "dbt_bigquery_audit.md" Timeline and Sequence recommendations in this file seem completely excessive... If we assumed the use of an LLM and a framework such as https://github.com/rittmananalytics/wire/issues/52, can you please reconsider your timeline'`. The `/wire:delivery-roadmap-generate` command would have produced a structured, validated plan from the audit outputs. It was not invoked. Lydia ran a separate earlier planning session on 2026-05-29, iterating on phase scope and gantt structure.

---

## 6. Release-by-Release Wire Usage Analysis

### Release 01 — discovery

**Wire commands used**: 0 (predates active telemetry period)

**Development approach**: Pre-Wire manual work. Problem definition, pitch deck, SOW, and commercial negotiations all handled outside the framework. Wire setup appears to have been completed on 2026-05-12 in a single session that generated and validated the problem definition, but there is no BigQuery telemetry for this date.

**What worked**: Problem definition was correctly generated and validated. It identified 12 open questions and 3 dependency questions, with OQ-3 and OQ-7 flagged as build blockers. That structure appears to have shaped the discovery sprint scope.

**Gaps**: Pitch, release_brief, and sprint_plan remain pending with no intention to complete them retroactively.

---

### Release 02 — discovery_sprint

**Wire commands used**: 22 (engagement-brief-validate ×5, engagement-brief-review ×1, stakeholder-map-generate ×2, stakeholder-map-validate ×2, discovery-analyses-generate ×1, requirements-matrix-review ×1, status ×1, new ×1, playbook-generate ×1, plus a cluster of validate/review commands on 05-21)

**Development approach**: The most Wire-intensive early period. Lydia drove the majority of this release, with Mark providing planning oversight. The arc was: plugin stabilisation (05-18 to 05-21) → clean Wire execution (05-21 to 05-29) → manual plan work (05-29 to 06-01). Six domain stakeholder interviews were conducted and processed via Wire, producing 131 requirements and a discovery_analyses document that prioritised scope into MoSCoW categories.

**What worked**: The stakeholder interview → requirements_matrix → discovery_analyses chain worked as designed. The requirements matrix's 131 requirements and four-phase MoSCoW breakdown gave the team a defensible basis for scope decisions when the project came under commercial pressure in late May.

**What didn't work**: Lydia's plugin install experience consumed 41 prompts across three sessions before Wire became reliably usable. The validate step on stakeholder_map failed without clear resolution — it was subsequently reviewed without the validate passing, which is out of sequence. `findings_playback` and `delivery_roadmap` were never generated despite being the logical next steps after discovery_analyses was complete.

---

### Release 03 — phase_1_lift_and_shift

**Wire commands used**: 2 (/wire:new, /wire:playbook-generate)

**Development approach**: Created 2026-06-01 as the container for the full migration. Wire was used to initialise the release and generate the playbook. After playbook generation, Mark spent approximately 15 prompts enriching the playbook manually with technical design content, CSV plans, and scope clarifications.

**What worked**: The release structure was set up correctly with the right migration configuration (snowflake → bigquery, airflow, private_network_mcp_tunnel). The playbook provided a useful framework.

**What didn't work**: All 13 Jira artifact keys in status.md are `null`. The Jira project key is also `null`. Despite Jira project CAR being active with relevant issues, Wire's Jira integration was never connected to this release.

---

### Release 04 — lift-and-shift-pilot (feature branch)

**Wire commands used**: ~43 across the full period (all audit generate/validate/review cycles, migration-inventory generate/validate, migration-strategy generate/validate/review, security-audit ×3, db-object-audit ×2, dbt-audit ×2, orchestration-audit ×2, reverse-etl-audit ×2, ingestion-audit ×2, playbook-generate ×1, new ×1, upgrade ×2, start ×2, status ×2)

**Development approach**: The most Wire-intensive release, driven primarily by Mark on 06-08 and 06-09, with Alex joining on 06-09 and Lydia running the review batch on 06-11. The audit phase ran across two intensive days: all six source platform audits generated, validated, and reviewed. Mark used MCP connection verification as a consistent pre-flight before each audit type. Alex's first-day pattern (status → new → audit-generate → audit-validate → status → start → plan) was textbook Wire onboarding.

June 11 saw two distinct sub-phases. Lydia worked through the morning running the audit review batch (all six reviews before 09:00) and the migration inventory generate/validate. She then moved into target setup investigation — working through CAR-246, CAR-247, CAR-250 conversationally rather than running `/wire:target-setup-generate`. Mark took over in the afternoon, ran the full migration strategy lifecycle cleanly (17:20–17:37), then ran `/wire:upgrade` twice in the evening. By 23:00, Mark was actively testing data migration — reading from Snowflake, writing to GCS bucket `ra_cw_test` in RA's test GCP project.

**What worked**: All six audits completed. Migration strategy generated, validated, and reviewed. `/wire:upgrade` used the day it shipped to address the Jira null-key problem. The parallel working model (Mark driving generate/validate, Lydia batching reviews) was efficient.

**What didn't work**: June 10 was entirely non-Wire — 75 prompts, 1 Wire command (`/wire:status`). The day was consumed by CAR-245 (MDS BigLake evaluation note), CAR-272/273/274 Jira updates, pilot lineage view refinement, and Germany SOW review. All legitimate work; none of it routed through Wire commands. Jira management dominated: 29 of 75 June 10 prompts explicitly referenced Jira tickets or Confluence pages. The migration strategy had a false start — Lydia's morning attempt (10:31) was a plain `/wire:migration-strategy-generate` without a project ID, not recognised as a Wire command, then backtick-wrapped at 10:39, also not recognised. Mark completed it cleanly at 17:20 with the full command and context.

---

## 7. Claude Code Prompt Patterns: Before, During and After Wire Commands

### Pre-Wire Preparation Patterns

**Plugin install/reload loop (14 of 67 Wire invocations preceded by install activity)**: Lydia's sessions on 05-18 and 05-20 were dominated by every possible install command variant: `/plugin marketplace add rittmananalytics/wire-plugin`, `/plugin install wire@rittman-analytics`, `/plugin install github:rittmananalytics/wire-plugin`, `/plugin install wire`, and a misspelled `/reload-plugin`. Mark exhibited the same pattern on 06-01 and twice on 06-11: `/plugins` → `/reload-plugins` → `what version of wire are we using?` — the sequence appears three times in the June 11 data alone, at 16:19, 17:17, and 21:25.

**MCP connection verification (8+ audit invocations)**: Mark's pre-audit pattern was consistent: `/mcp` status check → explicit server test (`'please check you can connect via the carwow_fivetran mcp server, and return the set of destinations'`) → Wire command. Appeared before every audit type. Wire's audit-generate step could absorb this as an automatic pre-flight.

**Context injection before playbook (4 invocations)**: Before `/wire:playbook-generate 03-phase_1_lift_and_shift`, Mark manually provided release configuration: `'release name is "phase_1_lift_and_shift". Source platform is snowflake, target is bigquery...'`. Wire's new/playbook flow should infer this from context.md.

### During Wire Command Patterns

The most common during-Wire pattern is incorrect project ID. Mark used `04-lift-and-shift` instead of `04-lift-and-shift-pilot` at least once, corrected immediately. Lydia's uncertainty about the generate→validate→review lifecycle surfaced twice on June 11: `'what is the validate step? Shall i do it for the audits'` (09:46) and `'There is no wire command to validate this document but could you validate it?'` (11:04). Both occurred despite Lydia having used Wire for three weeks and having just run the validate cycle successfully.

### Post-Wire Correction Patterns

**Jira sync failure (most frequent — 61 prompts across the full period, 29 on June 10 alone)**: The clearest post-Wire failure pattern. After nearly every validate and review, one of the team requested Jira status transitions and comment additions manually. Representative verbatim examples: `'why did you not set the status of the related Jira tickets to the correct status mapping for "validate"?'`; `'please update CAR-270 and move into internal_qa, and also sync all the new or updated audit report pages to confluence'`; `'The retl, ingestion, db and security. Check review and ready and move tickets into done'`; `'has the updated migration strategy document been sync'd to Confluence and CAR-275's comments updated to reflect this regeneration and re-validation?'`. June 10 was the peak — a day with almost no Wire commands but 29 Jira/Confluence manual prompts, driven by review feedback cycles on CAR-245, CAR-265, CAR-271, CAR-272, CAR-273, CAR-274.

**Confluence sync requests**: Persistently requested after generate steps: `'yes publish it to confluence'`, `'Can you add this confluence and update the jira ticket'`, `'now commit and push, upload to confluence and put a comment on the ticket and move to internal review'`. The document store provider is configured as `confluence` in both releases 03 and 04 context; the auto-publish trigger is not firing.

**Migration strategy format failures (2 prompts, June 11)**: Lydia's attempt at 10:31 — plain `/wire:migration-strategy-generate` without project ID — and at 10:39 — backtick-wrapped `` `/wire:migration-strategy-validate 04-lift-and-shift-pilot` `` — were both not recognised as Wire commands. Mark successfully ran the full lifecycle three hours later with `'/wire:migration-strategy-generate 04-lift-and-shift-pilot the underlying plugin has been updated and contains canonical snowflake-to-bigquery examples and instructions now'`.

**Commit/push as manual cleanup (~17 prompts)**: Treated as a required manual step by all three consultants: `'commit'`, `'and push to remote'`, `'commit and push, update the ticket to external QA and leave a comment'`. Wire does not auto-commit generated artifacts.

---

## 8. Gap Analysis: Wire Commands Never Used but Applicable

### Category A — Genuine Adoption Gaps (command existed and was applicable)

| Command | Available since | Evidence of manual equivalent | Estimated prompt saving |
|---|---|---|---|
| /wire:lineage-generate | **v3.7.5 (2026-06-06)** | 18 prompts of manual HTML lineage iteration on 2026-06-08/09, two days after the command shipped. Mark: `'With the lineage_view.html file, the the screen is blank'`, `'clicking on a single node doesn't seem to filter the rest of the report'` | ~15 prompts |
| /wire:findings-playback-generate | v3.5.0 (2026-05-14) | Discovery playback meeting ran 2026-06-02; deck prepared manually; CAR-234 open | ~15 prompts |
| /wire:utils-jira-sync | v3.7.0 (2026-06-01) | 61 Jira-management prompts; null Jira keys in status.md meant the utility could not work automatically anyway — fixed by `/wire:upgrade` on June 11 | ~25 prompts net |
| /wire:target-setup-generate | v3.7.0 (2026-06-01) | Lydia worked through CAR-246, CAR-247, CAR-250 conversationally on June 11 afternoon: `'Can I start the taregt setup though the inventory and startgey have not been approved yet?'`, `'Shall I confirm how we will be runnign dbt oauth or service account?'` | ~10 prompts |
| /wire:status (underused by Lydia) | Pre-engagement | Lydia asked open project-state questions on 2026-05-26/27 (`'Have carwow got their gcp project spun up?'`) and manually asked Claude to check Jira backlogs rather than running `/wire:status` | ~4 prompts |
| **Total** | | | **~69 prompts (~16.3% of total dataset)** |

**Why /wire:lineage-generate was missed**: The command shipped June 6. The migration playbook was generated June 1 — five days before — and had no lineage step. Consultants worked from the playbook. This is a surfacing failure, not an awareness failure.

**Why /wire:target-setup-generate was missed**: The artifact was discussed conversationally on June 11 afternoon but was not invoked as a Wire command. Lydia was asking sequencing questions (`'Can I start the taregt setup though the inventory and startgey have not been approved yet?'`) that suggest uncertainty about whether the prerequisite artifacts (migration_strategy) were sufficiently complete. `/wire:status` would have answered this directly.

**Why /wire:utils-jira-sync didn't resolve the Jira problem**: Even if consultants had invoked it explicitly, the status.md for releases 03 and 04 had all Jira artifact keys as `null`. The sync utility can only transition tickets it can identify. `/wire:upgrade` became available on June 11 and was used the same day.

---

### Category B — Product Roadmap Gaps (command existed but covered different artifact)

| Manual work pattern | Closest Wire command | Why it doesn't match | Recommended new command |
|---|---|---|---|
| 27 prompts of migration Gantt / FTE plan iteration (v8–v14), May 29–31 | `/wire:delivery-roadmap-generate` (v3.5.0) | Produces a sop_discovery Build/Pair/Coach delivery option deck — not a migration execution plan with week-by-week resources, Gantt, and contingency | `/wire:migration-plan-generate` (see Section 9) |
| Playbook enrichment after generate (10 prompts, June 1) | `/wire:playbook-generate` (v3.5.2) | Command was run; issue is it didn't auto-ingest discovery artifact context from `.wire/releases/02-discovery_sprint/` | Playbook generate spec needs to auto-read discovery artifacts from prior releases |

---

### Category C — Framework Coverage Gaps (command did not exist at time of use)

| Manual work pattern | Dates | Commands that shipped later |
|---|---|---|
| All migration audit discussions and prep | 2026-05-18 → 2026-05-31 | All 5 audit types — shipped in v3.7.0 on 2026-06-01 |
| Hightouch sync classification and migration planning | 2026-05-26 → 2026-06-09 | `reverse-etl-audit-*` — shipped in v3.7.7 on 2026-06-08 |
| Actual dbt model migration test (Mark, 2026-06-11 23:00+) | 2026-06-11 | No Wire command for dbt migration execution exists in any version — `dbt_migration-generate` spec handles planning not execution |
| Status.md Jira null key problem | 2026-06-08 → 2026-06-11 | `/wire:upgrade` — shipped 2026-06-11 (v3.8.2), used same day |

---

## 9. Recurring Manual Patterns — Candidates for New Wire Commands

### Pattern 1 — Improved Jira auto-sync (existing commands, broken behaviour)

**Evidence**: 61 prompts explicitly requesting Jira status transitions and comment additions after Wire validate and review steps — the single largest category of post-Wire overhead in the dataset. Peak was June 10 with 29 such prompts. Mark: `'why did you not set the status of the related Jira tickets to the correct status mapping for "validate"?'` Lydia: `'The retl, ingestion, db and security. Check review and ready and move tickets into done'`. Alex: `'Can you grab all the comments on the audit docs in confluence/jira so I can see them in one place? There are 6 total'`. Appeared after every audit validate/review cycle across June 8–11.

**Proposed behaviour**: Validate and review steps should automatically identify the relevant Jira task from the release's status.md artifact-key mapping, transition to the correct status (Internal QA for validate-pass, Client QA or Done for review-complete), and add a comment with the Confluence artifact link. Key population at `/wire:new` time should be required, not optional. The `/wire:upgrade` command now exists to fix schema drift in existing releases.

---

### Pattern 2 — `/wire:artifact-sync` (proposed)

**Evidence**: 61 Jira/Confluence manual prompts and 17 commit/push prompts — 78 total "housekeeping" prompts after every substantive Wire execution. Representative verbatim: `'yes publish it to confluence'`, `'commit and push, update the ticket to external QA and leave a comment'`, `'now commit and push, upload to confluence and put a comment on the ticket and move to internal review'`. Appeared after every single audit generate, validate, and review across June 8–11.

**Proposed behaviour**: A single `/wire:artifact-sync <release-id>` command that: (1) commits and pushes all changed artifacts in the release folder, (2) syncs all out-of-date artifacts to Confluence, (3) updates Jira ticket statuses and comments for all artifacts whose status changed since last sync.

---

### Pattern 3 — `/wire:session-start-checklist` (proposed)

**Evidence**: Every session on this engagement began with some combination of plugin verification, `/wire:status`, MCP connection testing, and project-ID recall. The June 11 data is the clearest example: Mark ran the plugin check sequence three separate times in the same day (16:19, 17:17, 21:25) — `'/plugins'` → `'/reload-plugins'` → `'what version of wire are we using?'`. Lydia ran `/mcp` eight times consecutively on June 9 without resolution. Appeared in some form on all 12 active days.

**Proposed behaviour**: At session start, automatically: (1) verify plugin version and display a warning if outdated, (2) check each configured MCP server and report connectivity, (3) display the current release status summary, (4) surface the next pending artifact with the exact command to run it.

---

### Pattern 4 — `/wire:plan-iterate` (proposed)

**Evidence**: 27 prompts of manual Gantt/plan CSV iteration across 05-29 (Lydia) and 05-31 (Mark). Verbatim examples: `'give me a gantt chart with task name, effort (hours), duration (hours), start and end date/time, dependencies and deliverable for the plan, resource-levelling the resources'`; `'Create a new csv file, carwow_plan_v9.csv, with this updated plan'`; `'ok now please create a version of this plan (call it v13_with_contingency) where overall, the project delivery time and hours estimate increases by 22% overall'`; `'Can you remove rows 59,50,7 from teh csv gantt and then updtae timlines'`.

**Proposed behaviour**: A command that takes the current delivery_roadmap artifact and applies a structured change: resource level, add contingency %, remove phases, split tasks. Saves versioned output automatically.

---

### Pattern 5 — Lineage view generation (existing command, not used)

**Evidence**: 18 prompts iterating an interactive HTML data lineage diagram across June 8–9. Mark: `'With the lineage_view.html file, the the screen is blank'`, `'filtering isn't working'`, `'the various nodes aren't grouped within the grouping boxes'`, `'clicking on a node now starts drag-moving it — that's not what we want'`. The `/wire:lineage-generate` command existed and was applicable. The playbook had no lineage step because the command postdated the playbook generation.

**Fix**: Add `/wire:lineage-generate <release-id>` as a step in the migration playbook template after migration-inventory. Update the playbook generate spec to flag new Wire commands that shipped since the playbook was last generated.

---

## 10. New Activity Since Previous Review (June 11 afternoon)

The previous review covered 372 prompts with a data cut-off of 2026-06-11 14:12. The updated dataset adds 53 prompts from June 11 14:12 onward, across two consultants. No prompts exist after June 11. There is no June 12+ activity in the dataset.

### Lydia Blackley — June 11 afternoon (14:12–15:45)

Lydia's session picked up where the morning audit reviews left off, transitioning into target setup investigation and dbt migration preparation.

**Target setup work (conversational — no Wire command)**: Lydia worked through five target-setup-related Jira tickets conversationally. Key prompts verbatim:

- `'Can I start the taregt setup though the inventory and startgey have not been approved yet?'` (14:45) — a sequencing question that `/wire:status` would have answered
- `'Is this now done? https://rittmananalytics.atlassian.net/browse/CAR-247 I can access:https://console.cloud.google.com/bigquery?project=carwow-data-lake'` (14:47)
- `'Do we not have the mcp server created for fivetran? We already have done the ingestion audit?'` (14:50)
- `'Shall I confirm how we will be runnign dbt oauth or service account? Can you see how they currently do it in the dbt folder?'` (14:55)
- `'Where are we writing the translated dbt code, in this repo or anither?'` (15:06)
- `'So, for the pilot keep the code in this repo then for the main project we create a new repo on their instance? Can you create a comment on the ticket to get approval from Jairo'` (15:11)

`/wire:target-setup-generate 04-lift-and-shift-pilot` was available and directly applicable. It was not invoked. Lydia asked four consecutive questions that the Wire artifact would have resolved in one command. This is the clearest single example in the new data of a genuine adoption gap — the command existed (v3.7.0, June 1), the work was directly in scope, and the conversational equivalent consumed ~10 prompts.

**CAR-279 (MDS spike document)**: Lydia completed the MDS BigLake evaluation document and moved CAR-279 to external QA. Key prompts: `'Mark has left comments on the ticket please action them'` (14:12), `'commit and push, update the ticket to external QA and leave a comment'` (14:24). The document was created outside Wire on June 10; the June 11 work was review-response and ticket closure.

**Jira/Slack threads as artifacts**: Lydia loaded a Slack thread as context before migration strategy work: `'Can you read this thread and upload it to this project so we can move onto the next step? https://rittmananalytics.slack.com/archives/C0AFQTGQJAE/p1781188238418419'` (14:40). This pattern — pulling Slack discussion threads into the Wire project as context — is a sensible workaround for the lack of native Slack-to-artifact ingestion in Wire.

### Mark Rittman — June 11 afternoon/evening (15:43–23:47)

Mark's session covers the clearest Wire signal in the updated dataset, followed by the most technically consequential non-Wire work.

**Wire commands run, in sequence**:

1. `/wire:start` (15:43) — no project ID; immediate correction
2. `/wire:start 04-lift-and-shift-pilot` (15:43) — clean
3. Plugin check loop × 2 (16:19–16:20, 17:17–17:19) — `'/plugins'` → `'/reload-plugins'` → `'what version of wire are we using?'`
4. `/wire:migration-strategy-generate 04-lift-and-shift-pilot the underlying plugin has been updated and contains canonical snowflake-to-bigquery examples and instructions now` (17:20) — clean, with context note about the updated plugin
5. `/wire:migration-strategy-validate 04-lift-and-shift-pilot` (17:30) — clean
6. `'with this new plugin, should we run the dbt-audit process again?'` (17:30) — answered yes; a legitimate re-audit question given the v3.8.2 plugin update
7. `/wire:migration-strategy-review 04-lift-and-shift-pilot` (17:36) — clean
8. `/wire:migration-strategy-validate 04-lift-and-shift-pilot` (17:37) — re-validation after review; standard sequence
9. `'has the updated migration strategy document been sync'd to Confluence and CAR-275's comments updated to reflect this regeneration and re-validation?'` (17:40) — the persistent Jira/Confluence gap, immediately post-Wire
10. `/wire:upgrade 04-lift-and-shift-pilot` (21:26) — first run
11. `/wire:upgrade 04-lift-and-shift-pilot` (23:07) — second run

The migration strategy cycle (steps 4–8) is the cleanest Wire execution sequence in the entire dataset for a complex multi-step artifact. Generate, validate, review, re-validate in 17 minutes. The only overhead was the plugin check loop between start and strategy-generate.

**Actual data migration test (23:00–23:47)**: After the second `/wire:upgrade` run, Mark began an actual data migration exercise — reading from Carwow's Snowflake, writing to RA's GCS test bucket. This is the first evidence in the telemetry of the pilot moving from planning into data movement.

Key prompts verbatim:

- (23:00) `'1. cw-test-migration is under RA's GCP organization. 2. Yes it's in this repo, at ./dbt. Also what if we limited this exercise to just the three gold-layer tables + their upstream and downstream depend'`
- (23:11) `'go ahead. The GCS bucket is \`ra_cw_test\`'`
- (23:29) **`'DO NOT, UNDER ANY CIRCUMSTANCES, WRITE DATA TO CARWOW'S SNOWFLAKE DB, OR THEIR GCP PROJECT \`CARWOW-DATA-LAKE\`'`** — a guardrail injected mid-session after what appears to have been an unexpected action by Claude
- (23:31) `'what are you doing?'`
- (23:33) `'read-only is fine, just don't write anything to carwow's systems'`
- (23:40) `'run it step by step, step 1 first'`
- (23:47) `'yes or just test on a small subset of rows'`

The 23:29 prompt is the most operationally significant in the entire dataset. It suggests Claude was about to write data to Carwow's production environment — either Snowflake or the BigQuery project `carwow-data-lake` — and Mark intervened. There is no Wire command that would have prevented this; the guardrail was entirely manual. This is a framework coverage gap: once pilot migration work begins, explicit data-safety constraints (read-only mode, environment separation) need to be codified in the Wire migration spec, not left to ad-hoc prompting.

The session ends with Mark and Claude working step-by-step through what appears to be a small-scale dbt model translation test on `ra_cw_test` — three gold-layer tables, reading from Snowflake, writing to GCS. The telemetry cuts off at 23:47.

---

## 11. Recommendations

**R1 — Fix Jira auto-sync in validate and review steps [High Priority]**

61 prompts explicitly requesting Jira status transitions — the single largest category of post-Wire overhead in the dataset. June 10 alone: 29 such prompts.

*Solution*: (1) Make Jira task key population mandatory at `/wire:new` (fail with an error if Jira is configured but keys are `null`). (2) Add an explicit Jira transition and comment step to the validate and review specs, conditional on the task key being non-null. (3) Run `/wire:upgrade` for all existing releases where keys are null. `/wire:upgrade` now exists and works — the process for retroactive repair is established.

*Spec files*: `wire/specs/migration/validate.md`, `wire/specs/migration/review.md`, `wire/specs/utils/jira_sync.md`

---

**R2 — Make Confluence auto-publish unconditional on generate [High Priority]**

21+ prompts explicitly requesting Confluence publication after Wire generate steps, despite the docstore provider being configured as `confluence` in both releases 03 and 04.

*Solution*: Every generate spec should include an unconditional Confluence publish step at the end when `docstore.provider = confluence`. The publish step should update the page if it exists or create it if not. Remove the current pattern of only publishing on explicit user request.

*Spec files*: All `wire/specs/migration/*-generate.md` files, `wire/specs/utils/docstore.md`

---

**R3 — Add /wire:target-setup-generate to the post-strategy prompt chain [High Priority]**

Lydia spent ~10 prompts on June 11 afternoon working through target setup questions conversationally, never invoking `/wire:target-setup-generate`. The command existed since v3.7.0. The sequencing uncertainty (`'Can I start the taregt setup though the inventory and startgey have not been approved yet?'`) suggests the playbook wasn't surfacing this as the next step.

*Solution*: (1) `/wire:status` output should display `/wire:target-setup-generate` as the recommended next step when migration_inventory and migration_strategy are both `complete`. (2) The migration playbook template should include target-setup as an explicit post-strategy phase.

*Spec file*: `wire/specs/utils/status.md`, `wire/TEMPLATES/migration-playbook-template.md`

---

**R4 — Surface /wire:lineage-generate in the migration playbook [High Priority]**

`/wire:lineage-generate` shipped June 6. The team spent 18 prompts building the lineage HTML manually on June 8–9. The playbook was generated June 1 and had no lineage step.

*Solution*: (1) Add `/wire:lineage-generate <release-id>` as a step in the migration playbook template after migration-inventory. (2) Update the playbook generate spec to flag new Wire commands that shipped since the playbook was last generated.

*Spec files*: `wire/TEMPLATES/migration-playbook-template.md`, `wire/specs/playbook/generate.md`

---

**R5 — Add data-safety constraints to the migration spec [High Priority — new finding]**

The June 11 23:29 prompt — Mark injecting `'DO NOT, UNDER ANY CIRCUMSTANCES, WRITE DATA TO CARWOW'S SNOWFLAKE DB, OR THEIR GCP PROJECT'` mid-session — is a production safety issue. Claude was operating in an environment with both source (Snowflake) and target (GCS/BigQuery) write access, and attempted an action that Mark had to override manually.

*Solution*: The Wire `dbt_migration` spec and the migration playbook should include explicit data-safety constraints as a pre-execution step: define which environments are read-only, which are write-permitted, and inject these as system constraints before any data movement commands run. The `context.md` should carry a `data_safety.source_readonly = true` flag that the migration specs enforce.

*Spec files*: `wire/specs/migration/dbt_migration-generate.md`, `wire/TEMPLATES/migration-playbook-template.md`

---

**R6 — Extend /wire:status with session-start guidance [Medium Priority]**

Mark ran the plugin check sequence three times in a single day. Lydia ran `/mcp` eight consecutive times without resolution on June 9.

*Solution*: Extend `/wire:status` to verify plugin version, check each configured MCP server, display release status, and state the next pending artifact with the exact command. Make this the mandated first Wire command in all playbooks.

*Spec file*: `wire/specs/utils/status.md`

---

**R7 — Create /wire:migration-plan-generate for platform_migration releases [Medium Priority]**

27 prompts of CSV Gantt/FTE plan work on May 29–31 have no Wire equivalent. `/wire:delivery-roadmap-generate` produces a Build/Pair/Coach delivery option deck — not a week-by-week migration execution plan.

*Solution*: Add a `/wire:migration-plan-generate <release-id>` command. It should read the migration_inventory artifact, apply configurable team capacity, produce a Gantt CSV and Mermaid diagram, and a contingency-adjusted estimate.

*Spec file*: `wire/specs/migration/migration_plan/generate.md` (new)

---

**R8 — Simplify audit command namespace [Medium Priority]**

Three naming errors in the telemetry. The `audit` infix is not recalled reliably.

*Solution*: Add aliases for short forms (`/wire:ingest-audit-generate` → `/wire:ingestion-audit-generate`, `/wire:db-audit-generate` → `/wire:db-object-audit-generate`) so wrong-name variants still resolve.

*Spec files*: Plugin manifest / command registry

---

**R9 — Auto-commit generated artifacts [Medium Priority]**

17 prompts of `'commit'` / `'and push to remote'` after every Wire execution.

*Solution*: Each generate spec should end with a `git add` and `git commit` step using a standard commit message. Push should be optional; local commit should be automatic.

*Spec files*: All `wire/specs/migration/*-generate.md` files

---

**R10 — Add plugin state auto-check at Wire command invocation [Low Priority]**

48 prompts of plugin install/reload activity across the full period, including three plugin-check loops in a single day.

*Solution*: Add a pre-execution check to the Wire plugin that verifies its own version before running any command. If outdated or failed to load, output a single clear install command rather than requiring variant-testing.

---

**R11 — Add /wire:findings-playback-generate to post-discovery-analyses flow [Low Priority]**

The findings playback meeting happened (02-06-2026) but the Wire artifact was never generated. CAR-234 remains open.

*Solution*: Add `/wire:findings-playback-generate` to the post-`discovery-analyses-validate` prompt chain alongside delivery-roadmap.

*Spec file*: `wire/specs/discovery/discovery_analyses-validate.md`

---

## Appendix: Data Sources

| Source | Content | Size |
|---|---|---|
| BigQuery telemetry | `ra-development.analytics.coding_agent_prompts_fact` WHERE `project_dir_basename = 'carwow-delivery'` | 424 rows, ~134k characters |
| GitHub delivery repo | https://github.com/rittmananalytics/carwow-delivery — context.md, 3× status.md, .wire/ structure | On record |
| Jira project CAR | `project = CAR ORDER BY created ASC` | 81+ issues (12 Epics, 69+ Tasks) |
| Fathom meetings | Search: "carwow", recorded_by: mark.rittman@rittmananalytics.com | 64 matching meetings |

**BigQuery query used:**
```sql
SELECT FORMAT_TIMESTAMP('%F %T', event_ts) AS event_time,
       consultant_name AS person_name,
       prompt_sequence_in_session AS prompt_seq,
       user_email,
       git_repo_canonical AS git_repo,
       project_dir_basename,
       seconds_since_prev,
       truncated_display AS prompt_text,
       slash_command_raw,
       CASE WHEN slash_command_raw LIKE '/wire:%' THEN 'Yes' ELSE 'No' END AS is_wire_command,
       slash_command_namespace,
       command_name
FROM `ra-development.analytics.coding_agent_prompts_fact`
WHERE project_dir_basename = 'carwow-delivery'
ORDER BY event_ts
```

---

*Original review generated 2026-06-11. Updated 2026-06-12. Data cut-off: 2026-06-11 23:47 for BigQuery telemetry. Total rows processed: 424.*
