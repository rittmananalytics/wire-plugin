---
wire_schema: "1.0"
command: generate
artifact: utils
domain: utils
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Derive the top-N client ask list from the register's blocker taxonomy, capped and guarded against re-asking anything the answers ledger already holds
argument-hint: <release-folder> [--max N]

---

# Utils — Ask List Generate

## Purpose

Derives the client ask list — the handful of questions and unblocks the delivery needs from the client right now — from the release's own state, instead of a consultant compiling it by hand (#179). Two documented failures motivate the two rules baked in: a 50-item ask list the client pushed back on in writing (hence the hard cap), and questions re-asked after the client had already answered them (hence the ledger guard).

**The output is a draft for the consultant to review and send. It is never auto-posted.**

## Configuration

- `client_comms.ask_list_max` in status.md (default 5) — the hard cap; `--max N` overrides for one run.
- `client_comms.answers_ledger` (default `decisions.md`) — the dated answers ledger `utils-client-watch` maintains.

## Workflow

### Step 1 — Collect candidate asks from the blocker taxonomy

Candidates come from machine state, not memory — each with its blocking reason, the models/objects it blocks, and the count:

- Register rows blocked on client-side inputs: `deferred` models whose `notes` name a client dependency (a source object not yet landed, a grant not yet made).
- `dbt-migration-batch-raise --dry-run` block reasons that resolve to a client action (an unmerged client base branch, a repo permission).
- Unresolved tenant-predicate registry rows awaiting a client ruling (`region-tagging-review` pile).
- Open human gates whose owner is the client (`data-residency-assessment-review` DPO items, UAT attestations).
- `migration-drift` findings needing a client decision (a removed source model with live downstream syncs).
- Any `cross_release_triggers` entry whose condition needs client-side confirmation.

### Step 2 — The re-ask guard (mechanical)

Check every candidate against the answers ledger before it can enter the list. A candidate whose topic matches a ledger entry — same object/gate/config key, or a normalised-question match — is **refused a slot**: it is listed separately under "already answered" with the ledger entry's date and verbatim answer, and the answer is applied instead of the question being re-asked. Tests mirror this guard (`wire/tests/platform_migration/validate_ask_list_guard.py`).

### Step 3 — Rank and cap

Rank the surviving candidates by unblock value (models unblocked, gates cleared — largest first; a cutover-path blocker outranks a long-tail model). Take the top `ask_list_max`. Everything below the cap is retained in the draft's "parked asks" appendix, not silently dropped — the cap bounds what the client is asked, not what the release tracks.

### Step 4 — Write the draft

`.wire/releases/$ARGUMENTS/client_comms/ask_list_{{DATE}}.md`: the capped list (one ask per line: the question, what it unblocks, the count), the "already answered" section (asks the guard refused, with their ledger answers), and the parked appendix. The consultant edits and sends; on sending, `utils-client-watch` tracks the post for replies.

### Step 5 — Report

One line per section count. Never post to any channel from this command.

## Post-Execution Hooks

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
