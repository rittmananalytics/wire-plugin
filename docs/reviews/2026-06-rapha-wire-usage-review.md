# Wire Framework & Claude Code Usage Review — Rapha

**Engagement:** Rapha Data & Analytics
**Review Date:** June 2026
**Review Author:** Generated from BigQuery telemetry, https://github.com/rittmananalytics/rapha-delivery, Jira RAP
**Period Covered:** 2025-12-17 – 2026-06-10
**Consultants:** Tim Griew (primary), Mark Rittman (minor)

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
10. Recommendations

---

## 1. Executive Summary

Over 176 days and 437 Claude Code prompts, the Rapha engagement produced 16 Wire command invocations — a 3.7% adoption rate. That is the lowest rate recorded across reviewed engagements to date, and it masks a more striking pattern: Wire was absent entirely for the first 82 days of active Claude Code work, peaked briefly in a single April setup session, then fell back to zero from May 5 onward. The engagement is still active. The final six weeks contain some of the most intensive Claude Code work in the dataset, with zero Wire involvement.

The headline miss is not a lack of Wire commands existing. Core delivery lifecycle commands — `/wire:requirements-generate`, `/wire:data_model-generate`, `/wire:session-start`, `/wire:session-end` — were available from day one of the engagement and were directly applicable to work Tim Griew was doing manually. Tim ran over 130 prompts building a DBML physical data model from ERD screenshots and meeting transcripts, then another 60+ generating dbt staging, integration, and warehouse models with a recurring correction loop on naming conventions. Each of those sessions has a Wire equivalent. None was used.

The second finding is that once Wire was adopted in April, it was treated as a documentation layer, not a workflow driver. Tim's most frequent Wire-adjacent prompt pattern is "Is there anything to update in the Wire docs?" — ten occurrences of manual Wire documentation updates as a follow-on step after completing development. Wire's generate/validate/review lifecycle was invoked only twice for substantive artifacts: one `/wire:dp-requirements-generate` in March and one `/wire:requirements-validate` in April. All other Wire invocations were session lifecycle (session-start/end) or setup commands (new, migrate).

Three recommendations are immediate. Run `/wire:new` at engagement start and incorporate `/wire:session-start` into every working day — the single setup session in April took 29 prompts to complete because Tim was doing it retroactively with months of work already in flight. Add `/wire:documentation-generate` or an equivalent MR description command to Wire — 21 manual MR description requests across the engagement represent the single highest-volume recurring manual pattern. And for any new dbt-first engagement, Wire's dbt-generate and data_model-generate commands should be the first commands demonstrated to the consultant, not the last ones discovered.

---

## 2. Engagement Overview

### Client & Scope

Rittman Analytics engagement with Rapha Racing — a global premium cycling apparel brand — covering data platform discovery, design, and build on GCP. Started November 2025 as a 4-week discovery sprint to capture institutional knowledge from the departing Head of Data before building a customer-centric analytics platform. The commercial structure was a 3-month Rapha-funded agile phase (£35k/month) to gather velocity data and produce a fixed-price SOW unlocking a ~£220k Google grant.

The strategic goal is a Single Customer View unifying digital behaviour (GA4, Bloomreach) with transactional data (Navision) to support end-to-end customer journey analysis, marketing attribution, and personalised experiences. The platform replaces a legacy stack of SQL Server stored procedures, Azure Data Factory pipelines, Experian Aperture for customer matching, and 64+ Power BI reports constrained by a 10GB model size limit.

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Warehouse | BigQuery (GCP) |
| Transformation | dbt (SQL + Jinja) — staging, integration, warehouse layers |
| Ingestion | dlt (Data Load Tool) — SQL Server via Rackspace BGP tunnel |
| Orchestration | Dagster on GKE (Terraform-deployed) |
| BI | Looker (LookML) |
| Semantic modelling | Modality (MML) |
| Customer resolution | Experian Aperture (being replaced with deterministic in-warehouse approach) |

### Delivery Releases

| # | Release Name | Type | Status | Key Scope |
|---|-------------|------|--------|-----------|
| 00 | Discovery | discovery | completed | Nov–Dec 2025 architecture approval; Calvin Koppenberg knowledge capture |
| 01 | Productionization | delivery | active | Dagster GKE deployment, dlt incremental pipelines, CI/CD |
| 02 | Customer Resolution | delivery | completed_with_followups | SCV/customer_identity bridge table; signed off Tom Webb 2026-05-06 |
| 03 | Customer Acquisition | delivery | active | CPA-by-channel, GA4 attribution, new/reactivated/retained customer KPIs |
| 04 | Core Trading Migration | delivery | blocked | Tabular Sales legacy pipeline → dbt/BigQuery; blocked on Michelle strategy decision |
| 05 | Customer LTV | delivery | design_complete | LTV methodology, KPI definitions, platform design; spawned R06 for build |
| 06 | Customer LTV Build | dbt_development | active | dbt LTV model, Looker explore, UAT |

### Key Stakeholders

| Name | Role | Notes |
|------|------|-------|
| Olivier Dupuis | Lead/Architect (RA) | LTV methodology, CTM strategy, design decisions |
| Tim Griew | Analytics Engineer (RA) | Primary Claude Code user — dbt, GA4, customer resolution |
| Lydia Blackley | PM (RA) | Jira management, sprint changeovers, stakeholder escalations |
| George | Analytics Engineer (RA) | LookML/Looker; departed end Apr 2026 |
| Ron | Analytics Engineer (RA) | Joined Sprint 9 for George handover; departed 2026-05-11 |
| Lukasz Aszyk | Analytics Engineer (RA) | Joined 2026-05-06; GA4, CPA join bug |
| Tom Moran | DevOps/Infra (RA) | Dagster K8s, Terraform; returned Sprint 12 |
| Peter Abidi | Product Sponsor (Rapha) | |
| Michelle | CFO / Executive Sponsor (Rapha) | Final KPI sign-off; blocking CTM strategy decision |
| Tom Webb | Lead, Customer Data & Insight (Rapha) | Day-to-day reviewer; signed off CR and CA wireframe |
| Simon Asquith | Data Lead (Rapha) | SCV/customer data, KPI reconciliation, CTM scoping |
| Gabija | Digital Analytics (Rapha) | GA4 expert, web traffic QA |

---

## 3. Wire Framework Adoption — Quantitative Summary

### Overall Statistics

| Metric | Value |
|--------|-------|
| Total prompts | 437 |
| Wire command invocations | 16 |
| Wire adoption rate | **3.7%** |
| Active days (days with at least one prompt) | 37 |
| Date range | 2025-12-17 – 2026-06-10 |
| Consultants | Tim Griew, Mark Rittman |
| Days before first Wire command | 82 |
| Days after last Wire command | 40 |

**By project_dir:**

| project_dir | Total prompts | Wire invocations | Wire % | Notes |
|-------------|--------------|-----------------|--------|-------|
| rapha-dbt | 430 | 14 | 3.3% | All substantive development work |
| rapha-delivery | 7 | 2 | 28.6% | Mark Rittman testing only — single brief session |

The rapha-delivery figure is misleading: both Wire invocations in that directory are `/wire:start` commands framing a `/plugins` check and `exit` — Mark testing the plugin was installed, not delivery work.

**Pre/post June 8 breakdown** (June 8 = start of team-wide Wire usage acceleration):

| Period | Prompts | Wire invocations | Wire % |
|--------|---------|-----------------|--------|
| Pre June 8 (Dec 2025 – Jun 7) | ~402 | 16 | ~4.0% |
| Post June 8 (Jun 8 – Jun 10) | ~35 | **0** | **0%** |

All 16 Wire commands occurred before June 8. The post-June 8 period covers Tim's most intensive LookML debugging and data audit work — with no Wire at all.

**Wire usage timeline — three phases:**

| Phase | Dates | Prompts | Wire | Wire % | Narrative |
|-------|-------|---------|------|--------|-----------|
| Pre-Wire | Dec 2025 – Mar 8 | ~134 | 0 | 0% | All design and dbt work; no Wire |
| Wire bootstrap | Mar 9 – May 4 | ~228 | 16 | 7.0% | dp-* trial, then /wire:new setup session, session-start/end |
| Wire dormancy | May 5 – Jun 10 | ~75 | 0 | 0% | Sales/trading KPIs, LookML, Dagster; Wire absent |

### Wire Commands Actually Used

| Command | Count | Date range | Consultant | Context |
|---------|-------|-----------|-----------|---------|
| /wire:session-start | 5 | Apr 16 – May 1 | Tim Griew | Used correctly at session start; twice on same day (Apr 16) |
| /wire:new | 2 | Apr 16 | Tim Griew | Second attempt after first was immediately aborted |
| /wire:start | 2 | May 22 | Mark Rittman | Plugin health-check only — not delivery work |
| /wire:dp-start | 1 | Mar 9 | Tim Griew | Delivery package bootstrap for customer resolution |
| /wire:dp-requirements-generate | 1 | Mar 9 | Tim Griew | Requirements for customer resolution sub-project |
| /wire:dp-data_model-generate | 1 | Mar 9 | Tim Griew | Data model for customer resolution |
| /wire:dp-data_model-validate | 1 | Mar 9 | Tim Griew | Validate data model — ran same session as generate |
| /wire:migrate | 1 | Apr 16 | Tim Griew | Migrated pre-Wire delivery package structure to current layout |
| /wire:requirements-validate | 1 | Apr 17 | Tim Griew | Validated CA requirements; correctly preceded by "I have committed the work" |
| /wire:session-end | 1 | Apr 23 | Tim Griew | Opened a session to close out the previous day's work |

### Observations on Command Namespace and Version

The March 9 session used `/wire:dp-*` commands — the older "delivery package" namespace that predated the current Wire lifecycle command structure. By April 16, Tim ran `/wire:migrate` to transition to the current layout. This suggests Tim had encountered Wire through an older version or documentation, then caught up to the current API. The two `/wire:start` invocations by Mark on May 22 appear to have been triggered by the release of `/wire:guide` (v3.5.9, also May 22) — the timing matches the same day that command was added to the plugin. Mark was testing it worked, not running a session.

---

## 4. Wire Plugin Version Availability During the Engagement

Key dates for Wire capabilities relevant to the Rapha engagement:

| Date | Wire version | Capability added | Relevant to Rapha? |
|------|-------------|-----------------|-------------------|
| Dec 2025 – Mar 2026 | ~3.x | Core delivery lifecycle — requirements, data_model, dbt, session management | Yes — all applicable throughout |
| Mar 9, 2026 | — | Tim first uses Wire (dp-* commands) | — |
| Apr 16, 2026 | — | Tim runs /wire:new and /wire:migrate | — |
| May 14, 2026 | 3.5.0 | `sop_discovery` release type with stakeholder-interview, requirements-matrix, findings-playback, delivery-roadmap | No — discovery was Nov 2025, predates this |
| May 22, 2026 | 3.5.9 | `/wire:guide` and session-start hook | Mark tests it immediately |
| May 23, 2026 | 3.5.11 | `/wire:guide` merged into `/wire:start` | — |
| Jun 1, 2026 | 3.7.0 | `platform_migration` release type | Marginal — R04 Core Trading Migration was already blocked |
| Jun 6, 2026 | 3.7.5 | `/wire:lineage-generate` | Potentially applicable to R04/R06 |
| Jun 8, 2026 | 3.7.7 | Reverse ETL audit (Hightouch), Snowflake support | Not applicable |
| Jun 11, 2026 | 3.8.2 | `/wire:upgrade` | Applicable — Rapha has 7 releases that could benefit |

**Key conclusion:** The Rapha engagement predates several Wire capabilities, but not the core ones that mattered most. `/wire:requirements-generate`, `/wire:data_model-generate`, `/wire:session-start`, and `/wire:dbt-generate` were all available from the start of the engagement in November 2025. The 82-day gap to first Wire usage is a pure adoption failure, not a framework availability gap.

The `sop_discovery` release type (v3.5.0, May 14) arrived five months after the discovery phase completed — so the Nov 2025 discovery cannot be categorised as a missed Wire opportunity. That is a framework timing gap, not a consultant adoption gap.

The `platform_migration` release type (v3.7.0, June 1) arrived while R04 Core Trading Migration was blocked on a strategy decision. Tim had not been working on it in Claude Code. The lineage diagram command (v3.7.5, June 6) arrived after Tim had stopped using Wire — no equivalent manual work appears in the June telemetry, unlike Carwow where the overlap was explicit.

---

## 5. Discovery Phase: Actual vs. Canonical Wire

### What Was Produced

The discovery phase (Nov–Dec 2025) predated any Wire usage on this project. The deliverables produced were:

- 67-page prior discovery report (existed before RA engagement)
- Architecture recommendations and GCP stack approval (in-person playback, Dec 9)
- Data model foundation in Modality MML
- Entity resolution strategy
- Stakeholder knowledge capture from Calvin Koppenberg (before departure)
- GA4 requirements specification (Mark Rittman, Dec 17 — first Claude Code session recorded)

### Canonical Wire Discovery Flow vs. What Happened

| Wire artifact | Wire command | What actually happened |
|--------------|-------------|----------------------|
| Problem definition | /wire:problem-definition-generate | Not produced. Architecture discussion and sign-off happened through in-person playback |
| Pitch / release brief | /wire:pitch-generate, /wire:release-brief-generate | Not produced |
| Sprint plan | /wire:sprint-plan-generate | Not produced — sprint planning done manually in Jira/Confluence |
| Engagement brief | /wire:engagement-brief-generate (sop_discovery) | Context.md serves this purpose — rich engagement summary, but not generated by Wire |
| Stakeholder map | /wire:stakeholder-map-generate | Stakeholders captured in context.md; no structured Wire stakeholder map |
| Requirements matrix | /wire:requirements-matrix-generate | Not produced as a structured artifact |
| GA4 requirements | /wire:requirements-generate | Mark Rittman spent Dec 17 doing this manually: "please search for any requirements relating to Google Analytics 4 (GA4) data" + standalone spec document |
| Findings playback | /wire:findings-playback-generate | The in-person Dec 9 playback was not documented via Wire |
| Delivery roadmap | /wire:delivery-roadmap-generate | Not produced in Wire format |

### Root Cause of Discovery Phase Gap

The discovery phase ran five months before Wire was adopted on this engagement. By the time Tim ran `/wire:new` on April 16, the discovery was complete, Customer Resolution was nearly done, and two more releases were in flight. The retroactive `/wire:migrate` captured the structure but could not retroactively produce Wire-formatted discovery artifacts.

The `sop_discovery` release type did not exist until May 14 (v3.5.0), so even if Wire had been used earlier, the structured discovery commands were not available. This is a Category C finding — a framework timing gap. The underlying delivery work (architecture decision, stakeholder knowledge capture, in-person playback) was done thoroughly. It simply was not captured in Wire's artifact structure.

### Specific Discovery Phase Gaps

**GA4 requirements (Dec 17):** Mark's two-prompt session is a verbatim `/wire:requirements-generate` use case — scoping requirements to a specific domain, then drafting a specification document. The outcome was produced but without Wire framing, naming conventions, or Jira/Confluence sync.

**Structured requirements matrix:** No artifact equivalent to Wire's requirements matrix (with MoSCoW priority, phases, stakeholder traceability) was produced for the Rapha engagement. Requirements are scattered across meeting transcripts, Modality MML files, and ad-hoc documents. The Carwow engagement produced a 131-requirement structured matrix via Wire — the absence of this on Rapha has downstream effects on requirements traceability.

---

## 6. Release-by-Release Wire Usage Analysis

### Release 00 — Discovery (Nov–Dec 2025)

**Wire commands used:** 0

The discovery predated Wire. Rich outputs were produced (architecture approval, MML data model, Calvin Koppenberg knowledge capture) but without Wire scaffolding. The status.md for this release was migrated from PKM on 2026-01-27 with `bound_sessions: 0` — it was never linked to a working session.

**Wire status.md quality:** Minimal. The migrated status shows "Migrated from PKM" with empty session history and deliverables marked "check brief.md". The Wire structure exists as a filing cabinet for this release, not as an active workflow record.

### Release 01 — Productionization (Feb 2026–)

**Wire commands used:** 0

One hundred and thirty-four prompts across January and February (before Wire was set up) covered Dagster integration, dlt pipeline debugging, and the entire physical data model build in DBML. None used Wire. This release has the richest session history in the `.wire/` directory (6 bound sessions, detailed session log), but all sessions were documented retroactively via Wire's session-history mechanism — not through `/wire:session-start` or `/wire:session-end`.

**Development approach:** Tim's January sessions are the purest example of convention-enforcement debt: 22 prompts iterating on DBML design, then 60+ generating dbt models from that DBML, then recurring loops to fix naming conventions (17 convention-check prompts, 16 field-naming corrections, 4 column-ordering corrections). Wire's dbt-generate command is designed to prevent exactly this loop by embedding conventions from the start.

**Wire status.md quality:** Well-maintained. The session history is detailed and accurate — evidence that Olivier (not Tim) maintained these during the May 20 `/wire:adopt` sweep rather than in real time.

**Specific gaps:** `/wire:data_model-generate` and `/wire:dbt-generate` both applicable throughout. Estimated combined prompt saving: 80–100 prompts from the correction loop alone.

### Release 02 — Customer Resolution (Feb–May 2026)

**Wire commands used:** 4 (Mar 9 — all dp-* commands)

The March 9 session was the first Wire usage on this engagement. Tim used four `/wire:dp-*` commands in sequence to bootstrap the customer resolution sub-project: dp-start → dp-requirements-generate → dp-data_model-generate → dp-data_model-validate. This is a genuinely correct Wire adoption moment — the sequence matched the intended lifecycle, and the inputs (SOW PDF, customer resolution requirements PDF) were appropriate.

However, three issues surfaced:
1. `/wire:dp-requirements-validate` was typed as a prompt text rather than a command invocation — Tim clearly intended to run it but the syntax failed silently.
2. The SOW scoping instruction ("only pick out the bits relevant to customer resolution") arrived after the generate command rather than before — the context sequence was wrong.
3. After this session, no dp-* commands were used again for 38 days.

The March 10–13 SCV staging work (23 prompts) immediately followed the Wire bootstrap with zero Wire commands. Wire generated the requirements and data model spec; it played no role in the staging model development itself.

**Wire status.md quality:** Excellent. The most complete status.md in the repo — 7 bound sessions, rich deliverable tracking, sign-off provenance, open follow-up tickets. Updated May 20 via `/wire:adopt` sweep.

**Specific gaps:** `/wire:dbt-generate` for the staging models (Tim built these manually across March 10–17); `/wire:requirements-validate` (attempted but failed to execute).

### Release 03 — Customer Acquisition (Mar–May 2026)

**Wire commands used:** 1 (/wire:requirements-validate, Apr 17)

One Wire command across the entire customer acquisition release — and it was used correctly. Tim explicitly signalled the transition: "I have committed the work. Let's do the requirements next." Then `/wire:requirements-validate releases/03-customer-acquisition`. The clean handoff pattern is encouraging.

What followed immediately: Tim generated an MR description manually (two prompts) rather than using Wire's documentation step. This is the post-Wire correction pattern that appears every time a Wire command completes.

The design work for this release (30+ prompts across March 17–30 — workshop outcomes, KPI definitions, Modality MML, EDM, DFD, Confluence review feedback) was entirely unstructured. Wire's requirements-generate, data_model-generate, and review commands were applicable for every design artifact produced.

**Wire status.md quality:** Good. 6 bound sessions, accurate blocker tracking (Jared silence, CPA join bug). Updated via `/wire:adopt` sweep May 20.

**Specific gaps:** `/wire:requirements-generate` (workshop → requirements doc); `/wire:data_model-generate` (Modality/EDM/DFD design); `/wire:review-generate` for Tom Webb's design feedback round.

### Release 04 — Core Trading Migration (Apr 2026–, blocked)

**Wire commands used:** 0

The April 16 scoping call with Simon Asquith produced a rich problem definition and strategy document — via entirely manual prompts. Neither `/wire:requirements-generate` nor the `platform_migration` release type (not yet available — arrived June 1) was used.

The problem definition was revised on April 29 (v1.1) as strategy evolved from "phased vs. nuclear" to "SOW gold-layer vs ERP-first". This revision work was also manual. The release has been blocked since April 28 pending Michelle's strategy decision.

The `platform_migration` release type arrived June 1 — while the release was already blocked. Converting R04 to a `platform_migration` type would give it 42 new commands covering audit, inventory, strategy, and migration phases. Given the release is still blocked, running `/wire:upgrade` and reconsidering the release type is a real option rather than a theoretical one.

**Wire status.md quality:** Excellent, but Olivier-maintained, not Tim. The blocker tracking, strategy narrative, and open action items are unusually precise — evidence of deliberate documentation by the engagement lead rather than organic Wire usage.

**Specific gaps:** `/wire:problem-definition-generate` (the April 17 manual drafting was 1-for-1 this command); potential `platform_migration` release type conversion if the Michelle decision unblocks this.

### Release 05 — Customer LTV (May–Jun 2026)

**Wire commands used:** 0

The LTV release covers the richest and most structured delivery work in the recent dataset — kickoff workshop, methodology document, KPI definitions, platform design, dashboard mockups, Tom Webb async review with feedback log. All produced manually or by Olivier directly in Claude Code. Tim did not contribute prompts to this release's Claude Code sessions.

The release was scaffolded on May 20 via `/wire:adopt` (note in status.md: "scaffolded_from: /wire:adopt (2026-05-20)"). This confirms the Wire structure was applied retroactively after the fact.

**Wire status.md quality:** Excellent — the most detailed in the repo for methodology and design context. Generated by Olivier's direct Claude Code sessions rather than through Wire commands.

### Release 06 — Customer LTV Build (Jun 2026–)

**Wire commands used:** 0

The active LTV build release (`dbt_development` type) is in flight as of June 10. Tim's June 8 session (the "thorough audit of all metrics in order_line_item" prompt — 15 prompts) is relevant to this release's data model review work but was not conducted via Wire. The review_feedback_log.md in the release artifacts captures Tom Webb's June 8 async feedback; this would normally be the input to `/wire:data_model-review`.

---

## 7. Claude Code Prompt Patterns: Before, During and After Wire Commands

### Pre-Wire Preparation Patterns

The dominant pattern across all 16 Wire invocations: Tim runs Wire commands either cold (first prompt of the session) or mid-stream while already in an active development thread. He rarely pauses to frame context before invoking Wire.

**Cold opens (Wire as first prompt):** `/wire:session-start` on April 27 and April 23 (`/wire:session-end`) opened sessions without any preceding context. This matches Wire's intended use — the session-start command loads context from the repo.

**Mid-stream Wire invocations:** The March 9 `/wire:dp-requirements-generate` and the April 16 `/wire:new` both ran while Tim was mid-thought on development decisions. Immediately before `/wire:dp-data_model-generate`, Tim had been typing context into non-Wire prompts ("This is the customer external ids view we need to use...") rather than providing that context as input to the Wire command.

**Context-provision errors:** The most consistent preparation failure is providing scoping constraints after Wire commands rather than before: "I want you to only pick out the bits of the SOW that are relevant to customer resolution" arrived after `/wire:dp-requirements-generate` had already run. This pattern — Wire command fires, then Tim corrects scope — appeared in three of the four March 9 commands.

### During Wire Command Patterns

**April 16 double session-start:** Tim ran `/wire:session-start` at seq=11, pasted DDL context, then ran `/wire:session-start` again at seq=14. The second run immediately followed a reauth failure ("I have reauthenticated so can you try again"). This suggests Wire's session-start was interrupted mid-execution by an auth timeout — a pattern that would benefit from session-start being resumable.

**Wire abort and restart:** The first `/wire:new` invocation on April 16 was immediately followed by "Stop this for now" at seq=3. Tim then ran `/wire:migrate` and started `/wire:new` again. This suggests he realised mid-setup that he needed to migrate first.

**Post-Wire MR description:** After every single substantive Wire invocation, Tim immediately generated an MR description manually. This is the most consistent post-Wire correction pattern: Wire completes → Tim asks for MR description → Tim saves to file. Zero instances of Wire's documentation step being used.

### Post-Wire Patterns

**"Update the Wire docs" as manual follow-up:** Ten explicit prompts asking Claude to update Wire documentation as a separate action after development work. These prompts occur hours or days after the Wire generate/validate cycle — Wire's own validate and review commands are designed to update status.md, but Tim treats this as a manual housekeeping task. Examples:

- "Ensure the Wire documentation is up to date with these recent changes" (March 11)
- "Is there anything to update in the Wire docs? What's the next step there?" (April 20)
- "Can you update the Wire status now and also write me a concise MR description for this staging work" (April 21)

This pattern confirms Wire is functioning as a documentation repository in Tim's mental model, not as a workflow guide.

**Post-session-start redirect:** On May 1, Tim ran `/wire:session-start`, then immediately redirected away from the release Wire had loaded: "I want to work on sales and trading actually not this release." Wire had loaded context for customer acquisition; Tim switched to a new unscoped session for sales and trading. The Wire session framework had no mechanism to track this redirect — Tim continued without invoking `/wire:new` for the new release.

---

## 8. Gap Analysis: Wire Commands Never Used but Applicable

### Category A — Command existed and was applicable; genuine adoption gap

| Command | Evidence of manual equivalent | Estimated prompt saving | Why it wasn't used |
|---------|-------------------------------|------------------------|-------------------|
| /wire:data_model-generate | 100+ prompts Jan 14–23: DBML from ERD screenshots, DDL, meeting transcripts | 40–60 prompts | Wire not yet adopted on project |
| /wire:dbt-generate | 60+ prompts Jan 16–19: staging, int, warehouse models from DBML; recurring correction loop | 30–50 prompts | Wire not yet adopted |
| /wire:session-start (consistent) | 32 active sessions, 5 session-start invocations | 20–25 prompts | Inconsistent habit formation after April setup |
| /wire:session-end | 37 active days, 1 session-end invocation | 15–20 prompts | Unknown |
| /wire:documentation-generate | 21 MR description requests ("write me a concise MR description") | 25–35 prompts | Command may not exist — see Section 9 |
| /wire:requirements-generate | Dec 17 GA4 requirements work (2 prompts); Mar 9 customer resolution bootstrap | 5–8 prompts | Wire not yet adopted (Dec); dp-* used instead (Mar) |
| /wire:data_quality-generate | Apr 29 QA ticket session (15 prompts — duplicate checks, test coverage audit, QA summary) | 10–15 prompts | Wire not part of Tim's QA workflow |
| /wire:training-generate | May 1 sales and trading enablement session ("I want to deliver a training session...") | 8–12 prompts | Tim named the release "enablement" but never triggered the command |

**Total estimated prompt saving from Category A:** 153–235 prompts, or 35–54% of the total non-Wire prompts in the dataset.

### Category B — Command existed but covered a different artifact; product roadmap gap

| Gap | Manual work | Notes |
|-----|-------------|-------|
| Wire docs manual update | 10 explicit prompts to update Wire documentation | Wire's validate/review commands update status.md automatically — but they weren't being run. A standalone `/wire:docs-sync` command that propagates development context to Wire artifacts without requiring the full validate/review cycle would address this pattern |
| DBML ↔ dbt sync | 22 DBML update prompts — Tim manually keeping warehouse.dbml in sync with dbt changes | No Wire command manages the physical data model as a living document alongside dbt models. Wire's data_model-generate produces a one-time artifact; it has no incremental sync command |

### Category C — Command did not exist at the time of the work; framework coverage gap

| Gap | Work done | When command became available |
|-----|-----------|------------------------------|
| Structured discovery | Nov–Dec 2025 discovery sprint | `sop_discovery` release type arrived May 14, 2026 (v3.5.0) — 5 months after the work |
| platform_migration for CTM | R04 CTM problem definition, Apr 17 | `platform_migration` arrived Jun 1, 2026 (v3.7.0) — after R04 was already blocked |

Both Category C gaps are framework timing issues, not consultant adoption failures. The Rapha discovery was thorough and well-structured — it just predated the Wire commands that would have captured it.

---

## 9. Recurring Manual Patterns — Candidates for New Wire Commands

### 9a — MR / PR Description Generation

**Proposed command:** `/wire:mr-description-generate <release>`

**Evidence:** 21 occurrences across the dataset. This is the single highest-volume recurring manual pattern by a wide margin — appearing after almost every branch of work regardless of release or consultant. Verbatim examples:

- "Draft a concise PR description in markdown covering all of the changes we made in this branch" (Jan 19)
- "Can you write me a concise MR description, covering what we have done and any key decisions or assumptions, including what we have tested. It should note the wire docs updates but focus more heavily on the dbt changes" (Apr 17)
- "Can you write me an MR description for the changes we just made?" (Apr 23)
- "Yes, update the execution log and draft me an MR description in a new md file" (Apr 27)
- "Write a concise MR description to a new MD file covering the changes we have changed and tested" (Jun 3)

**Proposed behaviour:** Read the current git diff against main (or the release branch base), cross-reference Wire artifacts generated in the current session, produce a structured MR description: one-line title, scope (files changed by layer), key decisions and assumptions, test coverage. Save to a file and optionally append to the Wire execution log.

**Input needed:** Current git diff, Wire session context (from session-start). No additional user input required.

### 9b — dbt Naming Convention Enforcement Loop

**Proposed command:** `/wire:dbt-conventions-check <model_path>`

**Evidence:** 17 convention-check prompts, 16 field-naming correction prompts, 4 column-ordering corrections — 37 total occurrences across January–February. The pattern is always the same: model generated → convention violation found → explicit correction prompt → verify corrections applied → next violation found.

Verbatim examples:
- "Replace 'nox' with number in field names. On the fact tables, we don't need to keep source system IDs if they are only there in order to calculate the fk to a dim table" (Jan 15)
- "I can still see plenty of field names with 'nox' in them" (Jan 15)
- "Fiest check /Users/timgriew/Documents/rapha-dbt/docs/dbt_coding_conventions.md to see if yo've missed anything else. Also color should be colour as everything should be in UK English" (Jan 15)
- "Double check the column ordering against the coding conventions. I think temporal columns should go last" (Jan 26)
- "Dates should be suffixed _dt and timestamps _ts. Use dbt_coding_conventions as your first reference" (Jan 26)

**Proposed behaviour:** Run against any generated dbt model — staging, integration, or warehouse. Check column names against the project's `dbt_coding_conventions.md`, validate suffix conventions (_pk, _fk, _ts, _dt, _natural_key), validate column ordering (metrics → dates → booleans → timestamps), flag abbreviations. Return a pass/fail report with specific corrections before the model is committed. This would run as a post-step in `/wire:dbt-generate` rather than as a standalone command.

### 9c — DBML Physical Data Model Sync

**Proposed command:** `/wire:dbml-sync <model_path>`

**Evidence:** 22 DBML update prompts across the engagement. Tim treats `warehouse.dbml` as the physical schema source of truth and manually keeps it in sync with dbt changes — in both directions (DBML → dbt and dbt → DBML).

Verbatim examples:
- "I want to update /Users/timgriew/Documents/rapha-dbt/docs/design/warehouse.dbml with warehouse tables for orders, order lines and returns" (Jan 14)
- "Use these new images and information to update the dbml. Note that tabular_sales has been renamed sales" (Jan 15)
- "Ensure the physical model dbml is up to date with these changes" (Jan 19)
- "Can we also update the physical schema mml file for any new columns we have added to a warehouse model" (May 6)

**Proposed behaviour:** Given a changed dbt model (or set of models), read the current warehouse.dbml, identify tables/fields that need adding or updating to reflect the dbt changes, apply the updates while preserving existing DBML annotations and relationships. Optional reverse direction: given a DBML change, scaffold the dbt model structure. This would integrate with `/wire:dbt-generate` as an automatic post-step.

### 9d — Wire Documentation Sync

**Proposed command:** `/wire:status-sync` (or enhancement to session-end)

**Evidence:** 10 explicit prompts asking Claude to update Wire documentation after development work. These prompts recur because Tim's mental model separates "doing the work" from "recording the work in Wire" — two distinct steps.

Verbatim examples:
- "Ensure the Wire documentation is up to date with these recent changes" (Mar 11)
- "Is there anything to update in the Wire docs? What's the next step there?" (Apr 20)
- "Can you update the MR description and also any wire documentation with the latest status and updates" (Apr 30)
- "Update the wire documentation and the MR description" (Apr 27)

**Proposed behaviour:** At session end (or on explicit invocation), read the current git diff, read the current Wire status.md, identify what has changed and update: artifact completion states, session history, blockers. This should already happen via `/wire:session-end` — but Tim ran session-end only once. The issue may be discoverability rather than a missing command.

---

## 10. Recommendations

### R1 — Wire onboarding at engagement start (High priority)

**Problem:** Tim Griew spent 134 prompts over 82 days before running a single Wire command. The entire physical data model build, initial dbt model generation, and all convention enforcement happened outside Wire's framework.

**Root cause:** No `/wire:new` was run at engagement start. By the time Wire was set up (April 16), four months of work were already in flight and Wire was adopted retroactively.

**Solution:** Make Wire project setup (`/wire:new` + `/wire:session-start`) the first documented step when Claude Code is introduced to a new engagement. The consultant adoption playbook should include a checklist: (1) clone delivery repo, (2) run `/wire:new` to create the first release, (3) run `/wire:session-start` before any development work. The May 20 adoption_playbook in the repo demonstrates Rapha learned this lesson mid-engagement — make it a pre-engagement standard.

**Implementation pointer:** `wire/specs/utils/onboarding.md` (create); update `/wire:new` to prompt for the first active session-start before returning.

---

### R2 — Session lifecycle compliance tracking (High priority)

**Problem:** Tim ran 37 active days of Claude Code work with 5 session-start invocations and 1 session-end. Per-session Wire context was absent on 32 of 37 working days. The post-session documentation gap means Wire status.md was always behind the actual work.

**Solution:** The session-start hook (installed by `/wire:new` since v3.5.9) fires on each session to show Wire project status. Verify this hook is installed and firing on the Rapha delivery repo. Consider adding a session-end reminder to the hook output: "You have not run /wire:session-end since [date] — run it before closing this session."

**Implementation pointer:** `wire/TEMPLATES/hooks/wire-session-check.sh` — add stale session-end detection.

---

### R3 — Add /wire:mr-description-generate (High priority)

**Problem:** 21 MR description requests — the highest-volume recurring manual pattern in the dataset. Every branch of dbt work ends with Tim asking for a structured MR description. Wire has no command for this.

**Solution:** Add `/wire:mr-description-generate <release>` as a thin wrapper: reads `git diff` against the release base branch, reads the current Wire session context, generates a structured MR description (title, scope, key decisions, test coverage), saves to file, optionally appends to the Wire execution log. Should run as an optional post-step in `/wire:session-end`.

**Implementation pointer:** `wire/specs/documentation/mr_description/generate.md` (create); integrate into `wire/specs/utils/session_lifecycle.md`.

---

### R4 — DBML sync integration with dbt-generate (Medium priority)

**Problem:** 22 DBML update prompts — Tim manually keeping `warehouse.dbml` in sync with every dbt change. This is mechanical work with a predictable input/output pattern.

**Solution:** Add DBML sync as a post-step in `/wire:dbt-generate`. After generating or updating dbt models, read the current `docs/design/warehouse.dbml` (or equivalent path from the engagement context), update it to reflect the generated schema. Run in the reverse direction when a DBML change triggers dbt scaffolding.

**Implementation pointer:** `wire/skills/dbt-development/SKILL.md` — add DBML sync step; `wire/specs/development/dbt/generate.md` — add DBML post-step.

---

### R5 — Convert R04 to platform_migration release type (Medium priority)

**Problem:** Release 04 (Core Trading Migration) is currently a `delivery` type with a manually-drafted problem definition and no structured audit or migration artifacts. The `platform_migration` release type (v3.7.0, June 1) is directly applicable — the CTM is moving from a SQL Server/Rackspace gold layer to BigQuery + dbt.

**Solution:** Once Michelle's strategy decision unblocks the release, run `/wire:upgrade 04-core-trading-migration` to bring the status.md schema current, then consider converting to a `platform_migration` type with the Tabular Sales pipeline audit, dbt migration planning, and cutover as structured Wire artifacts. The 42 migration commands provide the scaffolding for what is otherwise a manually-planned complex migration.

**Implementation pointer:** `wire/specs/utils/upgrade.md`; `/wire:new` for R04 as `platform_migration`.

---

### R6 — Automate Wire documentation sync in session-end (Low priority)

**Problem:** Ten manual "update the Wire docs" prompts show Tim separating documentation from workflow. Wire's session-end should prompt for a status update automatically.

**Solution:** Strengthen `/wire:session-end` to include a documentation sync step: read git diff since last session-start, update status.md artifact completion states based on files changed, append to session history. This is partially the existing session-end behaviour — the gap is that Tim ran session-end only once.

**Implementation pointer:** `wire/specs/utils/session_lifecycle.md` — reinforce session-end documentation step; make it the default last prompt in the session-end flow.

---

## Appendix: Data Sources

| Source | Content | Size |
|--------|---------|------|
| BigQuery | `ra-development.analytics.coding_agent_prompts_fact` — all prompts for `project_dir_basename IN ('rapha-dbt', 'rapha-delivery')` | 437 rows |
| GitHub | https://github.com/rittmananalytics/rapha-delivery — cloned to /tmp/rapha-delivery-review | 7 releases, 91 Fathom transcripts in .wire/engagement/calls/ |
| Jira | Project RAP — all issues | 100 issues (14 Epics, 78 Tasks, 8 Stories) |
| Fathom | "rapha" search — 10 meetings including steering committee and delivery risk sessions | 10 meetings |

**BigQuery query:**
```sql
SELECT
    FORMAT_TIMESTAMP('%F %T', event_ts)   AS event_time,
    prompt_sequence_in_session            AS prompt_seq,
    slash_command_raw                     AS slash_command,
    consultant_name                       AS consultant,
    git_repo_canonical                    AS git_repo,
    project_dir_basename                  AS project_dir,
    truncated_display                     AS prompt_text,
    CASE WHEN slash_command_raw LIKE '/wire:%' THEN 'Yes' ELSE 'No' END AS is_wire_command
FROM `ra-development.analytics.coding_agent_prompts_fact`
WHERE project_dir_basename IN ('rapha-dbt', 'rapha-delivery')
GROUP BY 1,2,3,4,5,6,7,8
ORDER BY 1
```

---

*Review generated 2026-06-11. Data cut-off: 2026-06-10 for BigQuery telemetry. Jira data current to 2026-06-11.*
