# Wire Framework — Developer Quick Reference

---

## Installation

```bash
# In Claude Code
/plugin marketplace add rittmananalytics/wire-plugin
/plugin install wire@rittman-analytics
/reload-plugins
/wire:help
```

---

## Starting an Engagement

```
/wire:new                        # Create engagement + first release
/wire:start                      # View all releases and recommended next actions
/wire:status <release>           # Check one release in detail
/wire:plan [release]             # Optional: enter Plan Mode and agree a session plan
```

---

## The Artifact Lifecycle (every artifact follows this pattern)

```
/wire:<artifact>-generate <release>   # AI produces the artifact
/wire:<artifact>-validate <release>   # Automated checks — PASS or FAIL report
/wire:<artifact>-review <release>     # Stakeholder approval gate
```

---

## Release Types and In-Scope Artifacts

| Release Type | Key Artifacts | Use When |
|-------------|--------------|----------|
| `discovery` | problem_definition, pitch, release_brief, sprint_plan | Uncertain scope — run before delivery |
| `full_platform` | All 15 artifacts | SOW to production dashboards, end-to-end |
| `pipeline_only` | requirements, pipeline_design, data_model, pipeline, dbt, data_quality, deployment | New pipeline + dbt, no BI layer |
| `dbt_development` | requirements, conceptual_model, data_model, dbt, data_quality | dbt layer only, data already in warehouse |
| `dashboard_extension` | requirements, mockups, dashboards, uat | New dashboards on existing semantic layer |
| `dashboard_first` | 14 artifacts inc. viz_catalog, seed_data, data_refactor | Early prototyping with seed data before client data access |
| `enablement` | requirements, training, documentation | Training + docs for existing platform |

---

## Full Platform Artifact Order

```
Phase 1 — Requirements:   requirements
Phase 2 — Design:         conceptual_model → pipeline_design → data_model → mockups
Phase 3 — Development:    pipeline → dbt → orchestration → semantic_layer → dashboards
Phase 4 — Testing:        data_quality → uat
Phase 5 — Deployment:     deployment
Phase 6 — Enablement:     training → documentation
```

---

## Discovery Release Flow

```
/wire:problem-definition-generate <release>
/wire:problem-definition-validate <release>
/wire:problem-definition-review <release>

/wire:pitch-generate <release>       # 10-section Shape Up pitch
/wire:pitch-validate <release>
/wire:pitch-review <release>         # Betting table review

/wire:release-brief-generate <release>
/wire:release-brief-validate <release>
/wire:release-brief-review <release>

/wire:sprint-plan-generate <release>
/wire:sprint-plan-validate <release>
/wire:sprint-plan-review <release>

/wire:release:spawn <release>        # Creates downstream delivery release folders
```

---

## Session Lifecycle (v3.4.20+)

No explicit session commands needed. State is managed automatically:

| What happens | How |
|-------------|-----|
| Context loads on first message | engagement-context skill fires automatically |
| Status updates after each command | `status.md` written by each command |
| Activity logged | `execution_log.md` appended after each command and skill activation |
| Optional structured planning | `/wire:plan [release]` — enters Plan Mode, proposes 3–5 step plan |

> `session:start` and `session:end` are deprecated. Running them shows a migration notice.

---

## Engagement Directory Structure

```
.wire/
  engagement/
    context.md          ← client background, stakeholders, working agreements
    sow.md              ← statement of work
    calls/              ← meeting transcripts (add manually)
    org/                ← org charts, RACI
  releases/
    01-<release-name>/
      status.md         ← process state (YAML frontmatter + notes)
      execution_log.md  ← timestamped command and skill activity log
      requirements/     ← generated artifact files
      design/
      development/
      ...
  research/
    sessions/           ← auto-saved technical research summaries
```

---

## Utility Commands

```
/wire:utils-run-dbt <release>             # Run generated dbt models
/wire:utils-meeting-context <release>     # Pull Fathom transcript context
/wire:utils-jira-create <release>         # Set up Jira Epic + Tasks
/wire:utils-linear-create <release>       # Set up Linear Project + Issues
/wire:utils-docstore-setup <release>      # Configure Confluence or Notion store
/wire:mcp [list|view|update|auth]         # Manage MCP server connections
/wire:autopilot [sow]                     # Autonomous end-to-end delivery
/wire:migrate                             # Migrate pre-v3.4 repo structure
/wire:archive <release>                   # Archive a completed release
```

---

## Skills That Auto-Activate

| Trigger | Skill | What it does |
|---------|-------|-------------|
| `.wire/` dir present | engagement-context | Loads release state, surfaces research |
| dbt models/files | dbt-development | Enforces naming, testing, 3-layer conventions |
| LookML files | lookml-content-authoring | Validates views, explores, dashboards |
| Looker MCP available | lookml-content-authoring (MCP) | Live schema validation against Looker |
| Dagster files | dagster | Assets-first patterns, dagster-dbt integration |
| Python files | dignified-python | Modern type syntax, LBYL, pathlib, Click |
| dbt error output | dbt-troubleshooting | Classifies and resolves dbt errors |
| "visualise lineage" | dbt-dag | Generates Mermaid lineage diagrams |
| Semantic layer work | dbt-semantic-layer | Metric layer patterns and validation |
| Unit test files | dbt-unit-testing | dbt unit test structure and coverage |
| dbt analytics Q&A | dbt-analytics-qa | Answers business questions via semantic layer |
| Dashboard mockup request | looker-dashboard-mockup | Pixel-accurate HTML Looker mockups |
| Technical research | research | Saves and surfaces prior research findings |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Commands not found | Run `/reload-plugins`; if still missing, reinstall the plugin |
| Generate produces poor output | Add more source material to `engagement/` and `requirements/` |
| Validate keeps failing | Read the error output carefully — it names the specific check that failed |
| Status.md out of sync | Run `/wire:status <release>` to reconcile |
| Engagement-context skill not firing | Check `.wire/` directory exists in repo root |
| Autopilot blocked | Fix the blocking artifact manually, then re-run `/wire:autopilot` |

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `USER_GUIDE.md` | Full user guide — all release types, worked examples, FAQ |
| `wire/specs/<path>.md` | Workflow spec for each command — edit to change behaviour |
| `wire/skills/<name>/SKILL.md` | Skill definition — edit to change when/how it activates |
| `wire/scripts/build-packages.sh` | Rebuild dist after changing specs or skills |
| `.wire/releases/<id>/status.md` | Current release state — read and writable |
| `.wire/releases/<id>/execution_log.md` | Append-only activity log |
