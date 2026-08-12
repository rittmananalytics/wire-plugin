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
argument-hint: <release-folder> [waves | item <name> | blocking <name> | exceptions] [--json]
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

## Subcommands

- **`item <name>`** — one object's full derivation: register row, current verdict (+ window fields where present), delivery stage with the live-repo evidence, wave, drift state, parent linkage for relocated models.
- **`blocking <name>`** — why an object is not at the next stage: the failing gate, the block reason from batch-raise's eligibility table, the unresolved registry row, or the human gate it is parked on — each with the command that clears it.
- **`exceptions`** — everything that needs a decision: `manual_review_required` models, unresolved predicate rows, `fail` verdicts, drifted-while-merged models, fired cross-release triggers, ledger-answered asks still listed anywhere.

## `--json`

Emit the same numbers as JSON (waves array + unassigned + provenance block), for report and chart generation. The JSON carries the provenance header's fields — a chart built from this output stays traceable to the manifest instant and repo fetch it derives from.

## Relationship to `/wire:status`

`/wire:status` reconciles Wire artifact lifecycle across any release type; this command is the migration delivery view (stages over models/syncs). Both may be run; neither replaces the other.

## Post-Execution Hooks

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

Execute the complete workflow as specified above.
