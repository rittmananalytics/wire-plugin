---
description: Validate the three analyses (chart shape, diagnosis, Maturity pin evidence)
argument-hint: <release-folder>
---

# Validate the three analyses (chart shape, diagnosis, Maturity pin evidence)

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
description: Validate the three analyses — completeness, chart shape, diagnosis grounding, Maturity pin evidence
---

# Discovery Analyses — Validate

## Purpose

Checks that the three analyses are complete, internally consistent, grounded in the matrix evidence, and ready to drive the Findings Playback deck. This validation is the last gate before client-facing deliverables; failures here propagate into the deck.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- All interview write-ups

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read all inputs.

### Step 2: Hierarchy analysis checks

- [ ] All five tiers appear in the distribution table (even if some have count 0)
- [ ] Counts in the distribution table match the actual `Hierarchy` column in the requirements matrix (cross-check)
- [ ] Diagnosis section has 4–6 bullets
- [ ] At least 2 of those bullets reference a specific verbatim quote
- [ ] No diagnosis bullet is generic boilerplate ("the client needs to invest in their data foundations" — flag as too vague)
- [ ] Per-tier supporting quotes section has at least one quote per non-zero tier

### Step 3: PPT analysis checks

- [ ] All three axes appear (People / Process / Technology) with counts
- [ ] Counts match the `PPT axis` column in the matrix
- [ ] Diagnosis has 4–6 bullets and names a binding constraint axis explicitly
- [ ] Word clouds have 6–12 labels per axis
- [ ] Word cloud labels are not the same as the axis name (i.e. not just `#People` `#Process` — actual themes)
- [ ] Per-axis supporting quotes present

### Step 4: Maturity Curve checks

- [ ] Pin is exactly one of the five stages
- [ ] Justification has 3–5 bullets
- [ ] Each justification bullet cites either a verbatim quote or a specific row from the matrix
- [ ] Pin is consistent with the Hierarchy and PPT distributions:
  - If Hierarchy is bottom-heavy (Collect/Clean dominate) and PPT diagnosis names Process or Technology as binding, pin should be **Data Chaos** or **Order** — flag if higher
  - If Hierarchy is top-heavy and PPT diagnosis is People-led, pin can be **Democratisation** or higher
  - Otherwise flag for reviewer confirmation

### Step 5: MoSCoW + Phase checks

- [ ] Every row in the requirements matrix now has a MoSCoW value (no remaining `TBD`)
- [ ] Every row has a Phase value
- [ ] Phase 1 row count is realistic for the SoW commercial envelope (flag a WARNING if >25 rows — usually means too much made it into Phase 1)

### Step 6: Conflict resolution checks

- [ ] Every conflict in the matrix Conflicts log has an entry in the `Sponsor decisions required` section, OR has been resolved with an explicit RA-side decision recorded
- [ ] No conflict is silently picked (i.e. row appears in matrix with one classification but no decision record)

### Step 7: Quote-bank checks

- [ ] Current State opener has 3–4 quotes
- [ ] Desired Future State opener has 2–3 quotes
- [ ] Each per-axis divider has 3 quotes
- [ ] Every quote is found verbatim in at least one interview write-up

### Step 8: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`

```markdown
# Discovery Analyses Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Hierarchy of Needs

| Check | Result | Note |
|---|---|---|
| All five tiers in table | ✅ | |
| Counts match matrix | ✅ | |
| Diagnosis bullets | ✅ | 5 bullets, 3 with quotes |

## PPT

| Check | Result | Note |
|---|---|---|
| All three axes present | ✅ | |
| Word cloud completeness | ⚠️ | Technology word cloud has only 4 labels — add 2 more |

## Maturity Curve

| Check | Result | Note |
|---|---|---|
| Pin set | ✅ | Data Chaos |
| Justification | ✅ | |
| Pin consistent with distributions | ✅ | Bottom-heavy hierarchy + Process-binding PPT supports Data Chaos |

## MoSCoW + Phase

| Check | Result | Note |
|---|---|---|
| Every row tagged | ✅ | |
| Phase 1 size | ⚠️ | 28 rows in Phase 1 — consider deferring some to Phase 2 |

## Sponsor decisions

3 unresolved conflicts surfaced — all in the `Sponsor decisions required` section. ✅

## Quote bank

All quotes verifiable in source interviews. ✅

## Issues to Resolve

[List FAILs and WARNINGs]

## Next Steps

[If PASS]:
Internal RA review (Head of Delivery + peer):
/wire:discovery-analyses-review $ARGUMENTS

[If FAIL]:
Fix the listed issues and re-run validation.
```

### Step 9: Update status

```yaml
artifacts:
  discovery_analyses:
    validate: complete   # or "failed"
```

### Step 10: Output summary

## Output Files

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`
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
