---
wire_schema: "1.0"
command: utility
artifact: fathom_sync
domain: utils
release_types: []
action_type: utility
logs_execution: true
description: Pull new Fathom call transcripts and summaries into .wire/engagement/calls/, then extract findings
argument-hint: (engagement-level — no release-folder argument)

---

# Fathom Sync — Pull Call Transcripts and Extract Findings

## Purpose

Fetch meeting recordings from Fathom for the current engagement's client, writing transcripts, summaries, and action items into structured markdown files under `.wire/engagement/calls/`, then extracting an analytical findings document per call. This is the persistence counterpart to `specs/utils/meeting_context.md` (which does a live, ad-hoc Fathom search at review time) — this spec writes durable, committed artifacts once, so the whole team can read them later without re-querying Fathom.

Two callers, two modes:

- **Automatic mode** — invoked silently by `skills/fathom-sync/SKILL.md` once per session. No flags, no interactive output beyond a brief one-line note if something new was found. Never fires if `fathom_sync.enabled` is not `true` in `.wire/engagement/context.md`.
- **Manual mode** — invoked directly via `/wire:utils-fathom-sync [flags]`. Always runs when explicitly invoked, regardless of `fathom_sync.enabled` — running the command is itself the consent. Full flag support and a full report.

## Prerequisites

- Fathom MCP server configured and reachable. If not, **skip silently in automatic mode** (exactly like any other optional MCP integration elsewhere in Wire); in manual mode, tell the user plainly that Fathom isn't configured and stop.
- `.wire/engagement/context.md` must exist with `fathom_sync.client_domain` set to a real, non-RA domain (automatic mode only — see Step 2's safeguard; manual mode still requires a usable domain to search on, see below).

## Configuration (read from `.wire/engagement/context.md`)

```yaml
fathom_sync:
  enabled: false          # resolved at /wire:new Step 2 from the client domain given, or set manually later
  client_domain: null     # required for enabled: true — matches calendar invitees, never rittmananalytics.com
  last_synced: null       # ISO date; drives the default --after window for incremental pulls
```

## Workflow

### Step 1: Parse Arguments (manual mode only)

| Flag | Default | Description |
|------|---------|--------------|
| `--after` | `fathom_sync.last_synced`, or engagement `created_date` if never synced | Only fetch calls after this date (YYYY-MM-DD) |
| `--before` | today | Only fetch calls before this date (YYYY-MM-DD) |
| `--limit` | `50` | Max calls per search page |
| `--dry-run` | false | List calls without writing files |
| `--no-findings` | false | Skip findings extraction |

In automatic mode, use the defaults for all of these — no flags are ever passed.

### Step 2: Resolve the Search Domain — and Refuse Unsafe Ones

**This is the step that stops RA-internal meetings ending up in a client (or any) repo. Do not skip or soften it, in either mode.**

1. Read `.wire/engagement/context.md`'s `fathom_sync.client_domain`.
2. **If it's blank/unset**: automatic mode skips silently (nothing to search on safely). Manual mode: ask the user for a client domain directly (`What's the client's email domain? e.g. acme.com`) — do **not** fall back to searching by `client_name` as free text in either mode. A text search on a company name can't distinguish "this specific client" from any other meeting that happens to mention the same words, and the whole point of this step is a filter narrow enough to trust.
3. **If it resolves to Rittman Analytics' own domain** (`rittmananalytics.com`, case-insensitive, or any subdomain of it) **— or if `client_name` is self-referential** ("Rittman Analytics", "RA", or a close variant) — refuse outright, regardless of mode or what `fathom_sync.enabled` says:
   - Automatic mode: skip silently, exactly as if `fathom_sync.enabled` were `false`. Do not log this as an error — it's a correct refusal, not a failure.
   - Manual mode: tell the user plainly why —
     ```
     This engagement's client domain resolves to Rittman Analytics' own domain (or the
     client name looks self-referential). Fathom Sync matches by calendar-invitee domain
     — your own domain is on every meeting your team has, internal or client-facing, so
     it can't safely narrow anything here. Refusing to run rather than pulling in
     unrelated internal meetings. If this genuinely is an external client whose name or
     domain happens to look like this, double-check .wire/engagement/context.md's
     client_domain and client_name before re-running.
     ```
   - Stop. Do not proceed to Step 3 under any circumstances once this check has triggered — this overrides everything else in this spec, including an explicit manual invocation with flags.
4. Otherwise, a real external domain is confirmed — proceed to Step 3 using it as the search filter.

### Step 3: Search Fathom

Use the Fathom MCP server's meeting-listing/search tools (`search_meetings`, `list_meetings`, or whichever the connected server actually exposes — inspect what's available rather than assuming a fixed signature) to find candidate meetings within the `--after`/`--before` window whose calendar invitees include the confirmed `client_domain` from Step 2:

- If the tool accepts a domain/company filter directly, use it.
- If it only accepts a free-text term, search on `client_domain` (not `client_name` — the domain is the thing Step 2 confirmed is safe) and, from the results, keep only meetings with at least one calendar invitee whose email matches that domain, discarding the rest client-side.
- Filter results to the date window client-side if the tool doesn't support date filtering natively.
- Paginate through all matching pages if the tool returns a cursor/next-page token; keep going until exhausted.

Collect all candidate meetings (title, date, recording ID, attendees, URL) — full transcript/summary content is fetched per-meeting in Step 5, not here. A candidate with zero invitees actually matching `client_domain` (a false positive from a text search) does not count as a match — discard it rather than writing it.

### Step 4: Filter to New Meetings Only

**Filename convention**: `YYYY-MM-DD_<sanitized-title>.md` under `.wire/engagement/calls/` — sanitize the title (lowercase, spaces to hyphens, strip non-alphanumeric except hyphens, truncate to 60 chars).

For each candidate meeting, check whether a file with that name already exists. If so, skip it — never overwrite an existing call file. Only meetings with no existing file are "new" and proceed to Step 5.

If `--dry-run`, list what would be fetched (title, date, new vs. already-present) and stop here without writing anything.

### Step 5: Fetch and Write Each New Meeting

For each new meeting, fetch the full transcript, summary, and action items (via `get_meeting_transcript`, `get_meeting_summary`, or whatever the connected MCP server's equivalent tools are named), then write:

```markdown
---
title: "{meeting.title}"
date: "{meeting.created_at}"
recording_id: {meeting.recording_id}
url: "{meeting.url}"
share_url: "{meeting.share_url}"
recorded_by: "{meeting.recorded_by.name}"
attendees:
{for each calendar_invitee}
  - name: "{invitee.name}"
    email: "{invitee.email}"
    external: {invitee.is_external}
{end for}
---

# {meeting.title}

**Date:** {formatted date}
**Recorded by:** {meeting.recorded_by.name}
**Attendees:** {comma-separated list of invitee names}
**Recording:** {meeting.url}

## Summary

{meeting summary, markdown-formatted — or "No summary available."}

## Action Items

{for each action_item}
- [ ] {action_item.description} — *{action_item.assignee.name}* ({action_item.recording_timestamp})
{end for}
{if no action items: "No action items recorded."}

## Transcript

{for each transcript_item}
**{speaker.display_name}** ({timestamp}):
{text}

{end for}
{if no transcript: "No transcript available."}
```

Ensure `.wire/engagement/calls/` exists before writing. If a meeting has no transcript or summary available, still write the file with the placeholder text shown above rather than skipping it — a partial record is better than none.

### Step 6: Extract Findings (skip if `--no-findings` or `--dry-run`)

For each **newly written** call file only (never for calls that were already on disk before this run):

**Filename**: same base name as the call file, with `_findings` appended before `.md`. Skip if it already exists (shouldn't happen for a genuinely new call file, but check anyway — never overwrite).

**How**: Read the full call file (summary, action items, transcript). Before writing, read 2–3 of the most recent existing `*_findings.md` files in `.wire/engagement/calls/` as style and structure references — match their voice, depth, and section conventions rather than inventing a new format each time. If this is the very first call synced for this engagement, use the structure below as-is.

**Structure**:

```markdown
# Findings: {meeting.title} — {short subtitle describing the call's focus}

**Date:** {date}
**Recording:** [Fathom]({meeting.url}) | [Share Link]({meeting.share_url})
**Attendees:** {name (role)} for each attendee, noting silent/absent/partial attendance
**Duration:** ~{duration}
**Purpose:** {1–2 sentence summary of the call's goal and context relative to prior sessions}

---

## 1. {First topic heading}

{Narrative analysis — not a transcript rehash. Explain what was discussed, what was decided, and why it matters. Include direct quotes where they capture a decision, insight, or strong opinion. Attribute quotes.}

---

[... one numbered section per major topic, sub-headings (###) for sub-topics ...]

## N-2. Decisions Captured

| # | Decision | Owner |
|---|----------|-------|
| 1 | **{Decision}** — {brief context} | {Owner} |

## N-1. Open Questions / Follow-ups

{Table or list of unresolved questions, with context and owner.}

## N. Action Items

- [ ] **{Owner}:** {Action description}
```

**Guidelines**:
- Synthesise, don't summarise — the call file already has the raw summary; findings add analytical value (what changed, what was decided, what it means downstream).
- Connect to prior sessions where the conversation builds on or reverts earlier decisions.
- Attribute decisions and quotes: `> *"quote"* — Name`.
- Skip small talk and off-topic segments.
- Be opinionated about implications — state what a decision means for downstream artifacts, releases, or architecture, don't just record that it happened.

### Step 7: Update Sync State

Update `.wire/engagement/context.md`'s `fathom_sync.last_synced` to today's date (or the latest meeting's date if it's later than today for any reason — shouldn't happen, but don't regress the marker).

### Step 8: Report

**Automatic mode**: if zero new meetings were found, say nothing at all — this is the expected, common outcome for most sessions. If one or more were found, one brief line: `Synced N new Fathom call(s) into .wire/engagement/calls/.`

**Manual mode**: always report in full, regardless of whether anything new was found:

```
## Fathom Sync Complete

- **Calls found:** {total candidates in window}
- **Files written:** {written} (skipped {skipped} — already on disk)
- **Findings written:** {findings_written} (skipped {findings_skipped})
- **Date range:** {after} to {before}
- **Output:** .wire/engagement/calls/

### Calls
| Date | Title | Recording ID | Call File | Findings |
|------|-------|---------------|------------|----------|
| ... | ... | ... | written/skipped | written/skipped |
```

## Error Handling

- Fathom MCP not reachable: skip silently (automatic) or tell the user plainly and stop (manual) — never treat this as a bug.
- No `client_domain` in context.md: same treatment as above (Step 2).
- `client_domain` resolves to Rittman Analytics' own domain, or `client_name` looks self-referential: refused, per Step 2 — not an error, a correct outcome.
- A meeting with no transcript or summary: write the file anyway with placeholder text (Step 5) — never skip a meeting just because part of it is missing.
- Never fail silently in manual mode — every error gets a clear, direct message. In automatic mode, never surface an error to the user at all; log nothing, just don't sync this session and try again next session.

## Notes

- This spec never manages a Fathom API key directly — it goes through the Fathom MCP server, configured once per user via `/mcp` (Claude Code) or `gemini mcp` (Gemini CLI), same as every other MCP-backed Wire feature.
- To change which client's calls sync for this engagement, edit `fathom_sync.client_domain` directly in `.wire/engagement/context.md`. Step 2's safeguard re-runs on every invocation, so an edit that resolves to RA's own domain is refused the same way it would be at `/wire:new`.
- The findings-extraction step (Step 6) is the most valuable and most expensive part of this workflow — it's a genuine analytical pass over each transcript, not a mechanical extraction. This is deliberately not skipped by default; use `--no-findings` (manual mode) if you want the raw call files without it.
