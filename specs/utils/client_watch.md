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
description: One client-watch tick — read the client channel for replies to tracked posts and the client repos for merged PRs, record rulings in the answers ledger, fire the configured post-merge action
argument-hint: <release-folder>

---

# Utils — Client Watch

## Purpose

One tick of the client-communication watch (#179). During delivery, two classes of client signal arrive asynchronously and go stale when nobody is watching: replies in the client channel (rulings, answers to open asks) and merges of our PRs in the client repos. On a live engagement, both ran as session-local practice — and its absence as product produced two documented failures: questions the client had already answered were re-asked (twice), and merged PRs sat undetected until someone thought to look.

This command is designed to run headless on a schedule (a cron/scheduler invoking one tick), configured entirely from status.md — nothing is hardcoded.

## Configuration (status.md)

```yaml
client_comms:
  slack_channel_id: "<id>"          # required; unset disables the tick cleanly with a note
  ask_list_max: 5                   # consumed by utils-ask-list-generate, kept here as the one config block
  answers_ledger: "decisions.md"    # release-relative path to the dated answers ledger
  post_merge_action: "/wire:equivalency-post-merge-verify"   # fired when an own PR merges
```

Client repos come from `migration.client_repos` — the same list `dbt-migration-batch-raise` and `utils-ci-parity` read; this command adds no second repo registry.

On a `bi_migration` release the tick reads two more signals and fires two more actions, both configured from blocks that already exist: a merge to the registered `migration_sources.lookml` repo fires `/wire:migration-drift-generate <release>` (the LookML changed under a translated view), and a commit to the `client_repos` entry with `role: bi_target_model` fires `/wire:omni-model-reverse-port <release>` (a client modeller changed the Omni model). Both are reported once, with the commit, like a merged PR.

## State

`.wire/releases/$ARGUMENTS/client_comms/watch_state.json` — the tracked-post list (message refs this release has posted to the channel and is awaiting replies on) and the last-tick cursors (per-channel last-read timestamp, per-repo last-seen merged PR). Rewritten at the end of each tick; a killed tick loses at most one tick's cursor advance and the next tick re-reads idempotently.

## Workflow (one tick)

### Step 1 — Read the channel

Read `client_comms.slack_channel_id` since the last cursor. For each reply that answers a tracked post or states a ruling ("option B", "approved", "use the June floor"), append an entry to the answers ledger (`client_comms.answers_ledger`):

```markdown
## {{DATE}} — <topic>
**Asked**: <the tracked post's question, one line>
**Answer (verbatim)**: "<the client's words, quoted exactly>"
**Consequence**: <what this settles — the config set, the gate cleared, the approach ruled out>
**Ref**: <channel permalink>
```

The verbatim quote is the point: a paraphrase is how a ruling drifts. Remove the answered post from the tracked list. A reply that is discussion rather than an answer stays tracked, noted.

### Step 2 — Read the client repos

For each `migration.client_repos` entry, `gh pr list --state merged` since the last cursor, filtered to this release's PRs (the register's `pr_url` values). For each newly-merged PR:

1. Advance its models in `migration/migration_register.csv` to `delivery_stage: merged` (the same transition `dbt-migration-batch-raise` Step 7 performs on demand — one contract, two triggers).
2. Fire `client_comms.post_merge_action` for the merged models (default: `/wire:equivalency-post-merge-verify`).

### Step 3 — Report once

Terminal report only (the fleet's report-once protocol, `specs/utils/migration_fleet.md`): new answers recorded (count + topics), PRs merged (count + urls), actions fired, posts still tracked. A tick with nothing new reports one line and exits.

### Step 4 — Update state

Rewrite `client_comms/watch_state.json` with the advanced cursors and the surviving tracked-post list.

## The ledger as a gate

The answers ledger is not an archive — it is the input to the re-ask guard. Any command about to surface a question to the client (`utils-ask-list-generate` mechanically; anything else by convention) checks the ledger first: an entry matching the question means the client has already answered, and the answer is used, not re-asked. Re-asking an answered question is the single fastest way to burn client patience with an agentic delivery.

## Post-Execution Hooks

After the tick, run:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
