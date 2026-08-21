---
description: Sponsor playback session — Sponsor Validation Checklist (the canonical gate)
argument-hint: <release-folder>
---

# Sponsor playback session — Sponsor Validation Checklist (the canonical gate)

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
description: Sponsor playback session — the canonical client-facing review gate
---

# Findings Playback — Review

## Purpose

**The canonical client-facing review gate of a SOP discovery release.**

This is not an internal review. The review action *is* the sponsor playback meeting — the deck is presented live (by Lewis or Mark per the playbook), the meeting is recorded via Fathom, and the **Sponsor Validation Checklist** is captured at the close.

State transitions:
- `complete` after the deck has been generated and validated
- `reviewed` after the playback meeting has been held (Fathom recording attached)
- `approved` **only when every item on the Sponsor Validation Checklist is `true`**

If any checklist item is `no`, the release stays at `reviewed` and a 30-minute follow-up sponsor session is scheduled (explicit in the playbook's failure modes).

Models Phase 4 (playback meeting + Sponsor Validation Checklist) of the Canonical Discovery Playbook.

## Inputs

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md` (must be PASS or PASS WITH WARNINGS)
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm validation has passed. If FAIL, stop: "Resolve validation failures before holding the playback."
2. Confirm `status.md → sponsor_validation.vision_statement_excerpt` is set. If null, prompt the consultant to set it now from the deck's Vision Statement slide. The playback is partly about the sponsor signing off on this — it needs to exist.

### Step 2: Capture playback meeting context

Ask the consultant:

```
Has the playback meeting been held?

(a) Yes — recorded via Fathom, ready to capture the Sponsor Validation Checklist
(b) Not yet — confirm date and presenter
```

If (b): record the planned date and presenter under `status.md → sponsor_validation.playback_date` and `sponsor_validation.preferred_delivery_option: null`, then stop with: "Re-run this command after the playback has been held."

If (a): proceed.

### Step 3: Pull Fathom transcript

Ask for the Fathom URL for the playback recording. Use the Fathom MCP server to pull:
- Full transcript
- Meeting summary
- Sponsor's verbal endorsements (or refusals) on each of the seven Sponsor Validation Checklist items

This is the most important Fathom integration in Wire — the sponsor's verbal "yes, this is what we want" against the Vision Statement is, per the playbook, the most important artefact in the engagement after the SoW itself.

### Step 4: Pre-fill the checklist from the transcript

For each of the seven Sponsor Validation Checklist items, walk the transcript and propose a value (`true` / `false` / `unclear`). Surface the supporting quote (verbatim) for each.

Then present each item to the consultant for confirmation:

```
For each of the 7 Sponsor Validation Checklist items, confirm the value based on the Fathom transcript and your in-room recall.

1. **Maturity Curve pin agreed.**
   Proposed: <true/false/unclear> based on quote: "<verbatim>"
   Confirm? (yes / no / change to false / change to unclear)

2. **Hierarchy of Needs diagnosis agreed.** ...
3. **PPT diagnosis agreed.** ...
4. **Vision Statement endorsed (both paragraphs).** ...
5. **Solution Initiatives confirmed.** ...
6. **Preferred Delivery Option named (Build / Pair / Coach).** ...
7. **Open conflicts resolved (or follow-up scheduled).** ...
```

For item 6, also capture the named delivery option ("build" / "pair" / "coach" / null) under `sponsor_validation.preferred_delivery_option`.

For any `unclear` or `false`, ask:

```
What follow-up action is needed for this item?
```

### Step 5: Determine the review outcome

If every item is `true`, outcome = **Approved (playback signed off)**.

If any item is `false` or `unclear`, outcome = **Reviewed — follow-up required**. Schedule a 30-min sponsor follow-up session within 1 week. Record the follow-up date under `sponsor_validation.follow_up_session`.

### Step 6: Record the result

Update `status.md`:

```yaml
sponsor_validation:
  playback_held: true
  playback_date: <YYYY-MM-DD>
  playback_fathom_url: <URL>
  maturity_pin: "<confirmed pin>"
  vision_statement_excerpt: "<first 200 chars of vision statement>"
  preferred_delivery_option: "<build|pair|coach|null>"
  checklist:
    maturity_pin_agreed: <true|false>
    hierarchy_diagnosis_agreed: <true|false>
    ppt_diagnosis_agreed: <true|false>
    vision_statement_endorsed: <true|false>
    solution_initiatives_confirmed: <true|false>
    delivery_option_named: <true|false>
    conflicts_resolved: <true|false>
  follow_up_session: <YYYY-MM-DD or null>

artifacts:
  findings_playback:
    review: complete       # = playback held and checklist captured
                           # Note: this is "reviewed" in workflow terms,
                           # not "approved". Approved = checklist all true.
```

### Step 7: Write the Playback Meeting Notes

**Output**: `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`

```markdown
# Findings Playback — Meeting Notes

**Date**: <YYYY-MM-DD>
**Presenter**: <Lewis / Mark>
**Fathom recording**: <URL>
**Sponsor**: <name>
**Outcome**: <Approved (signed off) | Reviewed — follow-up required>

## Sponsor Validation Checklist

| # | Item | Result | Supporting quote |
|---|---|---|---|
| 1 | Maturity Curve pin agreed (<pin>) | ✅ / ❌ | "<quote>" |
| 2 | Hierarchy of Needs diagnosis agreed | ✅ / ❌ | "<quote>" |
| 3 | PPT diagnosis agreed | ✅ / ❌ | "<quote>" |
| 4 | Vision Statement endorsed | ✅ / ❌ | "<quote>" |
| 5 | Solution Initiatives 1–5 confirmed | ✅ / ❌ | "<quote>" |
| 6 | Preferred Delivery Option named (<option>) | ✅ / ❌ | "<quote>" |
| 7 | Open conflicts resolved | ✅ / ❌ | "<quote>" |

## Decisions taken

[Bullet list — what the sponsor decided in the meeting]

## Concerns raised (and how they were addressed)

[Bullet list]

## Follow-ups

- [ ] Owner — action — due date

## Next session

[If approved]: Delivery Roadmap session (or release-spawn directly).
[If follow-up required]: 30-min sponsor session on <date> to resolve <items>.
```

### Step 8: Sync to document store

Follow `specs/utils/docstore_sync.md`. The Playback Meeting Notes go to the Confluence "Playback Meeting Notes" page named in the playbook folder structure (`5. Findings Playback / Playback Meeting Notes`).

### Step 9: Output review summary

If approved:
```
## Findings Playback Review — Approved ✅

All 7 Sponsor Validation Checklist items signed off.

**Maturity pin**: <pin>
**Preferred Delivery Option**: <build/pair/coach>
**Vision Statement endorsed**: yes

### Next Steps

1. Generate the Delivery Roadmap:
   /wire:delivery-roadmap-generate $ARGUMENTS

2. Or spawn Release 1 directly:
   /wire:release-spawn $ARGUMENTS
```

If follow-up required:
```
## Findings Playback Review — Follow-up Required ⚠️

Items not yet endorsed:
- [list]

**Follow-up session**: <date>

The release will remain at `reviewed` until every checklist item is true. Do not start Release 1 until the playback is approved — the playbook's failure-mode table specifically calls out the catastrophic cost of skipping this.
```

### Step 10: Approval gate

The release-level "approved" state is only set when:
- `sponsor_validation.playback_held == true`, AND
- every `sponsor_validation.checklist.*` is `true`

This is checked by `/wire:status` and surfaced as a hard gate before `/wire:release-spawn` can chain into a delivery release.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/playback/findings_playback.html` (no body changes, but the review captures Fathom URL etc)
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`
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
