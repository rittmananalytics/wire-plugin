---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Draft a Slack-shaped session summary from a release's execution log
argument-hint: <release-folder> [scope]
workload: mechanical
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

Read `.wire/releases/[release_folder]/execution_log.md` per the format defined in `wire/specs/utils/execution_log.md` — a Markdown table with columns `Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD)` (older rows may lack the trailing columns; parse positionally and treat missing cells as unknown).

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
