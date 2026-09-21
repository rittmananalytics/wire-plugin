---
description: Show help for Wire Framework commands
argument-hint: [<command>]
model: claude-haiku-4-5
---

# Show help for Wire Framework commands

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'help',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
description: Show help for Wire Framework commands
argument-hint: [<command>]
workload: mechanical
---

# Wire Help Command

## Purpose

Show a reference list of all Wire commands, or detailed man-page style help
for a single command. Modelled on the Unix `man` / `--help` convention.

## Usage

```
/wire:help                  — List all commands grouped by phase
/wire:help <command>        — Detailed man-page style help for one command
```

## Wire Command Catalog

<!-- Auto-generated by build-packages.sh — do not edit manually -->

### ENGAGEMENT & SETUP

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:start` | `[new/resume/explain]` | Session entry point and Wire co-pilot — orients new users, surfaces the right next action, and helps navigating consultants pick up where they left off |
| `/wire:new` | `(no arguments - interactive)` | Create a new Wire engagement or add a release to an existing engagement |
| `/wire:mcp` | `[list/view/check] [server-name or release-folder]` | Wire-aware MCP server overview and pre-flight check — list servers with Wire purpose, view details, check release readiness |
| `/wire:autopilot` | `[path-to-sow]` | Autonomous end-to-end engagement execution from SOW — discovery sprint then all delivery releases |
| `/wire:status` | `[project-folder] or --archived` | Report on all project statuses or specific project |
| `/wire:archive` | `<project-folder>` | Archive a completed project |
| `/wire:remove` | `<project-folder>` | Remove a project with confirmation |
| `/wire:kickoff-generate` | `[release-folder]` | Generate client kick-off presentation deck from SoW and engagement context |
| `/wire:kickoff-validate` | `[release-folder]` | Validate kick-off deck JSON structure and content completeness |
| `/wire:kickoff-review` | `[release-folder]` | Review kick-off deck internally and export to PDF on approval |
| `/wire:migrate` | `(no arguments — auto-detects the .wire/ layout)` | Migrate pre-v3.4.0 flat .wire/ layout to two-tier engagement/releases structure |
| `/wire:upgrade` | `[release-folder] [--dry-run]` | Upgrade a release folder's status.md to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values |
| `/wire:help` | `[<command>]` | Show help for Wire Framework commands |

### SESSIONS

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:session-start` | `(optional: release-folder)` | DEPRECATED — context loading is now automatic via the engagement-context skill; use /wire:session-plan for optional structured planning |
| `/wire:session-end` | `(optional: release-folder)` | DEPRECATED — session state is now written automatically after each Wire command completes |
| `/wire:session-plan` | `(optional: release-folder)` | Optional planning ritual — propose a focused 3–5 step plan before starting work |

### SHAPE UP DISCOVERY

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:problem-definition-generate` | `<release-folder>` | Generate structured problem definition for a Shape Up discovery release |
| `/wire:problem-definition-validate` | `<release-folder>` | Validate problem definition completeness and quality |
| `/wire:problem-definition-review` | `<release-folder>` | Review problem definition with stakeholders |
| `/wire:pitch-generate` | `<release-folder>` | Generate a Shape Up pitch document from the approved problem definition |
| `/wire:pitch-validate` | `<release-folder>` | Validate pitch document structure and Shape Up quality |
| `/wire:pitch-review` | `<release-folder>` | Review pitch with stakeholders and record appetite decision |
| `/wire:release-brief-generate` | `<release-folder>` | Generate formal release brief from the approved pitch |
| `/wire:release-brief-validate` | `<release-folder>` | Validate release brief against the pitch |
| `/wire:release-brief-review` | `<release-folder>` | Review release brief with client and record sign-off |
| `/wire:sprint-plan-generate` | `<release-folder>` | Generate sprint plan with epics, stories, and point estimates |
| `/wire:sprint-plan-validate` | `<release-folder>` | Validate sprint plan point estimates and appetite budget |
| `/wire:sprint-plan-review` | `<release-folder>` | Review sprint plan with delivery team and record approval |

### SOP DISCOVERY

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:engagement-brief-generate` | `<release-folder>` | Generate engagement brief from SoW and deal context |
| `/wire:engagement-brief-validate` | `<release-folder>` | Validate engagement brief completeness |
| `/wire:engagement-brief-review` | `<release-folder>` | Internal RA review of engagement brief |
| `/wire:stakeholder-map-generate` | `<release-folder>` | Generate stakeholder map with priorities and booking owners |
| `/wire:stakeholder-map-validate` | `<release-folder>` | Validate stakeholder map completeness |
| `/wire:stakeholder-map-review` | `<release-folder>` | Confirm stakeholder map with sponsor |
| `/wire:stakeholder-interview-generate` | `<release-folder>` | Generate a stakeholder interview write-up with the mandatory four-tag template |
| `/wire:stakeholder-interview-validate` | `<release-folder>` | Validate four-tag completeness on every theme bullet |
| `/wire:stakeholder-interview-review` | `<release-folder>` | Internal RA peer review of a stakeholder interview write-up |
| `/wire:requirements-matrix-generate` | `<release-folder>` | Generate the Discovery Requirements Matrix from tagged interviews |
| `/wire:requirements-matrix-validate` | `<release-folder>` | Validate requirements matrix completeness and tag consistency |
| `/wire:requirements-matrix-review` | `<release-folder>` | Internal RA review of the requirements matrix |
| `/wire:discovery-analyses-generate` | `<release-folder>` | Generate the three analyses: Hierarchy of Needs, PPT, and Maturity Curve |
| `/wire:discovery-analyses-validate` | `<release-folder>` | Validate the three analyses (chart shape, diagnosis, Maturity pin evidence) |
| `/wire:discovery-analyses-review` | `<release-folder>` | Internal RA review of the three analyses (HoD + peer consultant) |
| `/wire:findings-playback-generate` | `<release-folder>` | Generate the Findings Playback slide deck |
| `/wire:findings-playback-validate` | `<release-folder>` | Validate Findings Playback deck structure and EDITMODE population |
| `/wire:findings-playback-review` | `<release-folder>` | Sponsor playback session — Sponsor Validation Checklist (the canonical gate) |
| `/wire:delivery-roadmap-generate` | `<release-folder>` | Generate the delivery roadmap with Build / Pair / Coach options |
| `/wire:delivery-roadmap-validate` | `<release-folder>` | Validate the delivery roadmap and Release 1 scope |
| `/wire:delivery-roadmap-review` | `<release-folder>` | Sponsor review of the delivery roadmap and Release 1 scope |

### DESIGN

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:requirements-generate` | `<release-folder>` | Generate requirements specification from SOW |
| `/wire:requirements-validate` | `<project-folder>` | Validate requirements completeness |
| `/wire:requirements-review` | `<project-folder>` | Record stakeholder review of requirements |
| `/wire:workshops-generate` | `<project-folder>` | Generate workshop materials for clarification |
| `/wire:workshops-review` | `<project-folder>` | Record workshop outcomes |
| `/wire:mockups-generate` | `<project-folder>` | Generate dashboard mockups |
| `/wire:mockups-review` | `<project-folder>` | Review mockups with stakeholders |

### DEVELOPMENT

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:pipeline_design-generate` | `<project-folder>` | Design data pipeline architecture and data flow diagram |
| `/wire:pipeline_design-validate` | `<project-folder>` | Validate pipeline design |
| `/wire:pipeline_design-review` | `<project-folder>` | Review pipeline design |
| `/wire:pipeline-generate` | `<project-folder>` | Generate data pipeline code |
| `/wire:pipeline-validate` | `<project-folder>` | Validate pipeline code quality |
| `/wire:pipeline-review` | `<project-folder>` | Review pipeline code |
| `/wire:dbt-generate` | `<project-folder>` | Generate dbt models |
| `/wire:dbt-validate` | `<project-folder>` | Run dbt tests and validation |
| `/wire:dbt-review` | `<project-folder>` | Review dbt code |
| `/wire:dbt-staging-generate` | `<project-folder>` | Generate dbt staging-layer models only (alternative to the monolithic dbt-generate) |
| `/wire:dbt-staging-validate` | `<project-folder>` | Validate dbt staging-layer models |
| `/wire:dbt-integration-generate` | `<project-folder>` | Generate dbt integration-layer models only (alternative to the monolithic dbt-generate) |
| `/wire:dbt-integration-validate` | `<project-folder>` | Validate dbt integration-layer models |
| `/wire:dbt-warehouse-generate` | `<project-folder>` | Generate dbt warehouse-layer models only (alternative to the monolithic dbt-generate) |
| `/wire:dbt-warehouse-validate` | `<project-folder>` | Validate dbt warehouse-layer models |
| `/wire:dashboards-generate` | `<project-folder>` | Generate dashboards |
| `/wire:dashboards-validate` | `<project-folder>` | Validate dashboards |
| `/wire:dashboards-review` | `<project-folder>` | Review dashboards |
| `/wire:dbtcharts-generate` | `<release-folder> [--subject-area <folder>[,<folder>]] [--no-warehouse] [--force]` | Generate dbt Charts boards, one per warehouse subject area, from the dbt manifest and catalog (deterministic scaffold, then curation) |
| `/wire:dbtcharts-validate` | `<release-folder> [--no-warehouse]` | Validate dbt Charts boards — dct structure and warehouse dry-run, ref()-only queries, no inline data, metadata, coverage |
| `/wire:dbtcharts-review` | `<release-folder>` | Review dbt Charts boards with stakeholders |
| `/wire:orchestration-generate` | `<project-folder>` | Generate orchestration layer (Dagster or dbt Cloud) |
| `/wire:orchestration-validate` | `<project-folder>` | Validate orchestration layer against pipeline design |
| `/wire:orchestration-review` | `<project-folder>` | Review orchestration setup with stakeholders |
| `/wire:dbt-audit-generate` | `<release-folder>` | Catalog dbt models with complexity classification and feature detection |
| `/wire:dbt-audit-validate` | `<release-folder>` | Validate dbt audit completeness and complexity ratings |
| `/wire:dbt-audit-review` | `<release-folder>` | Internal RA review of dbt audit |
| `/wire:orchestration-audit-generate` | `<release-folder>` | Catalog orchestration jobs, schedules, and dependencies |
| `/wire:orchestration-audit-validate` | `<release-folder>` | Validate orchestration audit completeness |
| `/wire:orchestration-audit-review` | `<release-folder>` | Internal RA review of orchestration audit |
| `/wire:dbt-migration-generate` | `<release-folder> [--batch N] [--model name]` | Translate dbt models batch by batch to target dialect |
| `/wire:dbt-migration-validate` | `<release-folder> [--batch N]` | Validate dbt model translations compile on target profile |
| `/wire:dbt-migration-lint` | `<release-folder> [--batch N] [--model name] [--severity LEVEL] [--format FORMAT]` | Static pre-warehouse equivalence lint — dialect parse-check plus silent-behaviour-change rules on translated models |
| `/wire:dbt-migration-pre-pr-review` | `<release-folder> [--batch N ` | Pre-submission faithfulness review over a translated diff — deploy-time defect class static parse/lint cannot catch, before a PR is opened |
| `/wire:dbt-migration-fix` | `<release-folder> [--batch N ` | Closed fix-and-re-review loop — auto-apply the deterministic pre-PR-review fixes, re-run the gate, escalate only findings that need a human decision |
| `/wire:dbt-migration-review` | `<release-folder> [--batch N ` | Review translated dbt models |
| `/wire:dbt-migration-defer-build` | `<release-folder> --models <list> [--allow-graph] [--override-budget] [--dry-run]` | Cost-guarded sandbox build: refs deferred to prod state, writes gated to the scratch dataset, exact-name selectors, dry-run cost screen |
| `/wire:dbt-migration-batch-raise` | `<release-folder> [--wave id ` | Register-driven PR shipping pipeline: derive gate-passing candidates, smoke-build from the client branch, pre-raise comparison, drop-on-defect, raise with evidence-first body |
| `/wire:dbt-migration-reverse-port` | `<release-folder> [--wave id ` | Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work |
| `/wire:orchestration-migration-generate` | `<release-folder> [--wave id]` | Generate orchestration job migration runbook |
| `/wire:orchestration-migration-validate` | `<release-folder> [--wave id]` | Validate orchestration migration runbook |
| `/wire:orchestration-migration-review` | `<release-folder> [--wave id]` | Safety-gated approval before activating jobs on target |
| `/wire:dbt-carveout-relocate-generate` | `<release-folder> [--wave id \` | Relocate already-translated dbt models into a post-migration tenant carve-out instead of re-translating them |
| `/wire:dbt-carveout-relocate-validate` | `<release-folder> --target-dbt-project-path <path>` | Validate relocated carve-out dbt models — files present, predicates re-derived from disk, target compiles |
| `/wire:dbt-carveout-relocate-review` | `<release-folder> [--wave id \` | Human adjudication gate for relocated carve-out dbt models |

### TESTING

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:uat-generate` | `<project-folder>` | Generate UAT plan |
| `/wire:uat-review` | `<project-folder>` | Record UAT feedback |

### DEPLOYMENT

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:deployment-generate` | `<project-folder>` | Generate deployment artifacts |
| `/wire:deployment-validate` | `<project-folder>` | Pre-deployment validation |
| `/wire:deployment-review` | `<project-folder>` | Review deployment plan |

### ENABLEMENT

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:training-generate` | `<project-folder>` | Generate training materials |
| `/wire:training-validate` | `<project-folder>` | Validate training content |
| `/wire:training-review` | `<project-folder>` | Rehearse training |
| `/wire:documentation-generate` | `<project-folder>` | Generate documentation |
| `/wire:documentation-validate` | `<project-folder>` | Validate documentation |
| `/wire:documentation-review` | `<project-folder>` | Review documentation |

### UTILITIES

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:utils-run-dbt` | `<project-folder>` | Run dbt models |
| `/wire:utils-meeting-context` | `<project-folder> [artifact-name]` | Retrieve Fathom meeting context for artifact reviews |
| `/wire:utils-client-context` | `<client-name>` | Gather external client context from Slack, HubSpot, Harvest, Jira, Confluence and Fathom |
| `/wire:utils-atlassian-search` | `<project-folder> [artifact-name]` | Search Confluence and Jira for project context |
| `/wire:utils-jira-create` | `<project-folder>` | Create Jira Epic and issues for a project |
| `/wire:utils-jira-sync` | `<project-folder> <artifact> <action>` | Sync artifact status to Jira |
| `/wire:utils-jira-status-sync` | `<project-folder>` | Full Jira reconciliation for all artifacts |
| `/wire:utils-linear-create` | `<project-folder>` | Create Linear Project and issues for a project |
| `/wire:utils-linear-sync` | `<project-folder> <artifact> <action>` | Sync artifact status to Linear |
| `/wire:utils-linear-status-sync` | `<project-folder>` | Full Linear reconciliation for all artifacts |
| `/wire:utils-docstore-setup` | `<project-folder>` | Set up document store (Confluence/Notion) for a project |
| `/wire:utils-docstore-sync` | `<project-folder> <artifact>` | Sync a generated artifact to the document store |
| `/wire:utils-docstore-fetch` | `<project-folder> <artifact>` | Fetch document store content and comments for review |
| `/wire:utils-data-model-registry-setup` | `(no arguments - interactive)` | Clone the private wire-data-model-registry repo to this machine, for RA staff with access |
| `/wire:utils-fathom-sync` | `[--after YYYY-MM-DD] [--before YYYY-MM-DD] [--limit N] [--dry-run] [--no-findings]` | Pull new Fathom call transcripts for this engagement's client into .wire/engagement/calls/, then extract findings |
| `/wire:utils-migration-agent-delegate` | `(internal — called by migration generate commands)` | Auto-delegation protocol for migration generate commands — dispatch to migration-specialist subagent when available |
| `/wire:utils-session-summary` | `<release-folder> [scope]` | Draft a Slack-shaped session summary from a release's execution log |
| `/wire:utils-commit` | `<release-folder> <artifact> <action>` | Stage and commit generated or validated Wire artifacts to git |
| `/wire:utils-pr-create` | `[release-folder]` | Create a Wire-aware GitHub pull request pre-populated from session artifacts |
| `/wire:utils-pipeline-status` | `<release-folder>` | Check configured pipeline tool connection status |
| `/wire:utils-git-workflow` | `<release-folder> <artifact-id> <action>` | Ensure a branch-per-artifact exists and, on validate/review, commit and open or update its PR (composes utils-commit and utils-pr-create) |
| `/wire:utils-ci-parity` | `<release-folder> [--repo <path-or-role>] [--branch <name>]` | Client CI parity gate: detect the client repo's CI system, replicate its locally-runnable checks against a branch before raising, report pass/fail per check |
| `/wire:utils-client-watch` | `<release-folder>` | One client-watch tick — channel replies to tracked posts recorded in the answers ledger, merged client PRs advance the register and fire the post-merge action |
| `/wire:utils-ask-list-generate` | `<release-folder> [--max N]` | Draft the top-N client ask list from the register's blocker taxonomy — capped, and guarded against re-asking anything the answers ledger holds |
| `/wire:utils-delivery-forecast` | `<client-name> [--release <folder>]` | Calculate % delivered and ETA per release using checklist, Jira, Harvest and Fathom velocity, compared against contractual dates |
| `/wire:utils-doc-analyze` | `<file-path-or-url> [<file-path-2> ...]` | Extract deliverables, acceptance criteria, and timeline from SoW or project documents |
| `/wire:utils-modality-link` | `<release-folder> [--path <dir>]` | Locate the client's Modality model and record it on the release, so the design commands read the existing model instead of deriving one |

### RELEASE UTILITIES

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:release-spawn` | `<discovery-release-folder>` | Create downstream delivery release folders from an approved discovery release brief |

### PLATFORM MIGRATION

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:migration-audit-all` | `<release-folder>` | Run all platform migration audits in parallel (5 core + optional reverse ETL) |
| `/wire:ingestion-audit-generate` | `<release-folder>` | Catalog all Fivetran connectors with MCP or CSV fallback |
| `/wire:ingestion-audit-validate` | `<release-folder>` | Validate ingestion audit completeness and migration flags |
| `/wire:ingestion-audit-review` | `<release-folder>` | Internal RA review of ingestion audit |
| `/wire:db-object-audit-generate` | `<release-folder>` | Enumerate all databases, schemas, tables, views on source platform |
| `/wire:db-object-audit-validate` | `<release-folder>` | Validate db object audit classification completeness |
| `/wire:db-object-audit-review` | `<release-folder>` | Internal RA review of db object audit |
| `/wire:security-audit-generate` | `<release-folder>` | Catalog roles, permissions, users, service accounts |
| `/wire:security-audit-validate` | `<release-folder>` | Validate security audit completeness |
| `/wire:security-audit-review` | `<release-folder>` | Internal RA review of security audit |
| `/wire:reverse-etl-audit-generate` | `<release-folder>` | Catalog Hightouch reverse ETL syncs, models, and destinations |
| `/wire:reverse-etl-audit-validate` | `<release-folder>` | Validate reverse ETL audit completeness and dependency mapping |
| `/wire:reverse-etl-audit-review` | `<release-folder>` | Internal RA review of reverse ETL audit |
| `/wire:reverse-etl-migration-generate` | `<release-folder> [--wave id]` | Generate Hightouch sync migration runbook — repoint, rewrite, rebuild |
| `/wire:reverse-etl-migration-validate` | `<release-folder> [--wave id] [--twins-only]` | Validate reverse ETL migration runbook completeness, plus the authored twins — primaryKey casing (error) and destination-set safety |
| `/wire:reverse-etl-migration-review` | `<release-folder> [--wave id]` | Internal RA review of reverse ETL migration runbook |
| `/wire:reverse-etl-equivalency-validate` | `<release-folder> [--syncs name1,name2] [--tier N]` | Sync-level equivalence — old sync vs target twin at the sync grain (PK row set + changed-field hashes), tier-2 decoy diff where possible; promotion requires a tier-1 pass |
| `/wire:reverse-etl-twin-generate` | `<release-folder> [--wave id] [--syncs a,b] [--dry-run]` | Author the target-warehouse twin config per in-scope sync — additive, paused, decoy-pointed, model translated, manifest keyed on the normalised sync id |
| `/wire:reverse-etl-retire-generate` | `<release-folder> [--wave id] [--min-clean-days N]` | Generate the reverse-ETL retirement runbook — superseded and retire-classified syncs, ordered, with the evidence each replacement has run cleanly and the rollback |
| `/wire:migration-inventory-generate` | `<release-folder>` | Synthesise all audits into unified catalogue with dependency graph |
| `/wire:migration-inventory-validate` | `<release-folder>` | Validate migration inventory object counts and dependency graph |
| `/wire:migration-inventory-review` | `<release-folder>` | Internal RA and client scope confirmation |
| `/wire:lineage-generate` | `<release-folder>` | Generate interactive dbt lineage HTML, with optional reverse-ETL layer showing Hightouch syncs and destinations |
| `/wire:migration-batching-generate` | `<release-folder> [--seed <path>]` | Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph |
| `/wire:migration-batching-validate` | `<release-folder>` | Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared |
| `/wire:migration-batching-review` | `<release-folder>` | Human/client adjudication gate — turn the proposed batch partition into a committed schedule |
| `/wire:migration-strategy-generate` | `<release-folder>` | Generate platform-pair translation guide, phasing, rollback, equivalency criteria |
| `/wire:migration-strategy-validate` | `<release-folder>` | Validate migration strategy completeness |
| `/wire:migration-strategy-review` | `<release-folder>` | Client sign-off on migration strategy |
| `/wire:target-setup-generate` | `<release-folder>` | Generate target warehouse DDL scripts (SAFETY GATE) |
| `/wire:target-setup-validate` | `<release-folder>` | Validate target setup scripts |
| `/wire:target-setup-review` | `<release-folder>` | Safety-gated approval before writing to target platform |
| `/wire:ingestion-migration-generate` | `<release-folder> [--wave id]` | Generate Fivetran connector migration runbook |
| `/wire:ingestion-migration-validate` | `<release-folder> [--wave id]` | Validate ingestion migration runbook |
| `/wire:ingestion-migration-review` | `<release-folder> [--wave id]` | Safety-gated approval before activating Fivetran to target |
| `/wire:equivalency-validate` | `<release-folder> [--batch N ` | Run equivalency checks across all in-scope tables (parallel fan-out) |
| `/wire:equivalency-investigate` | `<release-folder> --object <table_or_model>` | Deep diagnostics for a specific failing object |
| `/wire:equivalency-fix` | `<release-folder> --object <name> --approach <description>` | Apply agreed fix and re-run equivalency checks for affected objects |
| `/wire:equivalency-post-merge-verify` | `<release-folder> [--models list] [--no-wait]` | Post-merge production verification: wait for the client pipeline to materialise merged models, compare at the full verdict bar, advance the register to production_verified |
| `/wire:equivalency-sweep` | `<release-folder> --pattern <rule-id> [--dry-run]` | Estate-wide defect-class sweep — enumerate one root-caused pattern across delivery tree, client main and open PRs, classify each site, close by encoding the lint rule |
| `/wire:cutover-generate` | `<release-folder>` | Generate cutover runbook (SAFETY GATE — point of no return) |
| `/wire:cutover-validate` | `<release-folder>` | Validate cutover runbook completeness |
| `/wire:cutover-review` | `<release-folder>` | Safety-gated sign-off before live cutover |
| `/wire:migration-report-generate` | `<release-folder>` | Generate post-migration report |
| `/wire:migration-report-validate` | `<release-folder>` | Validate migration report completeness |
| `/wire:migration-report-review` | `<release-folder>` | Final review and archive of migration report |
| `/wire:migration-register-generate` | `<release-folder>` | Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence) |
| `/wire:migration-register-validate` | `<release-folder>` | Validate the migration register — schema, coverage, state consistency |
| `/wire:migration-drift-generate` | `<release-folder>` | Scheduled drift gate — diff live source vs last-migrated commit, flag downstream syncs and masking changes |
| `/wire:migration-drift-validate` | `<release-folder>` | Validate the migration drift report — classification, sync flagging, masking hook |
| `/wire:migration-status` | `<release-folder> [waves/item/blocking/exceptions] [--json]` | Operational status view — per-wave exclusive model/sync stages, drift partition, provenance header, item/blocking/exceptions subcommands, JSON output |
| `/wire:data-residency-assessment-generate` | `<release-folder>` | Generate the GDPR and data-residency assessment, including the historical-window legal review (tenant carve-out) |
| `/wire:data-residency-assessment-validate` | `<release-folder>` | Validate the data residency assessment — all required sections present and non-empty |
| `/wire:data-residency-assessment-review` | `<release-folder>` | Client DPO/legal sign-off gate for the data residency assessment |
| `/wire:region-tagging-generate` | `<release-folder> [--region <code>]` | Classify in-scope items into region buckets for a tenant carve-out (candidates, never auto-removal) |
| `/wire:region-tagging-validate` | `<release-folder>` | Validate region tags — all three buckets populated, every item classified exactly once |
| `/wire:region-tagging-review` | `<release-folder>` | Human adjudication gate for region tags |
| `/wire:bulk-copy-migration-generate` | `<release-folder> [--wave id]` | Generate Snowflake→BigQuery bulk copy runbook (tenant carve-out, two-stage with equivalency gate) |
| `/wire:bulk-copy-migration-validate` | `<release-folder> [--wave id]` | Validate bulk copy runbook — tenant guard, two-stage gate, scoped service account |
| `/wire:bulk-copy-migration-review` | `<release-folder> [--wave id]` | Safety-gated approval before the first tenant bulk-copy execution |
| `/wire:logical-access-uat-generate` | `<release-folder> [--region <code>]` | Generate a region-scoped logical-access UAT plan and evidence pack (tenant carve-out) |
| `/wire:logical-access-uat-validate` | `<release-folder>` | Validate logical-access UAT — at least one negative test per IAM boundary |
| `/wire:logical-access-uat-review` | `<release-folder>` | Execute and sign off logical-access UAT — the isolation-proof gate before cutover |
| `/wire:metabase-audit-generate` | `<release-folder>` | Catalog Metabase collections, dashboards, cards/SQL, and permission groups |
| `/wire:metabase-audit-validate` | `<release-folder>` | Validate Metabase audit completeness and dependency coverage |
| `/wire:metabase-audit-review` | `<release-folder>` | Internal RA review of Metabase audit |
| `/wire:metabase-migration-generate` | `<release-folder>` | Generate Metabase migration runbook — translate card SQL, remap permission groups, two-stage connection repoint |
| `/wire:metabase-migration-validate` | `<release-folder>` | Validate Metabase migration runbook completeness |
| `/wire:metabase-migration-review` | `<release-folder>` | Internal RA review of Metabase migration runbook |
| `/wire:metabase-carveout-generate` | `<release-folder> [--collection id] [--dashboard id]` | Tenant carve-out of the Metabase estate — layer decision per card set (sandboxing/warehouse/dashboard-parameter/card-edit), registry-resolved filters, dashcard pruning, manifest review gate |
| `/wire:metabase-carveout-validate` | `<release-folder>` | Validate the Metabase carve-out — filters re-derived from the registry, no unfiltered card, dashcard-level removals, explicit shared-card decisions |
| `/wire:metabase-carveout-review` | `<release-folder>` | Human gate for the Metabase carve-out — adjudicate layer decisions, sign off manifest rows, resolve manual-review cards |
| `/wire:metabase-carveout-transport-generate` | `<release-folder> [--collection id] [--dashboard id]` | Produce the transport plan as a dry-run artifact: the four id-rewrites plus SQL-text rewrites of hardcoded source-project table references, writing nothing to either instance |
| `/wire:metabase-carveout-transport-validate` | `<release-folder>` | Validate the transport plan: re-derive the SQL scan from each card's own SQL, prove every source-project reference accounted for and every id-rewrite resolves on the target |
| `/wire:metabase-carveout-transport` | `<release-folder> [--target-instance-url url] [--collection id] [--dashboard id] [--dry-run]` | Transport signed-off carve-out cards and dashboards onto the separately-hosted tenant Metabase instance: executes the validated plan (id and SQL-text rewrites), dependency-ordered, idempotent by recorded target id |
| `/wire:metabase-carveout-repoint-generate` | `<release-folder> [--collection id] [--dashboard id] [--mode duplicate/in_place] [--include-layer card_edit]` | Produce the same-instance repoint plan as a dry-run artifact: per warehouse-layer card, the write mode, destinations, database-id and template-tag remaps, and SQL-text rewrites of hardcoded source-project references |
| `/wire:metabase-carveout-repoint-validate` | `<release-folder>` | Validate the same-instance repoint plan: re-derive the SQL scan from each card's own SQL, prove every reference accounted for, every remap resolves on the mapped database, every in-place row staged |
| `/wire:metabase-carveout-repoint` | `<release-folder> [--stage] [--promote] [--collection id] [--dashboard id] [--card id] [--dry-run]` | Execute the validated same-instance repoint plan: duplicate a card into its target collection, or swap the rewritten query into the existing production card in place, staged for review first |
| `/wire:metabase-equivalency-validate` | `<release-folder> [--cards id1,id2] [--dashboard id]` | Card-level equivalence — migrated/carved cards return the same rows, model verdict taxonomy; gates the connection cutover |
| `/wire:omni-audit-generate` | `<release-folder>` | Catalog Omni connections, model (topics/views/dimensions/measures), and folders/workbooks/tiles |
| `/wire:omni-audit-validate` | `<release-folder>` | Validate Omni audit completeness and dependency coverage |
| `/wire:omni-audit-review` | `<release-folder>` | Internal RA review of Omni audit |
| `/wire:omni-migration-generate` | `<release-folder>` | Generate Omni migration runbook — translate model view SQL on a branch, two-stage connection repoint |
| `/wire:omni-migration-validate` | `<release-folder>` | Validate Omni migration runbook completeness |
| `/wire:omni-migration-review` | `<release-folder>` | Internal RA review of Omni migration runbook |
| `/wire:oac-audit-generate` | `<release-folder>` | Catalog OAC's SMML semantic model — physical/logical/presentation layers |
| `/wire:oac-audit-validate` | `<release-folder>` | Validate OAC audit completeness and dependency coverage |
| `/wire:oac-audit-review` | `<release-folder>` | Internal RA review of OAC audit |
| `/wire:oac-migration-generate` | `<release-folder>` | Generate OAC migration runbook — translate physical-layer connection and joins, two-stage connection repoint |
| `/wire:oac-migration-validate` | `<release-folder>` | Validate OAC migration runbook completeness |
| `/wire:oac-migration-review` | `<release-folder>` | Internal RA review of OAC migration runbook |

### BI MIGRATION

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:looker-audit-generate` | `<release-folder>` | Catalog the Looker estate: LookML views, explores, fields and joins classified for translation, plus dashboards, Looks, tiles, schedules and usage |
| `/wire:looker-audit-validate` | `<release-folder>` | Validate Looker audit completeness: every construct classified, every content row with usage, counts match status |
| `/wire:looker-audit-review` | `<release-folder>` | Internal RA review of the Looker audit |
| `/wire:bi-migration-plan-generate` | `<release-folder>` | Usage-ranked inventory, director rulings (parity or redesign, drop list, PDT disposition, permissions, topic design), model and content batches, register bootstrap |
| `/wire:bi-migration-plan-validate` | `<release-folder>` | Validate the plan: every object in one batch or the drop list, batch dependencies, register row count |
| `/wire:bi-migration-plan-review` | `<release-folder>` | Release director review of the BI migration plan and its rulings |
| `/wire:omni-target-setup-generate` | `<release-folder>` | Prepare the Omni target: connection check, model branch, schema refresh, groups and user attributes |
| `/wire:omni-target-setup-validate` | `<release-folder>` | Validate the Omni target: branch exists, model validates with no blocking issue, groups exist |
| `/wire:omni-target-setup-review` | `<release-folder>` | Internal RA review of the Omni target setup |
| `/wire:omni-model-generate` | `<release-folder> [--batch N ` | Translate a batch of LookML views and explores to Omni views and topics on the model branch (deterministic converter plus agent judgement) |
| `/wire:omni-model-lint` | `<release-folder> [--batch N]` | Static lint of emitted Omni YAML for a batch: no ${TABLE}, no Liquid, valid timeframes, aggregate types, filter objects, primary keys, relationship types |
| `/wire:omni-model-validate` | `<release-folder> [--batch N]` | Validate a model batch on the branch: Omni validator clean, every in-scope field present, one smoke query per topic |
| `/wire:omni-model-review` | `<release-folder> [--batch N]` | Release director review of a translated model batch and its needs_human resolutions |
| `/wire:omni-model-reverse-port` | `<release-folder> [--batch N] [--dry-run]` | Carry changes made to the Omni model downstream (in Omni or its git repo) back into the delivery tree; four-way classification per emitted file, never clobbering unwritten local work |
| `/wire:omni-content-generate` | `<release-folder> [--batch N ` | Plan and create Omni dashboards for a batch of Looker dashboards and Looks; skipped tiles listed with reasons |
| `/wire:omni-content-validate` | `<release-folder> [--batch N]` | Validate a content batch: plan fields exist on the branch, controls map, created documents resolve with the planned tile count |
| `/wire:omni-content-review` | `<release-folder> [--batch N]` | Release director review of a migrated dashboard batch |
| `/wire:bi-equivalency-validate` | `<release-folder> [--batch N ` | Tile-level parity: Looker and Omni results compared under a pinned as-of, verdicts in the model taxonomy; gates cutover |

### DROUGHTY

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:droughty-setup` | `<release-folder> [--force]` | Install Droughty, generate profile.yaml and droughty_project.yaml |
| `/wire:droughty-introspect` | `<release-folder>` | Schema inventory report — tables, columns, PK/FK coverage |
| `/wire:droughty-dbml` | `<release-folder>` | DBML entity-relationship diagram from warehouse schema |
| `/wire:droughty-docs` | `<release-folder>` | AI-generated field descriptions for all columns |
| `/wire:droughty-qa` | `<release-folder>` | LangGraph data quality agent report |
| `/wire:droughty-stage` | `<release-folder>` | Staging SQL and sources.yml generation (BigQuery only) |
| `/wire:droughty-dbt-tests` | `<release-folder>` | Pattern-based dbt schema tests from deployed models |
| `/wire:droughty-lookml` | `<release-folder>` | Base LookML views from deployed dbt models |
| `/wire:droughty-generate` | `<release-folder> [--mode discovery` | Run full Droughty phase in sequence (discovery, post-dbt, or full) |

### OTHER

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/wire:delegate` | `<release-folder>` | Decompose a release's pending work into typed tasks and dispatch to specialist local subagents |
| `/wire:status-sync` | `[release-folder]` | Reconcile recorded release state against evidence (git, execution log, disk, sprint plan) and repair the record with confirmation |
| `/wire:work` | `<release-folder> [ticket-or-description]` | Work a ticket inside an existing release — plan with a command or skill named per step, run only the approved plan, publish via the client's PR, patch stale documents and reconcile the record |
| `/wire:playbook-generate` | `<release-folder>` | Generate a step-by-step BPMN delivery playbook for any Wire release |
| `/wire:business-rules-generate` | `<release-folder> [--domain <name>] [--import <path>]` | Discover, define and agree the business rules for one domain, from legacy systems and from the people who own the definitions, before design starts |
| `/wire:business-rules-validate` | `<release-folder>` | Validate the business rules register: statuses consistent with their required fields, assumptions unexpired, every variant sourced, rules and implementations citing each other |
| `/wire:business-rules-review` | `<release-folder>` | Review the business rules register with the people who own the numbers — each disputed rule settled or owned, each assumption accepted with its expiry |
| `/wire:current-state-appraisal-generate` | `<release-folder> [--section "<title>"]` | Appraise the client's current state — platform, sources, replication, tooling, documentation, governance, data quality — from documentation and interviews rather than system access |
| `/wire:current-state-appraisal-validate` | `<release-folder>` | Validate the current state appraisal: every claim sourced and confidence-rated, sources reconcilable, gaps named rather than empty |
| `/wire:current-state-appraisal-review` | `<release-folder>` | Review the current state appraisal with the client's technical lead — facts corrected, gaps owned, contradictions resolved or accepted |
| `/wire:conceptual_model-generate` | `<project-folder>` | Generate conceptual entity model from requirements |
| `/wire:conceptual_model-validate` | `<project-folder>` | Validate conceptual model completeness and correctness |
| `/wire:conceptual_model-review` | `<project-folder>` | Review conceptual model with business stakeholders |
| `/wire:logical_model-generate` | `<release-folder> [--domain <name>]` | Logical data model between the conceptual model and the physical dbt design — per-entity sources and grain, keys, cardinality, identity resolution, normalisation and attribution rules |
| `/wire:logical_model-validate` | `<release-folder>` | Validate the logical model: every conceptual entity accounted for, keys and cardinality decided or explicitly open, sources reconciled, attribution rules complete |
| `/wire:logical_model-review` | `<release-folder>` | Review the logical model — precedence and attribution decisions confirmed by the people who own them, open questions closed or owned |
| `/wire:data_model-generate` | `<project-folder>` | Design dbt model structure |
| `/wire:data_model-validate` | `<project-folder>` | Validate data model conventions |
| `/wire:data_model-review` | `<project-folder>` | Review data model with team |
| `/wire:viz_catalog-generate` | `<project-folder>` | Generate visualization catalog from mockup output |
| `/wire:semantic_layer-generate` | `<project-folder>` | Generate semantic layer (LookML, etc.) |
| `/wire:semantic_layer-validate` | `<project-folder>` | Validate semantic layer |
| `/wire:semantic_layer-review` | `<project-folder>` | Review semantic layer |
| `/wire:agents_schema-generate` | `<release-folder> [--providers <list>] [--skills-source <path>]... [--lookml-repo <owner/repo[@ref]>] [--provider <name>] [--no-guide] [--set-secrets] [--publish] [--no-warehouse] [--force]` | Publish the release's metadata into the warehouse AGENTS schema for AI agents: plan the providers (dbt manifest, LookML, Omni, OSI, Sigma, skills), write the pinned GitHub workflow, agents.yml and the skills, complete the warehouse guide, offer to set the repository secrets from the dbt profile, publish from CI or with --publish; --lookml-repo publishes LookML from its own repository |
| `/wire:agents_schema-validate` | `<release-folder> [--no-warehouse]` | Validate the Agents Schema publication — pinned workflow, sources unchanged, skills well formed, no credentials, AGENTS.ROOT providers, row counts, skill rows, no stale models |
| `/wire:agents_schema-review` | `<release-folder>` | Review the Agents Schema publication with stakeholders |
| `/wire:seed_data-generate` | `<project-folder>` | Generate seed data files from data model |
| `/wire:seed_data-validate` | `<project-folder>` | Validate seed data files |
| `/wire:seed_data-review` | `<project-folder>` | Record stakeholder review of seed data |
| `/wire:data_refactor-generate` | `<project-folder>` | Generate refactoring plan from seed-based to real client data |
| `/wire:data_refactor-validate` | `<project-folder>` | Validate refactored dbt project against real data |
| `/wire:data_refactor-review` | `<project-folder>` | Record stakeholder review of data refactor |
| `/wire:data_quality-generate` | `<project-folder>` | Generate data quality tests |
| `/wire:data_quality-validate` | `<project-folder>` | Run data quality tests |
| `/wire:data_quality-review` | `<project-folder>` | Review test results |
| `/wire:adopt` | `[repo-path-or-url]` | Adopt an in-flight project into Wire — assess repo and external sources, map existing work to artifacts, set up engagement structure, generate adoption playbook |
| `/wire:custom-define` | `<release-folder>` | Define a custom release type from SoW or project documents — map deliverables to Wire commands or generate bespoke specs |
| `/wire:custom-feature-request` | `<custom-spec-name>` | Raise a GitHub issue on the Wire repo proposing a bespoke command as a framework addition |
| `/wire:migration-acceptance-pack-review` | `<release-folder> [--batch N ` | Present migration batch acceptance pack for stakeholder sign-off |
| `/wire:migration-source-register` | `<release-folder> <source_type> <github_url>` | Register a source repository for a given migration source type |
| `/wire:migration-source-refresh` | `<release-folder> <source_type>` | Pull a fresh local snapshot of a registered migration source |
| `/wire:ads-audit-all` | `<release-folder>` | Run all three agentic data stack audits in parallel |
| `/wire:ads_dataset-audit-generate` | `<release-folder>` | Inventory warehouse tables, identify duplicates, grade governance maturity |
| `/wire:ads_dataset-audit-validate` | `<release-folder>` | Verify dataset audit completeness and tier classifications |
| `/wire:ads_dataset-audit-review` | `<release-folder>` | Stakeholder sign-off on canonical table selections and deprecation list |
| `/wire:ads_metric-audit-generate` | `<release-folder>` | Inventory metric definitions, identify conflicts and coverage gaps |
| `/wire:ads_metric-audit-validate` | `<release-folder>` | Check metric audit completeness and conflict detection quality |
| `/wire:ads_metric-audit-review` | `<release-folder>` | Stakeholder sign-off on metric definitions and gap priorities |
| `/wire:ads_query-audit-generate` | `<release-folder>` | Analyse query history to extract patterns and classify by semantic-layer answerability |
| `/wire:ads_query-audit-validate` | `<release-folder>` | Verify query pattern extraction and classification quality |
| `/wire:ads_query-audit-review` | `<release-folder>` | Stakeholder sign-off on query patterns and semantic layer addition priorities |
| `/wire:ads_governance-design-generate` | `<release-folder>` | Produce canonical dataset model, deprecation plan, and tiering policy |
| `/wire:ads_governance-design-validate` | `<release-folder>` | Verify governance design completeness and internal consistency |
| `/wire:ads_governance-design-review` | `<release-folder>` | Stakeholder sign-off on canonical model and deprecation schedule |
| `/wire:ads_semantic-layer-design-generate` | `<release-folder>` | Design metric definitions and dimension model for semantic layer build |
| `/wire:ads_semantic-layer-design-validate` | `<release-folder>` | Check semantic layer design completeness and metric definition quality |
| `/wire:ads_semantic-layer-design-review` | `<release-folder>` | Stakeholder sign-off on metric definitions before implementation |
| `/wire:ads_canonical-models-generate` | `<release-folder>` | Refactor dbt project to implement canonical models and deprecation notices |
| `/wire:ads_canonical-models-validate` | `<release-folder>` | Verify canonical models compile, tests pass, deprecation notices in place |
| `/wire:ads_canonical-models-review` | `<release-folder>` | Data team review of canonical model implementation |
| `/wire:ads_lookml-views-generate` | `<release-folder>` | Create or update LookML view files for new and restructured canonical models (Looker only) |
| `/wire:ads_lookml-views-validate` | `<release-folder>` | Verify LookML view files are valid, canonical models covered, no orphaned column references |
| `/wire:ads_lookml-views-review` | `<release-folder>` | Looker admin sign-off on view files before semantic layer metric build |
| `/wire:ads_semantic-layer-generate` | `<release-folder>` | Implement semantic layer metrics from approved design |
| `/wire:ads_semantic-layer-validate` | `<release-folder>` | Verify metrics queryable and coverage target met |
| `/wire:ads_semantic-layer-review` | `<release-folder>` | Data team review of semantic layer implementation |
| `/wire:ads_knowledge-skill-generate` | `<release-folder>` | Generate per-domain reference files collocated with dbt models |
| `/wire:ads_knowledge-skill-validate` | `<release-folder>` | Check knowledge skill files complete, accurate, and colocated |
| `/wire:ads_knowledge-skill-review` | `<release-folder>` | Domain owner review of knowledge skill files |
| `/wire:ads_agent-config-generate` | `<release-folder>` | Generate agentic data stack Wire skill with routing logic and provenance footer |
| `/wire:ads_agent-config-validate` | `<release-folder>` | Verify agent config skill completeness and routing logic |
| `/wire:ads_agent-config-review` | `<release-folder>` | Technical review of agentic data stack skill before eval suite build |
| `/wire:ads_eval-suite-generate` | `<release-folder>` | Build Q&A eval suite with per-domain accuracy baselines and CI harness |
| `/wire:ads_eval-suite-validate` | `<release-folder>` | Run eval suite and check per-domain accuracy against targets |
| `/wire:ads_eval-suite-review` | `<release-folder>` | Stakeholder review of eval coverage and accuracy results |
| `/wire:ads_adversarial-config-generate` | `<release-folder>` | Configure and test adversarial review sub-agent |
| `/wire:ads_adversarial-config-validate` | `<release-folder>` | Verify adversarial review configuration and calibration |
| `/wire:ads_adversarial-config-review` | `<release-folder>` | Technical review of adversarial review configuration |
| `/wire:ads_launch-gate-validate` | `<release-folder>` | Per-domain accuracy gate before agent announcement |
| `/wire:ads_launch-gate-review` | `<release-folder>` | Platform owner sign-off and launch communications |
| `/wire:ads_analytics-enablement-generate` | `<release-folder>` | Generate user training and maintenance documentation |
| `/wire:ads_analytics-enablement-validate` | `<release-folder>` | Verify enablement documents complete and accurate |
| `/wire:ads_analytics-enablement-review` | `<release-folder>` | Sign-off on user guide and maintenance docs before handover |

## Workflow

### Step 1: Determine mode

If no argument was provided → go to **Step 2 (list)**.

If an argument was provided:
1. Strip any leading `/wire:` prefix if present
2. Normalise: replace spaces and underscores with hyphens, lowercase
   (e.g. "requirements generate" → "requirements-generate")
3. Search the Wire Command Catalog above for an exact match
4. If found → go to **Step 3 (detail)**
5. If not found exactly → find all commands whose name starts with the argument
   - If exactly one match: display it with note `Showing closest match: /wire:<name>`
   - If multiple matches: list them and ask the user to be more specific
   - If no match at all: say so and suggest running `/wire:help` for the full list

---

### Step 2: List all commands

Print this header, then reproduce the Wire Command Catalog tables above verbatim:

```
Wire Framework — Command Reference
════════════════════════════════════════════════════════════════════════════
```

After the tables, print:

```
────────────────────────────────────────────────────────────────────────────
Run /wire:help <command> for full usage details on any command.
```

---

### Step 3: Detailed help for a single command

Look up the matched command in the Wire Command Catalog above to get its
description and argument hint. Then try to load its spec for deeper detail.

**Locating the spec (try in order):**
1. In a development repo: read `wire/specs/<spec-path>.md`
   (map command name → spec path: hyphens in the command name correspond to
   slashes or underscores in the spec path, e.g. `requirements-generate` →
   `wire/specs/requirements/generate.md`)
2. In an installed plugin: read `commands/<command-name>.md` from the plugin
   installation directory, or extract the `## Workflow Specification` section
   from the embedded command file

**Extract from the spec:**
- **DESCRIPTION**: the Purpose section (first 2–4 sentences, drop long examples)
- **PREREQUISITES**: the Prerequisites section verbatim, if present
- **STEPS**: summarise the Workflow section as a flat numbered list
  (one line per step, omit sub-bullets)
- **SEE ALSO**: infer from the command name:
  - `*-generate` links to `*-validate` and `*-review` variants if they exist
  - `*-validate` links to `*-generate` and `*-review`
  - `*-review` links to `*-generate` and `*-validate`
  - Utility commands link to the primary commands that call them
    (e.g. `utils-jira-sync` → `utils-jira-create`, `utils-jira-status-sync`)

**Display format:**

```
WIRE:<COMMAND-NAME-UPPERCASED>(1)              Wire Framework

NAME
    /wire:<command> — <one-line description from catalog>

SYNOPSIS
    /wire:<command> <argument-hint>

DESCRIPTION
    <2–4 sentence summary from the spec's Purpose section>

PREREQUISITES
    • <prerequisite>   (omit section if spec has none)

STEPS
    1. <step 1 summary>
    2. <step 2 summary>
    ...

SEE ALSO
    /wire:<related>, /wire:<related>
```

If the spec file cannot be located, display NAME, SYNOPSIS, DESCRIPTION from
the catalog entry and append: `(full spec not available in this context)`

---

### Step 4: Suggest next action

- After **list**: "Run `/wire:help <command>` for full details on any command."
- After **detail**: "Run `/wire:<command> <args>` to execute, or `/wire:help` for the full list."

## Edge Cases

- **`/wire:help help`**: display help for the help command itself (this file) — show NAME,
  SYNOPSIS, DESCRIPTION, and the two modes; no Steps or SEE ALSO needed
- **Command not in catalog** but spec file found: show whatever can be read from the spec,
  noting it is not in Wire's built-in catalog
- **Spec not accessible**: show the catalog entry only (NAME, SYNOPSIS, DESCRIPTION)
- **Alias forms**: `/wire:help wire:new`, `/wire:help new`, and `/wire:help /wire:new` all
  resolve to the same command (`new`)

Execute the complete workflow as specified above.
