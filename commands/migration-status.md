---
description: Operational status view — per-wave exclusive model/sync stages, drift partition, provenance header, item/blocking/exceptions subcommands, JSON output
argument-hint: <release-folder> [waves/item/blocking/exceptions] [--json]
---

# Operational status view — per-wave exclusive model/sync stages, drift partition, provenance header, item/blocking/exceptions subcommands, JSON output

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
description: The migration's operational status view — per-wave model and sync stages derived live from the manifest, the register, and a fresh read of the client repos, never from committed rollups
argument-hint: <release-folder> [waves | item <name> | blocking <name> | blocked-syncs | exceptions] [--json]
---

# Migration Status

## Purpose

One answer to "where are we", derived live (#179 item 6). Before this command, per-wave progress was compiled by hand and four people could give four different answers to the same question, because each was reading a different stale rollup. The rule that ended that: **every number derives, at ask time, from the dbt manifest, the register, and a live read of the client repos — never from a committed rollup or a remembered figure.**

This is a read-only reporting command. It writes nothing but its own output.

## Provenance header (mandatory)

Every invocation prints, before any table:

```
manifest : <engine> · parsed <UTC instant> · snapshot <source commit>
register : migration/migration_register.csv · <row count> rows
repos    : <each migration.client_repos url> · fetched <UTC instant>
```

**Merged state comes from a live repo read (`gh` / `git fetch` against each client repo), never from the register** — the register's `delivery_stage` is the working record, but this view is the one that gets quoted to clients, so it re-derives merge state from the repos each run and reports any register row it corrects.

## The waves table (default subcommand)

One row per wave (wave ids from `migration/migration_batching.csv`; models with no wave row are reported as an unassigned count, excluded from wave rows). Model columns are **exclusive stages** — every model in exactly one, so the columns sum to the wave's scope:

| Stage | A model counts here when |
|---|---|
| `to-do` | No translated file exists yet |
| `translated` | Translated (`state: migrated`), no current passing verdict |
| `eqv-ok` | Current verdict `pass`/`pass_qualified`, `delivery_stage` blank |
| `in-PR` | `delivery_stage: in_pr` (live PR still open) |
| `merged` | On the client's base branch (live read), not yet production-verified |
| `prod-verified` | `delivery_stage: production_verified` |

Assignment is by **highest stage reached** (tests mirror it: `wire/tests/platform_migration/validate_migration_status_stages.py`): `prod-verified > merged > in-PR > eqv-ok > translated > to-do`. **Drift is a partition, not a stage** — a `state: drifted` model keeps its stage column and is counted again in the wave's `drifted` partition column, so delivery progress and health stay separately visible (the register's own rule).

**Sync columns** (when the release has reverse-ETL scope), also exclusive:

| Sync stage | A sync counts here when |
|---|---|
| `not-started` | No twin authored anywhere |
| `authored-on-branch` | Twin exists on an unmerged branch or draft PR |
| `in-PR` | Twin in an open, non-draft PR |
| `merged` | Twin on the client's main (live read) |

`authored-on-branch` exists because a main-only count once misread several hundred authored twins as not-started — work that existed, on branches, invisible to a count that only read main. Branch and draft-PR reads are part of the live repo read.

**`blocked` is a sync partition, not a stage (v3.11.6).** A Hightouch model reads a warehouse table; if that table is not migrated and merged, the sync cannot be worked at all. Alongside its exclusive stage, every sync is counted again in the wave's `blocked` partition when any of its upstream warehouse objects has not reached `merged` — the same partition-not-stage treatment `drifted` gets for models, and for the same reason: "where is this sync" and "can this sync be worked" are different questions and collapsing them loses one.

Derive it by joining the sync's `warehouse_objects` (from `audit/reverse_etl_audit.csv`, which resolves them for every model type) to the register's model rows, and taking the lowest stage across them. Read the sync side from the register's `reverse_etl_sync` rows, which `migration-register-generate` seeds from the audit on the normalised sync id (wire#191), and say so in the provenance header. A register with no sync rows predates that seeding: read the sync side from the audit directly, say so in the provenance header, and recommend a register re-run. The derivation is the same either way, since the join needs only sync→table and table→stage.

Before this, nobody could answer "which syncs are blocked on an unmerged table" without deriving it by hand each time, so the answer was recomputed, inconsistently, by whoever was asked.

**Card columns** (when the release has a Metabase scope, #184), exclusive per native card: `to-do` (no manifest row applied), `translated`/`carved` (manifest row applied), `eqv-ok` (current `metabase-equivalency-validate` verdict `pass`/`pass_qualified`), `cut-over` (on the production target connection). MBQL cards are counted once as a repoint-only total, not per-card rows. Dashboards report derived state: done when every constituent card is.

## Subcommands

- **`item <name>`** — one object's full derivation: register row, current verdict (+ window fields where present), delivery stage with the live-repo evidence, wave, drift state, parent linkage for relocated models.
- **`blocking <name>`** — why an object is not at the next stage: the failing gate, the block reason from batch-raise's eligibility table, the unresolved registry row, or the human gate it is parked on — each with the command that clears it. For a **sync**, this names each upstream warehouse object that has not reached `merged`, with that object's current stage, so the answer is "blocked on these two tables" rather than "blocked".
- **`blocked-syncs`** — every blocked sync **by name**, each with its blocking upstream objects and their stages, grouped by the blocking object so one unmerged table shows all the syncs waiting on it. That grouping is the useful direction: it turns a list of blocked syncs into a ranked list of tables worth merging next.
- **`exceptions`** — everything that needs a decision: `manual_review_required` models, unresolved predicate rows, `fail` verdicts, drifted-while-merged models, fired cross-release triggers, ledger-answered asks still listed anywhere, and any twin whose `primaryKey` failed the casing rule or whose destination is in the live-destination set (`reverse-etl-migration-validate` Checks 13–14). From v3.11.7 it also lists every model at `merged` or `production_verified` whose `last_reverse_ported_commit` is blank, and every model whose verdict a reverse-port superseded: the first is a delivery tree that may already be stale, the second is a re-verification owed. All of these are silent in the running system, which is why they need one place that asks.

## `--json`

Emit the same numbers as JSON (waves array + unassigned + provenance block), for report and chart generation. The JSON carries the provenance header's fields — a chart built from this output stays traceable to the manifest instant and repo fetch it derives from.

## Workflow

### Step 1: Resolve the inputs, live

1. Parse the source dbt project to a manifest (`specs/utils/dbt_manifest_parse.md` — scratch directory, no warehouse connection) and record the engine, parse instant, and snapshot commit.
2. Read `migration/migration_register.csv` (abort with `[wire] No migration_register.csv — run /wire:migration-register-generate $ARGUMENTS first.` if absent), `migration/migration_batching.csv` for wave membership (models with no wave row become the unassigned count), and `migration/migration_verdict_log.csv` where present. Where the release has reverse-ETL scope, also read `audit/reverse_etl_audit.csv` for each sync's `warehouse_objects` and `migration/reverse_etl_twin_manifest.csv` for authored twins.
3. **Fetch each `migration.client_repos` repo live** (`git fetch` + `gh pr list` covering open, draft, and merged PRs, plus branch enumeration for sync twins). Record each fetch instant. If a repo is unreachable, say so in the provenance header and mark its derived columns `unverified` — never silently substitute the register's memory of merge state.

### Step 2: Derive the stages

Assign every model its exclusive stage (the table above; live merge state wins over the register's `delivery_stage`, and any correction is listed), partition drift, derive sync stages (including authored-on-branch from the branch/draft-PR read), partition blocked syncs by joining each sync's `warehouse_objects` to its upstream models' stages, and derive card stages where a Metabase scope exists. Register rows the live read corrects are reported under the table.

### Step 3: Render

Print the provenance header, then the requested subcommand's output (`waves` default; `item` / `blocking` / `blocked-syncs` / `exceptions` as asked). Under `--json`, emit the JSON document instead, carrying the provenance fields and the blocked-sync edges (sync → blocking objects), so a chart can show the merge order that unblocks the most syncs.

## Relationship to `/wire:status`

`/wire:status` reconciles Wire artifact lifecycle across any release type; this command is the migration delivery view (stages over models/syncs). Both may be run; neither replaces the other.

## Post-Execution Hooks

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

Execute the complete workflow as specified above.
