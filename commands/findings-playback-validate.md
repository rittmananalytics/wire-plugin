---
description: Validate Findings Playback deck structure and EDITMODE population
argument-hint: <release-folder>
---

# Validate Findings Playback deck structure and EDITMODE population

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.8.4\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"findings-playback-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.8.4\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate the Findings Playback deck — structure, placeholder fill rate, TODO regions, deliverability
---

# Findings Playback Deck — Validate

## Purpose

Checks the generated Findings Playback deck before the sponsor meeting:
- All required placeholders filled
- TODO chart/word-cloud regions populated (or explicitly deferred to in-meeting edit)
- Slide ordering matches the canonical structure
- Assets and fonts present and loadable
- File opens in a browser without console errors

## Inputs

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `wire/decks/findings_playback/Findings Playback.html` (reference template)

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the generated deck. If missing: "Run `/wire:findings-playback-generate $ARGUMENTS` first."

### Step 2: Structure checks

Parse the deck. For every `<section data-label="...">`:
- [ ] Slide ordering: numeric prefix (01, 02, ...) is contiguous (no gaps unless a section was explicitly excluded in generate)
- [ ] Total slide count between 28 and 60 (canonical range is 30–55; tolerance buffer)
- [ ] Cover slide (label starts with "01") present
- [ ] Section divider for Scope & Discovery Process present
- [ ] Three lens introduction slides present (Hierarchy of Needs, PPT framework, Maturity curve)
- [ ] Current State section divider present
- [ ] Vision Statement slide present
- [ ] At least one per-axis section present (Process / People / Technology) — order by largest count first per playbook

### Step 3: Placeholder fill check

For every `<span class="ph">&lt;&lt;variable_name&gt;&gt;</span>` still in the deck:
- [ ] Flag every unfilled placeholder with its slide number and variable name

Categorise:
- **Critical unfilled** — placeholders on Cover, Team intro, Scope & Objectives, Vision Statement, per-axis Summary slides. These MUST be filled before the sponsor sees the deck.
- **Optional unfilled** — placeholders on slides marked as optional (concept explainer, tool replacement, product spotlights). OK to leave if the slide will be excluded; otherwise must fill.

### Step 4: TODO region check

Search for `<!-- TODO Lead Consultant: ... -->` comments:
- [ ] Each TODO region has either: (a) been replaced with the actual data, or (b) been confirmed as "fill live in playback edit-mode" by the consultant. Surface every remaining TODO with slide number.

### Step 5: Asset loadability

- [ ] `assets/logo-black-blue.svg` exists at the deck-relative path
- [ ] `assets/logo-white-blue.svg` exists
- [ ] `assets/hierarchy-of-needs.png` exists
- [ ] `assets/ppt-venn.svg` exists
- [ ] `assets/maturity-curve.png` exists
- [ ] `colors_and_type.css` exists
- [ ] `deck-stage.js` exists
- [ ] `fonts/` directory present with at least Beatrice-Regular.woff2 and GoogleSans-Regular.ttf

### Step 6: Vision Statement check

- [ ] Slide labelled "Vision Statement" (or similar) contains two paragraphs
- [ ] Each paragraph has at least one `<strong>` bolded phrase (the load-bearing language)
- [ ] Vision Statement matches the Vision Statement excerpt recorded in `status.md → sponsor_validation.vision_statement_excerpt` (or that field is still null — flag a WARNING to set it before review)

### Step 7: Optional smoke test

If `--browser` flag is passed, the validator should open the deck in a headless browser and check for:
- No JavaScript console errors during initial render
- Every slide section visible (no `display: none` regression)
- Font load succeeds

This is opt-in and only runs if a browser engine is available. Without `--browser`, skip with a note "Smoke test skipped — pass --browser to enable".

### Step 8: Produce report

**Output**: `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md`

```markdown
# Findings Playback Deck Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**Deck**: playback/findings_playback.html

## Result: PASS / FAIL / PASS WITH WARNINGS

## Structure

| Check | Result | Note |
|---|---|---|
| Slide count in [28, 60] | ✅ | 42 slides |
| Slide ordering contiguous | ✅ | |
| Required canonical sections present | ✅ | |

## Placeholders

| Category | Count remaining |
|---|---|
| Critical unfilled | 3 |
| Optional unfilled | 7 (slides marked for exclusion) |

### Critical unfilled (must fix)
- Slide 04 — `presenter_title`
- Slide 14 — `vision statement paragraph 2`
- Slide 18 — `process headline`

## TODO regions

- Slide 10 — Hierarchy chart counts
- Slide 11 — PPT chart counts
- Slide 16 — Process word cloud
- Slide 22 — People word cloud
- Slide 28 — Technology word cloud

## Asset loadability

| Asset | Status |
|---|---|
| logo-black-blue.svg | ✅ |
| logo-white-blue.svg | ✅ |
| ... | ... |

## Vision Statement

- Two paragraphs: ✅
- Bold phrases: ✅
- Matches `sponsor_validation.vision_statement_excerpt`: ⚠️ field still null — set it before review

## Next Steps

[If PASS]:
Hold the playback meeting and run the review:
/wire:findings-playback-review $ARGUMENTS

[If FAIL]:
Fix unfilled placeholders and TODO regions, then re-validate.
```

### Step 9: Update status

```yaml
artifacts:
  findings_playback:
    validate: complete   # or "failed"
```

### Step 10: Output summary

Show: critical-unfilled count, TODO count, top issue.

## Output Files

- `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md`
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
