---
description: Generate the Findings Playback slide deck
argument-hint: <release-folder>
---

# Generate the Findings Playback slide deck

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
description: Generate the Findings Playback slide deck — the canonical sponsor-facing exit deliverable
---

# Findings Playback Deck — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates the **Findings Playback slide deck** — the canonical, sponsor-facing exit deliverable of a SOP discovery release. The deck is a 30–55 slide HTML presentation structured around the three analyses (Hierarchy of Needs, PPT, Maturity Curve), the Vision Statement, and the Solution Initiatives, populated from the approved `discovery_analyses.md` and `requirements_matrix.md`.

The deck template is a Claude Design handoff bundled with Wire at `wire/decks/findings_playback/`. Population is done by replacing `<span class="ph">&lt;&lt;variable_name&gt;&gt;</span>` placeholders inline and toggling `data-cond` flags.

Models Phase 4 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md` (`review: complete`)
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (MoSCoW + Phase columns filled)
- `wire/decks/findings_playback/Findings Playback.html` (the deck template)

**Helpful**:
- `engagement/context.md` — for client_short, RA team
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` — for engagement_title, presenter
- All interview write-ups — for quote backfill if the analyses quote bank is thin

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery` and `discovery_analyses.review: complete`. If not, stop: "Approve the three analyses before generating the deck — run `/wire:discovery-analyses-review $ARGUMENTS` first."

2. Locate the deck template. Check the following paths in order:
   a. `wire/decks/findings_playback/Findings Playback.html` — Wire source repo layout
   b. `decks/findings_playback/Findings Playback.html` — plugin install layout
   c. `find . -name "Findings Playback.html" -path "*/findings_playback/*" 2>/dev/null | head -1` — discover anywhere else

   If not found, instruct the user to pull the latest Wire plugin (which bundles the deck) and stop.

3. Decide the output path: `.wire/releases/$ARGUMENTS/playback/findings_playback.html`. If it already exists, ask whether to **re-generate** (overwrite) or **append** (only fill empty placeholders, leave already-edited content alone — preferred for incremental updates).

### Step 2: Build the data model

Aggregate everything the deck needs into a single in-memory data dictionary, sourced as follows:

| Placeholder | Source |
|---|---|
| `engagement_title` | `engagement/context.md → engagement_name`, formatted as "Client — Engagement" |
| `client_short` | `engagement/context.md → client_name` |
| `presenter_name`, `presenter_title` | Ask the consultant: "Who is presenting the playback? (Default Lewis or Mark, per playbook)" |
| `presentation_month` | Ask: "Target month of presentation? (e.g. June 2026)" |
| `name 1..6`, `role 1..6` | RA team from `engagement/context.md → team` (up to 6 tiles) |
| `scope_context_bullet 1..3` | First three context bullets from `engagement_brief.md` — usually the "Context for this engagement" bullets |
| `interview_question 1..6` | The 6 standard playbook interview questions (canonical, not engagement-specific) |
| `requirements_total` | Row count from `requirements_matrix.md` |
| `current_state_quote 1..3` | `discovery_analyses.md → playback quote bank → Current State opener` |
| `hierarchy_diagnosis_bullet 1..4` | First 4 bullets from `discovery_analyses.md → Hierarchy of Needs diagnosis` |
| `ppt_diagnosis_bullet 2..4` | Bullets 2–4 from PPT diagnosis (bullet 1 is the lead, used elsewhere) |
| `current_state_summary_bullet 1..4` | The 4-bullet narrative arc (situation → impact → diagnosis → opportunity) — derived from PPT + Hierarchy diagnoses |
| `future_state_quote 1..3` | `discovery_analyses.md → playback quote bank → Desired Future State opener` |
| `process_quote 1..3`, `people_quote 1..3`, `tech_quote 1..3` | Per-axis dividers from quote bank |
| `process_summary_bullet 1..3`, etc. | Per-axis diagnosis bullets |
| `process headline`, `people problem headline`, `tech problem headline` | Per-axis one-line problem statements (derived from diagnoses) |
| `solution headline`, `benefits headline` | From the Solution Initiatives section of the analyses (if recorded) |
| `rec 1..3 title`, `rec 1..3 description` | From the Solution Initiatives — top three recommendations |
| `incumbent_tool`, `replacement_tool`, `incumbent on axis 1..4`, `replacement on axis 1..4` | Only filled if a tooling-replacement angle is in scope. Otherwise these placeholders remain — the consultant will manually remove or fill the relevant slide. |
| `next_step 2`, `next_step 3` | From the Sponsor decisions required list — what the sponsor needs to decide |
| `n`, `role` | Generic — Lead Consultant fills if context demands |

If the quote bank in `discovery_analyses.md` is thin (fewer than 3 quotes for a section), pull additional quotes from the interview write-ups by searching theme bullets tagged to that axis/section.

### Step 3: Word clouds and chart data

The deck has three placeholder regions for chart data and word clouds. These are not `<span class="ph">` placeholders — they're inline SVG / DOM regions. Mark them with TODO comments in the generated deck so the consultant knows where to manually populate:

- **Slide 10 (Hierarchy chart)**: bar chart SVG. Insert an HTML comment listing the per-tier counts from the matrix (`<!-- TODO Lead Consultant: paste tier counts here: Collect=N, Clean=N, ... -->`)
- **Slide 11 (PPT chart)**: bar chart SVG. Same pattern — counts for People / Process / Technology.
- **Per-axis summary slides**: word clouds. Insert a comment listing the word-cloud labels from `discovery_analyses.md → Per-axis word clouds`.

For each region, leave a small inline JS comment with the exact data the consultant should plug in. The HTML template's `deck-stage.js` runtime supports interactive edits via the `__edit_mode_set_keys` mechanism — the consultant can paste/edit in a browser if they prefer.

### Step 4: Replace placeholders

Walk the deck HTML. For every `<span class="ph">&lt;&lt;variable_name&gt;&gt;</span>`:
- If `variable_name` is in the data model, replace the entire `<span>` (including tags) with the value, properly HTML-escaped
- If not, leave the placeholder intact so the consultant can fill in manually

For `data-cond` attributes:
- `google_cloud_partner` — ask the consultant: "Include the Google Cloud Partner logo on the cover? (yes/no)". If no, replace the `data-cond="google_cloud_partner"` element with an HTML comment `<!-- Google Cloud Partner block removed -->`. If yes, leave intact.

### Step 5: Conditional sections

The full slide structure (30–55 slides) includes optional sections:

| Optional section | When to include |
|---|---|
| Lean Product Canvas slide | Only if the canvas was used in Phase 1 (check engagement_brief or context) |
| Concept explainer slide (e.g. "what is a semantic layer?") | Only if the diagnosis hinges on a concept the sponsor may not be fluent in |
| Capabilities axis (fourth axis) | Only if the inline cross-cutting Capabilities axis was used in analyses |
| Product spotlights (BigQuery, dbt, Looker, etc.) | Only if those tools are material to the recommendation |
| Tool replacement comparison ("Why not Tableau?") | Only if an incumbent-replacement angle is in scope |
| Solution Initiatives + Delivery Roadmap | Only if the playback bundles the roadmap (inline-roadmap pattern). Otherwise these slides are removed and replaced with a "Next steps" slide naming the roadmap session. |

Ask the consultant directly which optional sections to include. Remove unincluded sections by deleting the corresponding `<section data-label="...">` blocks (preserving the rest of the deck order).

### Step 6: Output the populated deck

Write the populated deck to `.wire/releases/$ARGUMENTS/playback/findings_playback.html`.

Also copy supporting assets (relative to the template):
- `wire/decks/findings_playback/assets/` → `.wire/releases/$ARGUMENTS/playback/assets/`
- `wire/decks/findings_playback/colors_and_type.css` → `.wire/releases/$ARGUMENTS/playback/colors_and_type.css`
- `wire/decks/findings_playback/deck-stage.js` → `.wire/releases/$ARGUMENTS/playback/deck-stage.js`
- `wire/decks/findings_playback/fonts/` → `.wire/releases/$ARGUMENTS/playback/fonts/`

(Asset copy can be skipped if the consultant prefers symlinks; ask if disk-conscious.)

### Step 7: Update status

```yaml
artifacts:
  findings_playback:
    generate: complete
    file: playback/findings_playback.html
    deck_html_path: playback/findings_playback.html
    generated_date: {{TODAY}}
    generated_files:
      - playback/findings_playback.html
      - playback/assets/
      - playback/colors_and_type.css
      - playback/deck-stage.js
      - playback/fonts/
```

### Step 8: Sync to document store

Follow `specs/utils/docstore_sync.md`. For findings_playback, the docstore artifact is typically a link to the deck (Confluence "Findings Playback Deck" page that links to the canonical Google Slides version once the consultant has ported it).

### Step 9: Output summary

Show:
- Total slides generated
- Placeholders still unfilled (count and list — consultant must hand-edit before the playback)
- TODO regions (chart data, word clouds) — count and slide numbers
- Optional sections included / excluded
- Path to open the deck: `open '.wire/releases/$ARGUMENTS/playback/findings_playback.html'`

```
/wire:findings-playback-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `.wire/releases/$ARGUMENTS/playback/assets/...` (copied from template)
- `.wire/releases/$ARGUMENTS/playback/colors_and_type.css`
- `.wire/releases/$ARGUMENTS/playback/deck-stage.js`
- `.wire/releases/$ARGUMENTS/playback/fonts/...`
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
