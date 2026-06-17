---
description: Internal RA peer review of a stakeholder interview write-up
argument-hint: <release-folder>
---

# Internal RA peer review of a stakeholder interview write-up

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
description: Internal RA peer review of a stakeholder interview write-up
argument-hint: "[release-folder] --stakeholder <slug>"
---

# Stakeholder Interview — Review

## Purpose

Internal RA peer review of a single stakeholder interview write-up. Reviewer is a peer Lead Consultant or the Head of Delivery. The goal is to catch four kinds of problem before consolidation:

1. A tag classification that doesn't match the supporting bullet
2. A theme that's a workaround disguised as a requirement
3. A verbatim quote that's emotional but doesn't actually do diagnostic work
4. Missing follow-ups (questions the consultant should have asked but didn't)

This is **not** a sponsor-facing review.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
- The corresponding validation report

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS` and `--stakeholder <slug>`. Read the interview file and validation report. If validation has not passed, prompt: "Validation has not passed for this interview — fix tag completeness first via `/wire:stakeholder-interview-validate`."

### Step 2: Pull meeting context

If `fathom_url` is present, fetch the Fathom transcript via the Fathom MCP server. The reviewer is checking the write-up *against* the source recording, so the transcript matters here.

### Step 3: Present for review

Output the write-up. Then ask the reviewer:

```
Reviewer (peer Lead Consultant or Head of Delivery) — review the write-up. Specifically:

1. Are the four tags correct on every theme? (Especially Hierarchy tier — the rule is "lowest tier whose absence is blocking it")
2. Are any themes actually workarounds disguised as requirements?
3. Does the verbatim quote do diagnostic work, or is it just emotional?
4. What questions should have been asked but weren't?

Record anything that should change.
```

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the peer review of this stakeholder interview?",
    "header": "Interview Peer Review",
    "options": [
      {"label": "Approved", "description": "Write-up is solid and ready to feed consolidation"},
      {"label": "Approved with tag corrections", "description": "Specific tags need changing; apply inline"},
      {"label": "Schedule a follow-up", "description": "Material questions weren't asked — book a 30-min follow-up with the stakeholder"},
      {"label": "Re-draft from transcript", "description": "Write-up materially misrepresents what the stakeholder said"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

If tag corrections were called, ask:
```
List the line numbers and the corrected tags. Apply directly to the write-up.
```

Apply them inline.

If follow-up needed, append a `## Follow-up scheduled` section with the date and the unanswered questions.

If re-draft, set `interviews[<slug>].generate: not_started` and prompt to re-run `/wire:stakeholder-interview-generate` (which will pull the transcript again).

### Step 5: Update status

```yaml
interviews:
  - slug: <slug>
    review: complete    # or "pending_followup" / "pending_rework"
```

The aggregate `stakeholder_interview` review state becomes `complete` only when every interview has `review: complete`.

### Step 6: Output review summary

```
## Interview Review Complete — <slug>

**Outcome**: [Approved / Approved with tag corrections / Schedule follow-up / Re-draft]
**Tag corrections**: [N]
**Follow-up booked**: [yes/no]

### Next Steps

[If approved and at least one other interview still pending]:
Continue reviewing interviews. List remaining via /wire:status

[If this was the last interview and all are complete]:
Move to consolidation:
/wire:requirements-matrix-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
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
