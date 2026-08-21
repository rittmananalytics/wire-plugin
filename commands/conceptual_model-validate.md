---
description: Validate conceptual model completeness and correctness
argument-hint: <project-folder>
---

# Validate conceptual model completeness and correctness

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

## Workflow Specification

---
description: Validate conceptual model completeness and correctness
argument-hint: <project-folder>
---

# Conceptual Model Validation Command

## Purpose

Validate the generated conceptual entity model against quality criteria before presenting it to business stakeholders for review. Checks that:
- All business entities from functional requirements are represented
- All relationships have cardinality defined and labelled
- The diagram contains no column-level implementation detail (it must be conceptual, not physical)
- Entity names follow the PascalCase singular convention
- Open questions are documented rather than silently resolved
- Mermaid erDiagram syntax is correct

## Usage

```bash
/wire:conceptual_model-validate YYYYMMDD_project_name
```

## Prerequisites

- `conceptual_model`: `generate: complete`

## Workflow

### Step 1: Verify Conceptual Model Exists

1. Check `conceptual_model.generate == complete` in `status.md`
2. Check that `design/conceptual_model.md` exists

If not found:
```
Error: Conceptual model not yet generated.
Run: /wire:conceptual_model-generate <project_id>
```

### Step 2: Read Inputs

1. Read `.wire/<project_id>/design/conceptual_model.md`
2. Read `.wire/<project_id>/requirements/requirements_specification.md` (to cross-check entity coverage)

### Step 3: Run Validation Checks

Work through each check systematically. For each Critical failure, the overall result is FAIL. For Major failures, use judgement — multiple Major failures also constitute FAIL.

**Validation Checklist**:

| Check | Rule | Severity |
|-------|------|----------|
| Entity coverage | Every business noun appearing in Functional Requirements (FR-*) sections appears as an entity, or is explicitly listed in Section 4 (Out of Scope) | Critical |
| Cardinality completeness | Every relationship line in the erDiagram has a valid cardinality marker at both ends (e.g. `\|\|--o{`, `}o--o{`) | Critical |
| Relationship labels | Every relationship line has a quoted label (e.g. `"enrolled in"`) | Critical |
| No column leakage | The erDiagram block contains no `{ }` column definitions — entity-only format only | Critical |
| Mermaid syntax validity | No unclosed quotes, malformed cardinality markers, or duplicate entity definitions | Critical |
| PascalCase naming | All entity names are singular PascalCase (e.g. `Student` not `students`, `STUDENT`, or `student_record`) | Major |
| Entity descriptions | Every entity in Section 1 (Entity Inventory) has a description and at least 2 key business attributes | Major |
| Reference legibility | Every reference code cited from other artifacts (e.g. FR-n) is expanded at first mention or resolved in the Reference key table — run the `reference_legibility` check per `specs/utils/reference_legibility.md` | Major |
| Relationship narrative | Section 3 contains at least one explanatory sentence per relationship line in the diagram | Major |
| Open questions documented | Any relationship or entity that is ambiguous has been listed in Section 5 rather than silently resolved | Major |
| Out-of-scope section present | If any entities were considered and excluded, Section 4 is populated | Info |
| Volume estimates | At least some entities have volume/frequency information | Info |

### Step 4: Generate Validation Report

```
## Conceptual Model Validation: [PROJECT_NAME]

**Status**: PASS | FAIL
**Validated**: [date]

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Entity coverage | ✅/❌ | [e.g. "Assignment entity missing — referenced in FR-4"] |
| Cardinality completeness | ✅/❌ | [e.g. "STUDENT -- ENROLMENT line missing cardinality"] |
| Relationship labels | ✅/❌ | |
| No column leakage | ✅/❌ | |
| Mermaid syntax validity | ✅/❌ | |
| PascalCase naming | ✅/⚠️ | |
| Entity descriptions | ✅/⚠️ | |
| Relationship narrative | ✅/⚠️ | |
| Open questions documented | ✅/⚠️ | |
| Out-of-scope section | ✅/⚠️ | |
| Volume estimates | ✅/⚠️ | |

### Issues Found

[List each Critical and Major issue with location and suggested fix. Example:]
❌ CRITICAL: Entity 'Assignment' missing — referenced in FR-4 (assignment mark tracking)
   → Add Assignment entity to Section 1 and erDiagram

❌ CRITICAL: Relationship line "STUDENT -- ENROLMENT" has no cardinality markers
   → Change to "STUDENT ||--o{ ENROLMENT : \"enrolled in\""

⚠️ MAJOR: 'pastoral_note' should be 'PastoralNote' (PascalCase)
   → Rename entity throughout document

### Next Steps

[If PASS]:
  /wire:conceptual_model-review <project_id>

[If FAIL]:
  Fix the issues listed above in design/conceptual_model.md, then re-run:
  /wire:conceptual_model-validate <project_id>
```

### Step 5: Update Status

```yaml
conceptual_model:
  validate: pass | fail
  validated_date: [today]
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `conceptual_model`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Entities in Requirements That Are Genuinely Out of Scope

If an entity is referenced in requirements but is intentionally out of scope (e.g. a future phase deliverable), it must appear in Section 4 with the reason. It is not a validation failure if it is explicitly listed there — it is a failure only if it is completely absent.

### Relationship in Diagram Not Explained in Narrative

If Section 3 is missing a relationship that appears in the erDiagram, add an ⚠️ Major flag. The narrative is important for business stakeholders who cannot read ERD notation.

### Mermaid Syntax Errors

Common Mermaid erDiagram syntax issues to check:
- Relationship labels must be in double quotes: `"label"` not `'label'` or unquoted
- Cardinality markers: valid options are `||`, `o|`, `|o`, `o{`, `{o`, `}|`, `|}`, `}o`, `o}`
- Entity names cannot contain spaces or hyphens (use PascalCase to avoid)
- Each entity can only be defined once in the diagram

## Output

- Validation report (displayed to user)
- Updates `.wire/<project_id>/status.md` with validate result and date

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
