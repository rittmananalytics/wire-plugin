---
description: Generate the Discovery Requirements Matrix from tagged interviews
argument-hint: <release-folder>
---

# Generate the Discovery Requirements Matrix from tagged interviews

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
description: Generate the Discovery Requirements Matrix from tagged interview write-ups
---

# Requirements Matrix — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Harvests every tagged theme from every stakeholder interview write-up, de-duplicates near-identical themes, and produces the **Discovery Requirements Matrix** — the structured single source of truth for the three analyses in `discovery_analyses`.

This is internal RA work. The matrix is **not** the sponsor deliverable — the Findings Playback deck is. The matrix's job is to make Phase 3 mechanical: tag harvest → de-duplicate → classify → diagnose.

Models Phase 3 Steps 1–2 (and prepares for Steps 3–8) of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/interviews/*.md` — every interview file (must all pass `/wire:stakeholder-interview-validate --all`)
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` — to read the in-scope domain list
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md` — to read priority and resolve `source_stakeholders` counts

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery`.
2. Confirm every interview file passes validation. If any are failing or missing tags, stop: "Tag failures present in [N] interview files. Run `/wire:stakeholder-interview-validate --all` and fix before consolidating. Retrofitting tags here will lose diagnostic signal."
3. Confirm every P0 stakeholder from the map has an interview write-up. If any are missing, ask the consultant whether to proceed (some P0s legitimately couldn't be booked) or pause.

### Step 2: Tag harvest

Walk every interview file. For every theme bullet, extract:
- Bullet text (verbatim)
- Domain tag (the `#<domain>` tag)
- Type tag (one of `#pain` `#requirement` `#kpi` `#risk` `#existing-asset`)
- Hierarchy tier (one of `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`)
- PPT axis (one of `#people` `#process` `#technology`)
- Source stakeholder (from the file's `slug`)
- Verbatim quote (the closest verbatim sentence from the same write-up, or the stakeholder quote at the top of the file)

Do not paraphrase. Copy bullet text verbatim into the matrix.

### Step 3: De-duplicate

Cluster identical or near-identical themes (same Hierarchy tier + same PPT axis + same domain + semantically equivalent bullet text). For each cluster:
- Choose the strongest bullet text as the canonical Title/Description
- Sum the count of source stakeholders
- Note the priority mix (e.g. "3 P0, 1 P1")
- If the sponsor is a source stakeholder, set `sponsor_backing: Y`
- Carry forward the strongest verbatim quote across all clustered sources

### Step 4: Generate Req IDs

For each de-duplicated row, assign `R-<DOMAIN>-<NN>` where `<DOMAIN>` is the upper-case domain tag and `<NN>` is a zero-padded sequence within that domain.

### Step 5: Draft the matrix

**Output**: `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`

```markdown
# Discovery Requirements Matrix: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Status**: Internal RA — pre-analyses

## Source

- Interview files: {{N}} write-ups across {{N_domains}} in-scope domains
- Tag set: enforced by `/wire:stakeholder-interview-validate`

## Matrix

| Req ID | Domain | Type | Hierarchy | PPT axis | Title | Description | Verbatim quote | Source stakeholders | Count | Sponsor backing | MoSCoW | Phase | Confidence | Source systems | Existing asset | Conflicts / open questions |
|--------|--------|------|-----------|----------|-------|-------------|----------------|---------------------|-------|-----------------|--------|-------|------------|----------------|----------------|----------------------------|
| R-RETAIL-01 | retail | pain | clean | process | Store-level conversion not trusted | Store managers cannot trust footfall numbers because SAP/EPOS reconciliation runs weekly and breaks silently. | "We can't trust the conversion numbers, so we just call head office." | Maud, Laura, Sav | 3 | Y | TBD | TBD | High | SAP, CowHills EPOS, Footfall | LD-520 | None |

Notes on the columns:
- **MoSCoW** and **Phase** are deliberately left `TBD` here. They are layered in by `/wire:discovery-analyses-generate` Step 8 (after Hierarchy / PPT / Maturity Curve placement).
- **Confidence** is the consultant's confidence that this is the right ask. High / Medium / Low.
- **Conflicts / open questions** is where you call out contradictions between stakeholders without silently picking a side.

## Conflicts log

[Cluster every contradiction across stakeholders here. Name both sides, name who said what. The Findings Playback will surface these to the sponsor as forced-decision items.]

## Coverage

- In-scope domains (from engagement brief): {{list}}
- Domains represented in matrix: {{list}}
- Domains under-represented (fewer than 3 requirements): {{list — flag in playback}}

## Tag distribution (preview — drives the analyses)

### By Hierarchy tier
| Tier | Count |
|---|---|
| Collect | N |
| Clean | N |
| Define & Track | N |
| Analyse | N |
| Optimise & Predict | N |

### By PPT axis
| Axis | Count |
|---|---|
| People | N |
| Process | N |
| Technology | N |

These counts are previewed here for sanity-check; the diagnostic prose comes in `/wire:discovery-analyses-generate`.
```

### Step 6: Update status

```yaml
artifacts:
  requirements_matrix:
    generate: complete
    file: planning/requirements_matrix.md
    generated_date: {{TODAY}}
    generated_files:
      - planning/requirements_matrix.md
```

### Step 7: Sync to document store

The Confluence / Notion mirror is the working surface for the rest of the consolidation. Follow `specs/utils/docstore_sync.md`.

### Step 8: Output summary

Show: total requirements after de-dup, breakdown by Hierarchy tier and PPT axis, count of conflicts logged, list of under-represented domains.

```
/wire:requirements-matrix-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
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
