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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

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
