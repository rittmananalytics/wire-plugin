---
description: Validate four-tag completeness on every theme bullet
argument-hint: <release-folder>
---

# Validate four-tag completeness on every theme bullet

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
description: Validate four-tag completeness on every theme bullet of a stakeholder interview write-up
argument-hint: "[release-folder] [--stakeholder <slug> | --all]"
---

# Stakeholder Interview — Validate

## Purpose

Mechanically enforces the **mandatory four-tag rule** on every theme bullet of every interview write-up. This is the most consequential validation in the SOP discovery release type — the three analyses in `discovery_analyses` are only as good as the tags applied here, and the playbook's failure modes explicitly warn against retrofitting tags from the consolidated matrix.

Validate runs in two modes:
- `--stakeholder <slug>` — validate one interview write-up
- `--all` — validate every interview in the release and produce a coverage report

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md` (per-stakeholder mode)
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`

## Workflow

### Step 1: Locate and parse

1. Resolve `$ARGUMENTS`. Read the stakeholder map.
2. Decide mode:
   - If `--stakeholder <slug>` provided → validate that single file
   - If `--all` provided (or no arg) → list every file under `planning/interviews/` and validate each

### Step 2: Per-file checks

For each interview file, run these checks. **Definitions are closed sets** — anything outside these sets fails.

#### Front-matter
- [ ] `slug` present and matches the file name
- [ ] `stakeholder_name`, `title`, `department`, `priority` populated
- [ ] `interview_date` is an ISO date
- [ ] `fathom_url` present, OR a note in the body explaining "no recording"

#### Stakeholder quote
- [ ] `## Stakeholder quote` section present and not the template placeholder text
- [ ] Quote is in blockquote (`>`) format

#### Meeting summary
- [ ] At least 5 of the 7 standard bullets present (role, painful thing, decision/workflow, KPIs, existing assets, risks, scope notes)

#### Theme bullets — the four-tag rule
For every line under `### Theme list` (or any `## Themes` subsection that contains bullet themes):

- [ ] Bullet text is non-empty
- [ ] Bullet ends with a tag cluster matching the regex pattern (case-sensitive):
  - **Domain tag**: `#[a-z][a-z0-9-]+` (any kebab-case lowercase tag — domain set is configurable per engagement; do not hard-code)
  - **Type tag**: exactly one of `#pain` `#requirement` `#kpi` `#risk` `#existing-asset`
  - **Hierarchy tag**: exactly one of `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`
  - **PPT tag**: exactly one of `#people` `#process` `#technology`
- [ ] **Exactly one tag from each of the four sets** appears on the line. Zero or two tags from a set is a FAIL on that line.
- [ ] Uncertain tags (`?` suffix, e.g. `#process?`) are surfaced as WARNINGs — the consultant must confirm before review.

A line with `#retail #pain #clean #process` passes. A line with `#retail #pain #process` fails (missing Hierarchy). A line with `#retail #pain #clean #analyse #process` fails (two Hierarchy tags).

### Step 3: Cross-file coverage check (`--all` mode only)

- [ ] Every P0 stakeholder in the stakeholder map has an interview file
- [ ] Every P1 stakeholder in the stakeholder map has an interview file OR is explicitly marked deferred in `status.md → interviews[].generate: deferred`
- [ ] Every interview file's `slug` matches a row in the stakeholder map

### Step 4: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/interviews/_validation_report.md` (covers all files in `--all` mode) or `.wire/releases/$ARGUMENTS/planning/interviews/<slug>_validation.md` (single-file mode).

```markdown
# Stakeholder Interview Validation Report

**Release**: $ARGUMENTS
**Mode**: [single / all]
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Per-file summary

| File | Theme bullets | Fully tagged | Missing tag | Uncertain (`?`) | Result |
|---|---|---|---|---|---|
| maud-bakker.md | 12 | 12 | 0 | 0 | ✅ |
| sav-jansen.md | 9 | 7 | 2 | 0 | ❌ |
| ola-jin.md | 11 | 9 | 0 | 2 | ⚠️ |

## Failures (must fix before consolidation)

### sav-jansen.md — line 47
> Store-level conversion is not visible in real time `#retail #pain #process`

Missing Hierarchy tag. Add one of: `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`.

### sav-jansen.md — line 52
> Footfall counts are unreliable `#retail #pain #clean #process #people`

Two PPT tags (`#process` and `#people`). Pick the binding constraint and remove the other.

## Warnings (resolve before review)

### ola-jin.md — line 31
> `#process?` suffix — consultant confirmation needed

## Coverage (--all mode)

| Stakeholder map row | Priority | Interview file | Status |
|---|---|---|---|
| Maud Bakker | P0 | maud-bakker.md | ✅ |
| Sav Jansen | P0 | sav-jansen.md | ❌ failing |
| Ola Jin | P1 | ola-jin.md | ⚠️ |
| Pieter Hoekstra | P1 | — | ❌ missing file |

## Next Steps

1. Fix every FAIL line by adding/removing tags as flagged
2. Resolve `?` suffixes by confirming the tag choice
3. Re-run validation
4. When PASS: /wire:stakeholder-interview-review $ARGUMENTS --stakeholder <slug>
```

### Step 5: Update status

For each validated file:
```yaml
interviews:
  - slug: <slug>
    validate: complete   # or "failed"
    themes_tagged: <count>
```

Aggregate `stakeholder_interview` state in `artifacts`:
- `validate: complete` — only when every interview file passes
- `validate: failed` — if any file fails

### Step 6: Output summary

Show the worst N failures with file:line references. Don't show every check — just what needs fixing.

## Output Files

- Validation report file(s) as above
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
