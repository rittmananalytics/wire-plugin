---
description: Generate stakeholder map with priorities and booking owners
argument-hint: <release-folder>
---

# Generate stakeholder map with priorities and booking owners

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Generate the stakeholder map for a SOP discovery release
---

# Stakeholder Map — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Builds the stakeholder map: the list of people RA needs to interview in this discovery, with priority, influence/interest, sentiment, booking owner, and recommended interviewer. The map drives the interview backlog in Phase 2 of the canonical playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` (approved)

**Helpful**:
- `engagement/context.md` — named team members from `/wire:new`
- `engagement/sow.md` — named stakeholders from the SoW
- HubSpot deal record (if MCP available) — known contacts at the client
- Client org chart (`engagement/org/` if present)

## Workflow

### Step 1: Locate the release

Resolve `.wire/releases/$ARGUMENTS/`. Confirm `release_type: sop_discovery` and that the engagement brief exists. If missing: "Generate the engagement brief first."

### Step 2: Gather candidate stakeholders

Extract from:
1. SoW named stakeholders
2. Engagement brief sponsor field + RA team
3. HubSpot deal record contacts
4. Org chart attachments

Also ask the engagement lead directly:
```
Who else needs to be on the interview list? (Beyond those already named in the SoW and deal record.)
List any roles where you suspect a P0 or P1 voice is missing.
```

### Step 3: Draft the map

**Output**: `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`

```markdown
# Stakeholder Map: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}

## Interview priority guide

- **P0** — Sponsor, primary economic buyer, named end-user lead, technical owner of source systems. Week 1.
- **P1** — Domain SMEs whose requirements drive Release 1 scope. Week 1 or early week 2.
- **P2** — Adjacent stakeholders, downstream consumers, governance/security. Time-permitting or group session.

## Stakeholder list

| Slug | Name | Title | Department | Role in discovery | Influence (H/M/L) | Interest (H/M/L) | Sentiment | Priority | Booking owner | Recommended interviewer | Target week |
|------|------|-------|------------|-------------------|-------------------|------------------|-----------|----------|---------------|--------------------------|-------------|
| `firstname-lastname` | Firstname Lastname | Title | Department | Sponsor / SME / Adjacent / Governance | H | H | Positive / Neutral / Sceptical | P0 / P1 / P2 | Sponsor / RA Lead / SME | Mark / Lewis / consultant | Week 1 / 2 / 3 |

Slug convention: `firstname-lastname` (lowercase, hyphens, ASCII only). Used as the file name for the interview write-up and the `slug` key in `status.md → interviews[]`.

## Coverage check (run after the map is drafted)

- [ ] Every in-scope domain (from `engagement_brief.md → In-scope domains`) has at least one P0 or P1 stakeholder
- [ ] Sponsor is P0
- [ ] At least one technical owner of the source systems is named
- [ ] At least one end-user lead is named per in-scope domain
- [ ] Sentiment is recorded for every P0 and P1 (don't leave blank — guess if you have to, and correct after the interview)

## Gaps and risks

[List any domains where coverage looks thin, or any stakeholder you expect will be hard to book. These become the sponsor confirmation asks at the kick-off.]
```

### Step 4: Update status

```yaml
artifacts:
  stakeholder_map:
    generate: complete
    file: planning/stakeholder_map.md
    generated_date: {{TODAY}}
```

### Step 5: Sync to document store (if configured)

Follow `specs/utils/docstore_sync.md`.

### Step 6: Output summary

Show: count of stakeholders by priority (P0/P1/P2), domains covered vs in-scope-domains-with-no-stakeholder, the top gap to chase with the sponsor.

Next:
```
/wire:stakeholder-map-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
