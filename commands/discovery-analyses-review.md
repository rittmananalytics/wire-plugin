---
description: Internal RA review of the three analyses (HoD + peer consultant)
argument-hint: <release-folder>
---

# Internal RA review of the three analyses (HoD + peer consultant)

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
description: Internal RA review of the three analyses (Head of Delivery + peer consultant)
---

# Discovery Analyses — Review

## Purpose

The internal RA review gate before the Findings Playback deck is generated. Reviewer is the **Head of Delivery + one peer Lead Consultant**. This is the playbook's Phase 3 Step 10 review — its job is to challenge the diagnoses, especially the Maturity pin, before the analyses get baked into a sponsor-facing deck.

Not sponsor-facing.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read inputs.

### Step 2: Pull document store comments

If a document store is configured, follow `specs/utils/docstore_fetch.md` — reviewers often annotate the Confluence mirror with margin comments.

### Step 3: Present for review

Output:
1. The Maturity pin and justification
2. The Hierarchy diagnosis bullets + chart counts
3. The PPT diagnosis bullets + chart counts
4. The Sponsor decisions required list
5. Phase 1 MoSCoW summary (Must/Should counts)

Then prompt:

```
Review focus — the playbook's explicit challenge points:

1. **Maturity pin** — is it placed too generously? Prior engagements have landed at Data Chaos and the engagements were better for it. If the prose doesn't justify the pin, push back.

2. **Hierarchy/PPT consistency** — does the Hierarchy chart contradict the PPT diagnosis? (E.g. Hierarchy top-heavy + PPT diagnosis says foundations are missing → one of them is wrong.)

3. **Diagnosis specificity** — are the bullets specific enough to land with the sponsor, or are they consultant-speak?

4. **Phase 1 scope** — does Phase 1 fit the SoW budget? If 28 rows are Phase 1 Must and the SoW says 6 weeks, something has to give.

5. **Vision Statement** — the deck will derive its Vision Statement from these analyses. Is the diagnosis strong enough that the Vision Statement will write itself? If not, the analyses aren't ready.
```

Then `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the internal RA review of the three analyses?",
    "header": "Discovery Analyses Review",
    "options": [
      {"label": "Approved", "description": "Ready to draft the Findings Playback deck"},
      {"label": "Approved with edits", "description": "Specific diagnosis bullets or word-cloud labels need tightening"},
      {"label": "Re-pin Maturity Curve", "description": "Pin is too generous or too harsh — re-place with evidence"},
      {"label": "Re-analyse", "description": "Material issue with Hierarchy/PPT classification or Phase scoping — go back to Step 3"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

Apply inline edits if approved-with-edits. For pin re-placement, ask for the new pin + justification and apply directly. For re-analyse, append a `## Review Decisions` section listing what needs to change and reset `discovery_analyses.generate: not_started`.

### Step 5: Update status

```yaml
artifacts:
  discovery_analyses:
    review: complete    # or "pending_rework"

sponsor_validation:
  maturity_pin: "<confirmed pin>"   # only set if review approves
```

### Step 6: Output review summary

```
## Discovery Analyses Review Complete

**Outcome**: [Approved / Approved with edits / Re-pin / Re-analyse]
**Maturity pin (confirmed)**: [Data Chaos / Order / ...]
**Edits applied**: [N]

### Next Steps

[If approved]:
Generate the Findings Playback deck:
/wire:findings-playback-generate $ARGUMENTS

[If re-analyse]:
Update the analyses:
/wire:discovery-analyses-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
