---
description: Draft a Slack-shaped session summary from a release's execution log
argument-hint: <release-folder> [scope]
---

# Draft a Slack-shaped session summary from a release's execution log

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
description: Draft a Slack-shaped session summary from a release's execution log
argument-hint: <release-folder> [scope]
---

# Session Summary Utility

## Purpose

Read a release's `execution_log.md` and draft a concise, Slack-post-shaped summary of what happened — artifacts generated, validated, or reviewed, their pass/fail or approval outcomes, and any open TBDs or blockers. Displays the draft for a human to read, edit, and post themselves.

**This utility never sends anything.** It has no Slack MCP call anywhere in it. It drafts text and returns it, the same way `wire/specs/utils/pr_create.md` drafts a PR body from `execution_log.md` and `status.md` without ever calling `gh pr create` until the user confirms — this spec stops one step earlier and doesn't even offer to post, because posting to a client-facing channel is a judgment call that belongs to a person, not a default.

This addresses the third-largest manual-prompt cluster identified in [wire#113](https://github.com/rittmananalytics/wire/issues/113): 21 instances on a real client migration where a consultant was asked, ad hoc in chat, to summarize a day's or session's work for posting to a client Slack channel.

## Usage

```bash
/wire:utils-session-summary 20260616_acme_migration
```

| Input | Description | Default |
|-------|-------------|---------|
| `release_folder` | Release folder path under `.wire/releases/` | (required) |
| `scope` | `today` — only execution_log.md rows from today's date. `session` — rows since the last commit on the release's base branch, or since the branch was created if there is no such commit (same boundary `pr_create.md` Step 1 uses for "the most recent session's rows"). `all` — every row in the log. | `today` |

## Prerequisites

- `.wire/releases/[release_folder]/execution_log.md` must exist (see edge case below if it doesn't)
- `.wire/releases/[release_folder]/status.md` should exist for client/engagement name and artifact display names, but is not required

---

## Workflow

### Step 1: Read the Execution Log

Read `.wire/releases/[release_folder]/execution_log.md` per the format defined in `wire/specs/utils/execution_log.md` — a Markdown table with columns `Timestamp | Command | Result | Detail`.

**Filter to scope**:
- `today` (default): rows whose Timestamp date matches today's date.
- `session`: rows since the boundary `pr_create.md` Step 1 already defines — the later of (a) the most recent commit on the release's base branch, or (b) the branch's creation. Reuse that boundary logic rather than redefining it; if this utility is invoked standalone without git context to establish that boundary, fall back to `today`.
- `all`: every row.

Drop `skill` rows (skill activation entries) from the draft — they're useful for tracing but not client-relevant. Keep only rows whose Command starts with `/wire:`.

### Step 2: Read status.md for Context

Read `.wire/releases/[release_folder]/status.md` frontmatter (best-effort — proceed without it if missing):
- `client_name`, `engagement_name` (or equivalent project-level fields)
- Each in-scope artifact's current `generate` / `validate` / `review` state, for cross-checking the log against current status
- Any entries in `blockers:` or `notes:` that look recent

### Step 3: Group Filtered Rows by Artifact

Parse each row's Command (`/wire:<artifact>-<action>`) to recover the artifact key and action. Group consecutive/related rows by artifact, so a artifact that was generated, validated (failed), regenerated, and validated again (passed) reads as one throughline rather than four disconnected lines.

For each artifact group, determine:
- **Final outcome for this scope window**: the last row's Result (`complete`, `pass`, `fail`, `approved`, `changes_requested`)
- **Whether it changed state during the window** (e.g. went from `not_started` to `complete`) vs. was just touched without a state change
- **Any failure or changes-requested detail** worth surfacing (from the Detail column)

### Step 4: Identify Open TBDs and Blockers

- Any artifact whose most recent action in the window was `fail` or `changes_requested` is an open item.
- Any entry under `status.md`'s `blockers:` list is an open item.
- Any artifact still `not_started` that the release plan expects to be in progress (cross-reference `status.md`'s artifact table) is worth a mention only if it's a genuine blocker, not routine backlog — use judgment; don't pad the summary with everything not yet started.

### Step 5: Draft the Summary

Format as a Slack message using Slack `mrkdwn` (`*bold*`, `_italic_`, `` `code` ``, `•` bullets — not GitHub Markdown headers or tables, which don't render in Slack).

Keep the register consistent with this framework's other client-facing drafts — direct and specific, no filler. Say what got done and what it means for the client, not a restatement of command names. Compare against how `pr_create.md`'s drafted PR body states artifact changes plainly ("Change" column: "generated", "validated", "reviewed and approved") rather than narrating the process.

**Template**:

```
*[Client Name] — [Release Folder] — [scope label, e.g. "Today's update" / "Session summary"]*

*Progress*
• [Artifact Display Name]: [what happened and where it landed — e.g. "generated and validated (14/14 checks passed), ready for review"]
• [Artifact Display Name]: [...]

*Open items*
• [Artifact Display Name]: [validation failure or changes-requested detail, in plain terms]
• [blocker from status.md, if any]

_No open items this [period]._  <!-- use this line instead of an empty "Open items" section if there are none -->

*Next up*
• [Logical next step per artifact, e.g. "dbt: awaiting review from [reviewer]"]
```

Omit the `*Open items*` section header entirely (not just its bullets) if there is genuinely nothing to report — an empty section with a placeholder reads worse than no section, per this framework's usual "don't pad with process notes" convention.

If nothing in scope changed at all (e.g. `scope: today` on a day with no commands run), output that fact plainly rather than drafting an empty template:
```
No Wire activity logged for [release_folder] today.
```

### Step 6: Display for Review

Output the drafted summary in full, followed by:
```
Draft above — review and post manually to the relevant Slack channel.
This utility does not post to Slack.
```

Do not call any Slack MCP tool. Do not ask "should I post this?" — there is nothing to post it with from this spec.

---

## Edge Cases

### execution_log.md missing or empty

```
No execution_log.md found for [release_folder] (or the log is empty) — nothing to summarize yet.
```
Do not fabricate a summary from status.md alone; the log is the source of truth for this spec.

### status.md missing

Proceed using only `execution_log.md`. Use the release folder name in place of client/engagement name in the header line, and skip the blockers cross-reference in Step 4.

### Multiple releases requested at once

This spec takes exactly one `release_folder`. If a multi-release digest is wanted, invoke this spec once per release and let the caller concatenate the drafts — don't add multi-release logic here.

### Pipe characters or Slack-breaking characters in Detail text

`execution_log.md` already replaces `|` with `—` in Detail text per its own Rule 4. Carry that through unchanged; don't re-introduce raw pipes when quoting Detail text in the draft.

## Output

This utility:
- Reads `.wire/releases/[release_folder]/execution_log.md` and filters to the requested scope (default: today)
- Cross-references `status.md` for client name, artifact display names, and blockers
- Drafts a Slack `mrkdwn`-formatted summary grouped by artifact, with progress, open items, and next steps
- Displays the draft in full for human review
- **Never calls a Slack MCP tool and never posts anything** — posting is always a deliberate, separate human action

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
