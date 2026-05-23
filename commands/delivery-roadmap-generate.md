---
description: Generate the delivery roadmap with Build / Pair / Coach options
argument-hint: <release-folder>
---

# Generate the delivery roadmap with Build / Pair / Coach options

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.5.13\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"delivery-roadmap-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.5.13\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate the delivery roadmap with Build / Pair / Coach options
---

# Delivery Roadmap — Generate

## Purpose

Translates the validated playback into a delivery plan. Produces the Delivery Roadmap document — the Phase 5 exit artefact — and prepares Release 1 for spawning. The roadmap is sponsor-facing.

If the playback included the Roadmap section inline (BARK pattern), this command produces a confirmatory document mirroring the deck's roadmap slides. If the playback deferred the roadmap to a separate session (Hunkemöller pattern), this command produces the full standalone artefact.

Models Phase 5 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md` (playback held, checklist captured)
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (with MoSCoW + Phase columns set)
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `engagement/sow.md` (for commercial envelope context)

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery`.
2. Confirm `sponsor_validation.playback_held == true`. If not, stop: "Hold and review the playback first."
3. Note `sponsor_validation.preferred_delivery_option` — drives which delivery option is the headline. If null (sponsor didn't name one), the roadmap presents all three side-by-side as equal.

### Step 2: Read commercial context

Read the SoW to extract:
- Commercial envelope (contract value, sprint count if specified, target go-live)
- Named RA team and % allocations
- Client-side dependencies (named integrations, security review windows, etc.)

### Step 3: Compute the Phase 1 scope

From `requirements_matrix.md`:
- All rows with `Phase: 1` form the Release 1 backlog
- Group by `Domain` and `Hierarchy tier` for the breakdown
- Total row count = Release 1 size

If Phase 1 row count is materially larger than the SoW commercial envelope can support (rule of thumb: more than 4 rows per sprint week), surface the gap explicitly — the roadmap is the moment to force the sponsor to defer some Phase 1 items to Phase 2.

### Step 4: Draft the roadmap

**Output**: `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`

```markdown
# Delivery Roadmap: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Sponsor**: <name>
**Preferred Delivery Option**: <Build | Pair | Coach | not yet named>

## Objectives (3–5 bullets, business-outcome framed)

[What this discovery has agreed to achieve, lifted from the Vision Statement + Solution Initiatives. Use business outcome framing, not deliverable framing.]

## Scope overview

[Visual diagram of the end-to-end flow showing Release 1 in-scope (✅) vs out-of-scope (❌). Use a mermaid diagram or a simple bullet list.]

## Breakdown of Release 1 requirements

| Domain | Hierarchy tier | Row count | Top requirement | Source systems |
|---|---|---|---|---|
| Retail | Clean | 8 | Store-level conversion trust | SAP, CowHills EPOS, Footfall |
| Retail | Define & Track | 4 | UPT/ATV/Conversion definitions | — |
| ... | ... | ... | ... | ... |

**Total Phase 1 rows**: <N>

## Recommendations table

| Task | Description | Proposed Owner | Priority |
|---|---|---|---|
| Populate BigQuery with SAP source | Migrate raw SAP data via Fivetran connector | Data Engineering (Olivier) | High |
| Finalise KPI selection | Confirm Phase 1 KPI list with named sponsor | Sponsor + RA Lead | High |
| Wireframe analytical products | Lo-fi wireframes of Release 1 dashboards | RA Lead | Medium |

## Delivery Options

Three options were presented at the playback (or are presented now if the roadmap is a follow-up session). Each option delivers the same Release 1 backlog; what differs is who does the work and what the client retains at the end.

### Build (RA delivers)

| Dimension | Detail |
|---|---|
| What RA delivers | Full implementation: pipelines, dbt models, semantic layer, dashboards |
| What the client provides | Source-system access, sponsor time, end-user validation |
| Sprint count | <N> sprints of <length> |
| Time to value | Fastest — go-live in <weeks> |
| Cost (relative) | Highest |
| Knowledge transfer | Documentation + recorded sessions; client team observes |
| Risk profile | Low delivery risk; medium adoption risk if client team isn't engaged |

### Pair (RA + client co-delivery)

| Dimension | Detail |
|---|---|
| What RA delivers | 50–70% of the implementation; reviews 100% |
| What the client provides | A named data engineer / analyst pairing 3–4 days/week |
| Sprint count | <N> sprints — typically 1.5× Build option |
| Time to value | Medium |
| Cost (relative) | Medium |
| Knowledge transfer | Hands-on — paired implementation builds client capability |
| Risk profile | Medium delivery risk (depends on client capacity); low adoption risk |

### Coach (Client delivers; RA coaches)

| Dimension | Detail |
|---|---|
| What RA delivers | Architecture + reference implementations + weekly coaching sessions |
| What the client provides | A full delivery team |
| Sprint count | <N> sprints — typically 2× Build option |
| Time to value | Slowest |
| Cost (relative) | Lowest direct RA cost; highest client cost |
| Knowledge transfer | Strongest — client team owns the delivery from day one |
| Risk profile | High delivery risk (client team capability); lowest adoption risk |

### Comparison

| | Build | Pair | Coach |
|---|---|---|---|
| Time | <weeks> | <weeks> | <weeks> |
| Cost (RA) | <£> | <£> | <£> |
| Client capacity needed | Low | Medium | High |
| Knowledge retained | Low | Medium | High |
| Delivery risk | Low | Medium | Higher |

## Release 1 plan summary

- **Sprints**: <N> × <length>
- **Expected go-live**: <date>
- **RA team**: <named consultants and % allocation>
- **Key client-side dependencies**:
  - Source-system access (named systems and contacts)
  - Sponsor weekly availability
  - End-user validation window

## Discovery exit checklist

- [ ] All Stakeholder Interview pages published with all four tags
- [ ] Requirements Matrix complete and reviewed (Hierarchy, PPT, Maturity all locked)
- [ ] Discovery Findings Working Document published (per domain)
- [ ] Findings Playback Deck delivered and sponsor-validated (all 7 checklist items)
- [ ] Sponsor Validation Checklist on the Playback Meeting Notes page
- [ ] Delivery Roadmap published (this document)
- [ ] Release 1 Jira/Linear epic created with stories pre-populated
- [ ] Release 1 kick-off scheduled
- [ ] Engagement Brief updated with discovery outcomes
- [ ] Internal RA retro held

## Next steps

[Named owners + dates for everything that needs to happen between this document and the start of Release 1.]
```

### Step 5: Update status

```yaml
artifacts:
  delivery_roadmap:
    generate: complete
    file: planning/delivery_roadmap.md
    generated_date: {{TODAY}}
```

### Step 6: Sync to document store

Follow `specs/utils/docstore_sync.md`.

### Step 7: Output summary

Show: Release 1 row count, preferred delivery option, top three Phase 1 risks.

```
/wire:delivery-roadmap-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
