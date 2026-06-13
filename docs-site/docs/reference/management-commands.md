---
sidebar_position: 6
title: Management Commands
---

# Management Commands

Management commands operate on releases and engagements as a whole — creating, archiving, reporting status, and performing housekeeping. None of them generate or validate individual artifacts.

## `/wire:new`

Create a new release. This is always the first Wire command you run for an engagement.

```
/wire:new
```

Wire prompts for:
1. Release type
2. Client name and project name
3. Delivery start date
4. Optional: Jira project key
5. Optional: Linear project
6. Optional: Document store (Confluence space or Notion database)
7. Optional: Document store parent page/database

Wire creates:
- `.wire/releases/YYYYMMDD_<client>_<type>/` — engagement folder
- `.wire/releases/YYYYMMDD_<client>_<type>/config.yaml` — engagement configuration
- `.wire/releases/YYYYMMDD_<client>_<type>/status.md` — initial status report
- `.wire/releases/YYYYMMDD_<client>_<type>/execution_log.md` — empty execution log
- `CLAUDE.md` update — adds project context if not already present

---

## `/wire:status`

Show the current status of all active releases, or a specific release.

```
/wire:status
/wire:status <release-folder>
```

Output includes:
- Phase and artifact completion counts per release
- Any open review gates
- Any validation failures
- Jira/Linear sync status (if configured)
- Last activity timestamp

With a specific release folder, output is expanded to show every artifact and its current state.

`/wire:status` also performs reconciliation when integrations are configured — syncing any missing Jira/Linear updates and flagging divergences between the local execution log and external trackers.

---

## `/wire:archive`

Archive a completed or cancelled release. This marks the release as archived in the execution log, writes a final status snapshot, and optionally exports all artifacts to a client-facing package.

```
/wire:archive <release-folder>
```

Wire asks:
1. Reason for archiving (Completed / Cancelled / Superseded)
2. Whether to export a client package (Markdown files, rendered PDFs)
3. Whether to close associated Jira Epic / Linear Project (if configured)

Archived releases remain in `.wire/releases/` and are shown in `/wire:status` with an "Archived" badge. They are not included in active engagement counts.

---

## `/wire:status-report`

Generate a formatted status report for client or internal sharing.

```
/wire:status-report <release-folder>
/wire:status-report <release-folder> --format pdf
/wire:status-report <release-folder> --format confluence
```

Formats:
- **markdown** (default) — writes to `.wire/releases/<release>/status_report_YYYYMMDD.md`
- **pdf** — renders to PDF via headless Chrome (requires Playwright installed)
- **confluence** — publishes to the configured Confluence space (requires Atlassian MCP)

The report includes:
- Engagement summary and current phase
- Artifact status table (phase, artifact, state, last updated)
- Open items (validation failures, pending reviews, stakeholder actions)
- Recent decisions log (last 10 entries from the execution log)
- Next steps

---

## `/wire:execution-log`

View or search the execution log for a release.

```
/wire:execution-log <release-folder>
/wire:execution-log <release-folder> --filter decisions
/wire:execution-log <release-folder> --filter failures
/wire:execution-log <release-folder> --since 2024-01-15
```

Filters:
- `decisions` — show only review decisions and stakeholder feedback
- `failures` — show only validation failures and their resolutions
- `approvals` — show only approved artifacts with their approvers
- `all` (default) — show everything

---

## `/wire:utils-linear-create`

Create the Linear project hierarchy for an engagement.

```
/wire:utils-linear-create <release-folder>
```

Creates a Linear Project, Issues (one per artifact), and Sub-issues (one per lifecycle step). The Linear project and issue IDs are written to `.wire/releases/<release>/config.yaml` so subsequent commands can sync to them.

---

## `/wire:utils-doc-analyze`

Analyse a source document and extract Wire-relevant information without creating any artifacts.

```
/wire:utils-doc-analyze path/to/SoW.pdf
/wire:utils-doc-analyze path/to/SoW.pdf path/to/kickoff-notes.md
```

Output:
- Extracted deliverables with descriptions and acceptance criteria
- Wire match scores (how well each deliverable maps to an existing Wire command)
- Proposed engagement structure
- Open questions Wire can't resolve from the document alone

Useful for scoping an engagement before running `/wire:new`, and for verifying that a SoW is specific enough to drive Wire artifact generation.

---

## `/wire:utils-docstore-config`

Configure or reconfigure the document store integration for a release.

```
/wire:utils-docstore-config <release-folder>
```

This is the same configuration step offered during `/wire:new` Step 9.5, available separately for releases that were set up without a document store.
