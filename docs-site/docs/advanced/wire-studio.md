---
sidebar_position: 3
title: Wire Studio
---

# Wire Studio

Wire Studio is a browser-based interface to the Wire Framework — a visual, multi-user console for running Wire commands, reviewing artifacts, and managing engagements without a local CLI environment.

It is an alternative to the Claude Code CLI for users who prefer a web interface, or for team members who don't have Claude Code installed.

## What Wire Studio provides

- **Visual engagement dashboard** — all active releases with status, phase, and artifact health at a glance
- **One-click artifact generation** — run any Wire command from a browser button, with live output streaming
- **Inline artifact review** — review and approve generated documents without leaving the browser
- **Multi-user collaboration** — team members can comment on artifacts and approve review gates from their own browser sessions
- **Execution log viewer** — full audit trail of every command, decision, and stakeholder interaction
- **Status board** — the same status report as `/wire:status`, rendered as a live web page

Wire Studio does not replace the CLI. The CLI is faster for power users running sequences of commands. Studio is for stakeholder reviews, status visibility, and team members who don't use Claude Code day-to-day.

## Deploying Wire Studio

Wire Studio is a Cloud Run service. The deployment script is at `wire-web-ui/scripts/deploy.sh`.

### Prerequisites

- Google Cloud project with Cloud Run and Artifact Registry APIs enabled
- `gcloud` CLI authenticated with `gcloud auth login`
- Docker installed and running

### Deploy

```bash
cd wire-web-ui
./scripts/deploy.sh --project my-gcp-project --region europe-west2
```

The script:
1. Builds the Studio Docker image
2. Pushes it to Artifact Registry
3. Deploys to Cloud Run with a public HTTPS endpoint
4. Prints the Studio URL

### Connect Studio to a project repository

After deployment, Studio needs to know where your Wire project repositories live. Configure repository access in Studio's admin panel at `https://[studio-url]/admin`.

For GitHub repositories:
1. Go to Admin → Repository Sources → Add GitHub
2. Authorize Studio with a GitHub personal access token (repo scope)
3. Add the repository by URL
4. Studio will auto-discover Wire releases in `.wire/releases/`

For local repositories (development use):
```bash
wire studio connect --local /path/to/project
```

## The Studio dashboard

The main dashboard shows all active engagements in the connected repositories. Each engagement card shows:
- Release type and project name
- Current phase
- Last activity timestamp
- Artifact completion counts (e.g. "12/18 approved")
- Any open review gates awaiting approval

Click an engagement card to open the engagement view.

## Running commands from Studio

In the engagement view, the **Run Command** button opens a command panel. Commands are grouped by phase. Click any command to run it — Studio streams the output in real time to the right panel.

Unlike the CLI, Studio does not auto-suggest the next command. You pick the command you want. The status board on the left always shows which artifacts are in which state, so it's clear what's pending.

## Reviewing artifacts from Studio

When an artifact reaches the review stage, Studio shows a notification badge on the artifact. Opening the artifact shows:
- The full artifact document (rendered Markdown)
- Any validation results from the preceding validate step
- A text input for feedback
- **Approve** and **Request changes** buttons

Clicking **Approve** writes the approval to the execution log with the reviewer's name and timestamp. Clicking **Request changes** saves the feedback and marks the artifact as awaiting revision. The next generate run will incorporate the feedback.

## Multi-user review

Multiple team members can comment on an artifact before it's approved. Studio shows a threaded comment panel alongside the artifact. Comments are stored in the execution log.

To assign a review to a specific team member:
1. Open the artifact in Studio
2. Click **Assign reviewer**
3. Select a team member from the list
4. They receive an email notification with a direct link to the artifact

## The execution log in Studio

The execution log is a full audit trail of every command run, every decision recorded, and every review action taken. In Studio, it's a filterable timeline with:
- Timestamp
- Command name
- Who ran it (or "Autopilot" for automated runs)
- Outcome (completed, failed, approved, feedback)
- Decision notes (for review steps)

Export the execution log as a CSV from Admin → Export → Execution log.

## Status board

The status board at `https://[studio-url]/status/[engagement-id]` renders the same output as `/wire:status` as a live web page. Share this URL with stakeholders who want a read-only view of engagement progress without Studio access.

## Connecting Studio to Claude Code (agent mode)

Wire Studio can act as a front-end for Claude Code running on a remote server. When enabled, Studio's Run Command buttons send commands to a Claude Code agent running on a Cloud Run job, rather than spawning a local session. This means:
- Studio users don't need local Claude Code installations
- All Wire commands run in a consistent, pre-configured environment
- Output streams back to the Studio browser panel in real time

To configure agent mode, see `wire-web-ui/docs/agent-mode.md` in the repository.
