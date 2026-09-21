---
description: Report on all project statuses or specific project
argument-hint: [project-folder] or --archived
---

# Report on all project statuses or specific project

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
    'command': 'status',
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
wire_schema: "1.0"
command: lifecycle
artifact: status
domain: status
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Report on all release statuses in the current engagement

---

# Wire Engagement Status Report

## Purpose

Generate a concise status report showing artifact lifecycle progress for every release in the current engagement (or for one specific release). Outputs a table format with minimal verbosity.

Wire is one-engagement-per-repo: a single `.wire/engagement/context.md` holds engagement-wide metadata (client, SOW, etc.), and each unit of delivery lives in its own `.wire/releases/<release_folder>/` (e.g. `01-discovery`, `02-full-platform`). `/wire:status` reports across all releases in that one engagement.

## Usage

```bash
/wire:status                    # Show all releases in this engagement
/wire:status 01-discovery       # Show detailed status for a specific release
/wire:status --archived         # Show archived releases (see /wire:archive)
```

## Workflow

### Step 1: Read Engagement Context and Scan Release Folders

**Process**:
1. Read `.wire/engagement/context.md` if it exists and parse its frontmatter for `client_name`, `engagement_name`, and similar engagement-wide fields. These are shown once in the report header — they are no longer duplicated per-release the way `client` used to be repeated in every old per-project `status.md`. If the file is missing, proceed without it (older or partially-set-up repos).
2. If the `--archived` flag is present, use Glob: `.wire/releases/_archive/*/status.md`
3. Otherwise, use Glob to find every release in the current engagement: `.wire/releases/*/status.md`
4. Extract the release folder name (e.g. `01-discovery`) from each matched path
5. Build the list of all releases to report on

### Step 2: Parse Release Status Files

**For each release**:
1. Read `status.md`
2. Parse YAML frontmatter to extract:
   - `release_id`, `release_name`, `release_type`
   - `current_phase`
   - `jira` section (if configured): `epic_key`, artifact issue keys
   - the artifact lifecycle states (see below — the shape of this varies by release type)

**Reading artifacts generically**

Different release types have genuinely different artifact sets and even different status-tracking shapes (compare `wire/TEMPLATES/status-template.md` to `wire/TEMPLATES/discovery-status-template.md` to `wire/TEMPLATES/droughty-status-template.md`). Rather than hardcoding a fixed artifact list, always read whatever is actually present in the release's own `status.md`:

**Standard shape** (used by `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement`, `discovery`, `sop_discovery`, `custom`, and `platform_migration`): a top-level `artifacts:` YAML map. Each key is an artifact name (e.g. `data_model`, `dbt`, `semantic_layer`, `problem_definition`). Iterate over the map **in the order its keys appear in the file** — every current template's frontmatter key order matches its own phase/dependency order (verified against `wire/TEMPLATES/status-template.md`, whose YAML key order matches its own Artifact Status Summary table order exactly), so no separate ordering rule is needed.

For each artifact entry, look at which of the `generate` / `validate` / `review` keys are actually present on it — the lifecycle progression is simply **whichever of those three keys exist, in that relative order, skipping whichever are absent**:
- All three present → full lifecycle: generate → validate → review (e.g. `data_model`, `dbt`, `requirements`)
- `generate` + `review` only (no `validate` key) → generate+review-only (same idiom as `mockups` and `uat` — see `wire/specs/design/mockups/review.md`, which documents "mockups is a generate+review artifact — there is no validate step")
- `generate` only (no `validate`, no `review`) → generate-only (same idiom as `viz_catalog` and `lineage_view` — see `wire/specs/design/viz_catalog/generate.md`, which documents "This is a generate-only artifact (no validate or review steps)")
- `validate` + `review` only (no `generate`) — a gate-check artifact with nothing to generate (seen in the `agentic_data_stack` release type's `launch_gate` — see Special Cases below)

The artifact's own key name derives its command — but the exact transform is not identical across every release type, so consult the table in "Command derivation" below rather than assuming one universal rule.

**Special cases** (differently-shaped status tracking — do not force these through the standard-shape logic above):

- **`droughty`**: has no top-level `artifacts:` map at all. Instead it has a `droughty:` section keyed by step name (`setup`, `introspect`, `dbml`, `docs`, `qa`, `stage`, `dbt_tests`, `lookml`), each with a single `status: not_started | complete` field rather than a generate/validate/review triad — these are single-action commands, not three-step lifecycles. Read steps in the order they appear in `wire/TEMPLATES/droughty-status-template.md` (setup → introspect → dbml → docs → qa → stage → dbt_tests → lookml, matching its own Phase headings). The `stage` step is BigQuery-only; if its status reads `not_applicable` (Snowflake warehouse), skip it when determining the next action. See "Command derivation" below for how step names map to commands.
- **`agentic_data_stack`**: has no top-level `artifacts:` map either. Each artifact's generate/validate/review state is tracked as a YAML code block embedded in the markdown body under its own `###` heading (see `wire/TEMPLATES/agentic_data_stack/status_agentic_data_stack.md`), in document order: `dataset_audit` → `metric_audit` → `query_audit` → `governance_design` → `semantic_layer_design` → `canonical_models` → `lookml_views` → `semantic_layer` → `knowledge_skill` → `agent_config` → `eval_suite` → `adversarial_config` → `launch_gate` → `enablement`. Parse each fenced `yaml` block the same generic generate/validate/review way described above (`launch_gate` has no `generate` key — it's validate+review only). See "Command derivation" below for how artifact keys map to commands, including a naming exception on `enablement`.
- **`custom`**: artifact keys and their file paths are whatever `/wire:custom-define` decided for this specific engagement — there's no fixed template or predictable command-name transform at all. Its commands are freshly generated per engagement as `.claude/commands/` wrappers, not entries in `wire/scripts/build-packages.sh`. Read the actual generated command names from `.wire/releases/<release_folder>/custom-commands/` rather than deriving them.

**Command derivation**

The artifact key's transform into a command name is **not identical across every release type** — spot-checked directly against `wire/scripts/build-packages.sh`'s COMMANDS array:

| Release type(s) | Transform | Example |
|---|---|---|
| `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement` (i.e. anything built from `wire/TEMPLATES/status-template.md`) | Key used verbatim — underscores are **kept**, not hyphenated | `data_model` → `/wire:data_model-generate`; `semantic_layer` → `/wire:semantic_layer-review`; `viz_catalog` (generate-only) → `/wire:viz_catalog-generate` |
| `discovery`, `sop_discovery` | Multi-word keys are **hyphenated** | `problem_definition` → `/wire:problem-definition-generate`; `engagement_brief` → `/wire:engagement-brief-generate`; `stakeholder_map` → `/wire:stakeholder-map-generate`. Exception: `kickoff_deck` is renamed outright, not hyphenated → `/wire:kickoff-generate` |
| `platform_migration` | Multi-word keys are **hyphenated** | `dbt_audit` → `/wire:dbt-audit-generate`; `ingestion_migration` → `/wire:ingestion-migration-generate`; `cutover` (single word, unaffected) → `/wire:cutover-generate` |
| `agentic_data_stack` | `ads_` prefix, then the key's underscores **hyphenated** | `dataset_audit` → `/wire:ads_dataset-audit-generate`; `semantic_layer_design` → `/wire:ads_semantic-layer-design-generate`. Exception: `enablement` does not follow the mechanical transform — it maps to `/wire:ads_analytics-enablement-generate` (and `-validate`/`-review`), never a bare "ads_" + "enablement" form |
| `droughty` | `droughty-` prefix, step name **hyphenated**, single action (no generate/validate/review suffix) | `dbt_tests` → `/wire:droughty-dbt-tests`; also a composite `/wire:droughty-generate` that runs the whole phase in sequence — prefer suggesting that when several steps remain |
| `custom` | No fixed transform — see the Special Case above | n/a |

If a release type isn't covered above (new release types get added over time), don't guess a transform — confirm the exact command by matching the artifact's `<category>/<artifact_key>/<step>` against the `spec_path` column of a `wire/scripts/build-packages.sh` COMMANDS entry, then take that entry's own first field (before the pipe), replacing `/` with `-`.

**Artifact State Mapping**:
```
generate: not_started → ⬜, pending → ⏳, complete → ✅
validate: not_started → ⬜, pending → ⏳, pass → ✅, fail → ❌
review:   not_started → ⬜, pending → ⏳, approved → ✅, changes_requested → 🔄
ready:    auto-calculated from above
```

**Ready Calculation** (generic — derived from whichever steps the artifact actually has):
```
ready = ✅ if every lifecycle step the artifact actually has is in its "done" state
        (generate=complete, and validate=pass if present, and review=approved if present)
ready = ⬜ otherwise
```

### Step 3: Generate Output

Both overview and detail modes use the same artifact lifecycle table format.

**Artifact lifecycle table** (used in both modes — columns present in a given release depend on what that release's artifacts actually track):

```
| Artifact         | Generate    | Validate   | Review       | Ready |
|------------------|-------------|------------|--------------|-------|
| requirements     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| workshops        | ✅ complete | -          | ✅ approved   | ✅     |
| conceptual_model | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| data_model       | ✅ complete | ✅ pass     | ⬜            | ⬜     |
| mockups          | ✅ complete | -          | ⬜            | ⬜     |
| viz_catalog      | ⬜          | -          | -            | ⬜     |
```

**Notes:**
- A row shows "-" in the Validate column when the artifact has no `validate` key (generate+review-only, e.g. `workshops`, `mockups`, `uat`), and "-" in both Validate and Review when it has neither (generate-only, e.g. `viz_catalog`, `lineage_view`).
- Artifacts with `not_applicable` state (e.g. droughty's `stage` step on Snowflake) are hidden from the table.
- If `jira.epic_key` exists, add a "Jira" column showing the artifact's `task_key` (e.g., `PROJ-124`)
- In overview mode, if Jira is configured, show the Epic key in the release header: `## release_folder (release_type | current_phase | PROJ-123)`

---

**If no specific release is given** (overview mode) — show every release in the current engagement (there is only ever one client per `.wire/` root now, so this is no longer "one row per client project"):

```
# Acme Corporation — Engagement Status

**Engagement:** acme_data_platform

## 01-discovery (discovery | Discovery)

| Artifact           | Generate    | Validate   | Review       | Ready |
|---------------------|-------------|------------|--------------|-------|
| problem_definition | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| pitch              | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| release_brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| sprint_plan        | ⬜          | ⬜          | ⬜            | ⬜     |

**Next:** `/wire:sprint-plan-generate 01-discovery`

---

## 02-full-platform (full_platform | Requirements)

| Artifact     | Generate    | Validate   | Review | Ready |
|--------------|-------------|------------|--------|-------|
| requirements | ✅ complete | ✅ pass     | ⬜      | ⬜     |
| workshops    | ⬜          | -          | ⬜      | ⬜     |

**Next:** `/wire:requirements-review 02-full-platform`

---

Summary: 2 release(s) | 0 ready for Prod
```

**Overview format rules:**
- A single engagement-level header up top (client + engagement name, from `.wire/engagement/context.md`)
- Each release gets an H2 header: `## release_folder (release_type | current_phase)`
- Followed by the standard artifact lifecycle table
- Followed by a single **Next:** line with the suggested command
- Releases separated by horizontal rules, in ascending release-folder order (`01-...` before `02-...`)
- Summary line at the bottom

---

**If a specific release is requested** (detail mode):

Same artifact lifecycle table, plus a Highlights section with additional context:

```
# 02-full-platform — Status

**Client:** Acme Corporation

| Artifact     | Generate    | Validate   | Review       | Ready |
|--------------|-------------|------------|--------------|-------|
| requirements | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| workshops    | ✅ complete | -          | ✅ approved   | ✅     |
| data_model   | ✅ complete | ⬜          | ⬜            | ⬜     |

### Highlights

- **Next:** Run `/wire:data_model-validate 02-full-platform` to validate the data model
- **Jira:** Epic PROJ-101 — 5 of 16 artifact tasks complete
- **dbt:** 12 files generated
```

**Highlights section rules:**
- Always include a "Next:" line with the suggested command
- Include a "Jira:" line if `jira.epic_key` exists, showing the Epic key and rough progress
- Include a "Docstore:" line if `docstore.provider` is set, noting the target space/page
- For any artifact whose entry has a non-empty `generated_files` array, optionally mention the file count (e.g. "**dbt:** 12 files generated")
- For any artifact whose entry contains a URL-like field, surface it under that artifact's name
- Include "Blockers:" only if `blockers` in frontmatter is non-empty
- Include other notable items (e.g., "requirements approved by [stakeholder] on [date]")
- If the report itself reveals drift — an execution-log row or artifact file newer than the recorded state, or a `last_updated` older than recent activity — add a line suggesting `/wire:status-sync <release-folder>` (the reconciler in `specs/utils/status_sync.md`)
- Keep to 2-5 bullet points max

### Step 4: Determine Next Action

**Logic for next action** — fully data-driven from whatever the release's own `status.md` documents. Do not hardcode a fixed artifact list here; different release types genuinely differ (see Step 2's "Reading artifacts generically").

**For standard-shape releases** (has a top-level `artifacts:` map):
1. Walk the artifacts in the order their keys appear in the frontmatter (this is the release's own phase order — see Step 2).
2. For each artifact, walk its own present lifecycle steps in `generate → validate → review` order (skipping any step key the artifact doesn't have):
   - If that step's local state is not yet in its "done" value (`generate` ≠ `complete`, `validate` ≠ `pass`, `review` ≠ `approved`): that artifact key and step is the next action — derive the command using the "Command derivation" table in Step 2, and stop.
   - If every present step on this artifact is done, move to the next artifact.
3. If every artifact's every present step is done, the release is complete — say so, and suggest starting or resuming the next release (`/wire:status` overview will show what's next) or, if this is the last configured release, wrapping up the engagement.

**For `droughty` releases**: walk the `droughty:` steps in template order (setup → introspect → dbml → docs → qa → stage → dbt_tests → lookml, skipping any marked `not_applicable`); the first step whose `status` isn't `complete` is the next action — derive its command from the "Command derivation" table in Step 2.

**For `agentic_data_stack` releases**: walk the embedded YAML blocks in document order (see Step 2's Special Cases); apply the same generate→validate→review-present-steps-only rule per block, deriving the command from the "Command derivation" table in Step 2.

### Step 4.5: Sync Jira Status (Optional)

If `jira` section exists in a release's `status.md` and `jira.epic_key` is not null:

1. Follow the full reconciliation workflow in `specs/utils/jira_status_sync.md`
2. Pass the release folder (e.g. `01-discovery`), so the utility operates on `.wire/releases/<release_folder>/status.md`
3. The utility will sync all local artifact states to Jira Sub-tasks, Tasks, and Epic
4. If any discrepancies are found, add them to the Highlights section
5. If Atlassian MCP is unavailable, skip silently

Run this for every release being reported on (overview mode) or the one release being reported on (detail mode). This ensures Jira stays in sync every time `/wire:status` is run.

## State Icons Reference

| Icon | Meaning |
|------|---------|
| ⬜ | Not started |
| ⏳ | In progress / Pending |
| ✅ | Complete / Pass / Approved |
| ❌ | Failed |
| 🔄 | Changes requested (needs iteration) |

## Error Handling

- **No releases found in this engagement**: Display a message suggesting `/wire:new` to create a release (and, if `.wire/engagement/context.md` is also missing, that no engagement has been set up in this repo yet)
- **Invalid status file**: Skip that release with a warning
- **Missing frontmatter**: Use default "not_started" states

## Design Philosophy

**Minimal verbosity, maximum clarity.**

Key principles:
1. **Table-first**: Primary output is always a table
2. **Icon-driven**: Use emoji for quick visual scanning
3. **Next action**: Always show what to do next
4. **Auto-calculate Ready**: Don't require manual "ready" state management
5. **Data-driven, not hardcoded**: Read each release's own artifact set and lifecycle shape from its `status.md` rather than assuming a fixed vocabulary — release types genuinely differ (see `wire/TEMPLATES/*.md`)

Execute the complete workflow as specified above.
