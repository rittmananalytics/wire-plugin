---
description: Demo and stakeholder approval for semantic search
argument-hint: <release-folder>
---

# Demo and stakeholder approval for semantic search

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
description: Review AI semantic search feature with stakeholders for approval
argument-hint: <project-folder>
---

# Agentic Commerce — Semantic Search Review Command

## Purpose

Demo the semantic search feature to stakeholders, walk through the validation report, and capture approval or change requests before moving to the next feature.

## Usage

```bash
/wire:ac_semantic_search-review YYYYMMDD_project_name
```

## Prerequisites

- `semantic_search.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

Check `semantic_search.validate == pass`. If not:
```
Warning: Semantic search has not passed validation.
Run `/wire:ac_semantic_search-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Present for Review

```
## Semantic Search Review Session

**Project:** [PROJECT_NAME]
**Feature:** AI Semantic Search
**Provider:** [from validation report]
**Products indexed:** [N]

### What to Review

Please evaluate the semantic search feature:

**Relevance Quality**
- [ ] Natural language queries return relevant products (not just keyword matches)
- [ ] Typos are handled gracefully
- [ ] Vague/descriptive queries work (e.g. "gift for a cyclist")
- [ ] Relevance explanations are clear and useful

**User Experience**
- [ ] Search bar is prominent and easy to find
- [ ] Example query pills are relevant to our catalog
- [ ] Loading state is smooth (not jarring)
- [ ] Results feel fast enough for a good experience
- [ ] Active query label and clear button work well

**Integration**
- [ ] Product grid updates correctly after search
- [ ] Search results look on-brand
- [ ] No visible errors or rough edges
```

### Step 3: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `semantic_search`
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any prior discussions about search requirements or provider selection

### Step 4: Demo Script

Guide the reviewer through a live demo using these queries (adapt to actual catalog):

1. **Descriptive query**: "lightweight jersey for a hot summer ride"
   - Expected: summer/breathable products
2. **Gift intent**: "something for a cyclist who has everything"
   - Expected: premium or gift-friendly products
3. **Typo tolerance**: "cyclng shorts" (deliberate typo)
   - Expected: cycling shorts despite misspelling
4. **Contrast with keyword search**: Search for "breathable" in the old search vs semantic
   - Demonstrates the improvement

### Step 5: Gather Feedback

```
Please provide your feedback:

1. **Reviewer name and role:**
2. **Decision:**
   - [ ] Approved
   - [ ] Approved with minor notes
   - [ ] Changes requested
   - [ ] Needs discussion
3. **Relevance quality rating (1-5):**
4. **UX rating (1-5):**
5. **Specific feedback:**
6. **Example queries that didn't work well (if any):**
```

### Step 6: Record Outcome

**If approved:**
```yaml
semantic_search:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  relevance_rating: [1-5]
  ux_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
semantic_search:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 7: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `semantic_search`, action: `review`.

### Step 8: Suggest Next Steps

**If approved:**
```
## Semantic Search Review: Approved ✓

### Suggested Next Features

- **Conversational Assistant** (builds on search): 
  `/wire:ac_conversational_assistant-generate <project>`
- **Personalisation Engine** (enhances search with user context):
  `/wire:ac_personalisation-generate <project>`
```

**If changes requested:**
```
## Semantic Search Review: Changes Requested

Changes needed:
[list from feedback]

After changes: re-validate and re-review.
```

## Output

- Updated `status.md` with review outcome

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
