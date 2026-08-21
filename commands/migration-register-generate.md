---
description: Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)
argument-hint: <release-folder>
---

# Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)

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
description: Build and maintain the per-model migration register — the source-of-truth state store for what has been migrated, from which source commit, to which BigQuery target, and how it last validated
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_register` and `artifact_file_path: migration/migration_register.csv` before proceeding.

---

# Migration Register — Generate

## Purpose

Maintains a **per-model migration register** — one row per in-scope model recording what was migrated, from which source commit, to which BigQuery target, its current state, and how it last validated. This is the queryable source of truth that the drift gate, the equivalency loop, and CI all read; it is distinct from the per-model transformation **log** (`migration.transformation_log_table`), which is an append-only audit trail, not current state.

The register is maintained **incrementally** by the migration commands (see the maintenance contract below). This command initialises it, and rebuilds/reconciles it on demand.

## Register schema

`.wire/releases/$ARGUMENTS/migration/migration_register.csv`:

| Column | Meaning |
|--------|---------|
| `model` | dbt model **or snapshot** name (unique key); for a `reverse_etl_sync` row, the normalised sync id (see Reverse-ETL sync rows below) |
| `object_type` | `model` (default), `snapshot` (an SCD-2 history object, tracked here so its migration strategy and state travel with everything else), `reverse_etl_sync` (a reverse-ETL sync, seeded from `audit/reverse_etl_audit.csv` per Reverse-ETL sync rows below, #191; its equivalence verdict comes from `reverse-etl-equivalency-validate`), `metabase_card` (a **native** Metabase card — MBQL cards are repoint-only and carried by the connection, not tracked as rows), or `metabase_dashboard` (state derives from its cards) — #184 |
| `source_path` | path to the model/snapshot in the source dbt project (e.g. `models/business/orders.sql`, `snapshots/orders_snapshot.sql`) |
| `source_layer` | source-project layer (e.g. `source_project`, `business_project`, `reporting`) |
| `last_migrated_commit` | source repo commit SHA the translated model was built from |
| `bq_target` | the **fully qualified physical target relation** (`project.dataset.table` on BigQuery; `database.schema.table` on Snowflake), resolved from the target-side manifest node's resolved config (`database`/`project`, `schema`, and `alias`; the model name only when no alias is set, dbt's own fallback), never composed from the model name (#201). For a snapshot, the fully qualified `target_schema` relation. For `metabase_card`/`metabase_dashboard` rows, the target connection + database (a reporting-layer reference, not a warehouse relation, exempt from the segment rule below). **Legacy form**: registers written before #201 carry a dbt-relative two-segment value (e.g. `de_source_project.orders`). Consumers distinguish by dot-separated segment count (three segments is a physical path, two is the legacy form) and must never guess a physical path from a legacy value: `/wire:upgrade` Step 6c re-resolves legacy rows from the manifest, and `equivalency-validate` Step 1g defines what a consumer does with a row it cannot resolve exactly (`unresolved_target`, never a guess) |
| `state` | `pending` \| `migrated` \| `drifted` \| `failed` \| `removed` \| `deferred` |
| `snapshot_strategy` | for `object_type = snapshot`: `copy_and_continue` (default) or `rebuild_from_T` — blank for models. `rebuild_from_T` is valid only with a sign-off recorded in `notes` (see below) |
| `last_equivalence_result` | `pass` \| `pass_qualified` \| `diff_vintage` \| `diff_availability` \| `diff_schema_type` \| `fail` \| `null` — the verdict of the last equivalency run for this object, per the verdict taxonomy in `specs/migration/equivalency/validate.md` (legacy registers may still carry `info`; treat it as `pass_qualified`) |
| `last_equivalence_t` | the baseline instant `T` of that equivalency run (UTC), or `null` for a live run |
| `last_validated_commit` | source commit at the last equivalency validation (lets the drift gate tell "validated-then-drifted" from "never validated") |
| `delivery_stage` | blank \| `in_pr` \| `merged` \| `production_verified` — how far past "migrated" the object has shipped. Orthogonal to `state`: `state` records translation lifecycle and health (a merged model can still go `drifted`), `delivery_stage` records delivery progress. Blank until the object enters a client PR |
| `pr_url` | URL of the client PR carrying this object (set with `delivery_stage: in_pr`; kept through `merged`/`production_verified`; cleared with `delivery_stage` if the PR closes unmerged) |
| `last_reverse_ported_commit` | The client-repo commit whose version of this model was last carried back into the delivery tree by `dbt-migration-reverse-port`. Blank means never swept: a `merged` row with a blank value is the standing reminder that the delivery tree may already be stale (wire#195) |
| `parent_release` | **Relocated rows only** (`origin: relocate` in `notes`): the parent migration release folder the model's translation came from (from `migration.parent_release`). Blank on every other row |
| `parent_model` | Relocated rows only: the model's name in the parent register (usually identical; recorded so a rename never breaks the link) |
| `parent_verdict_ref` | Relocated rows only: a reference to the parent verdict that proves the SQL being relocated — the parent register row's `last_equivalence_result` plus its evidence (`<parent_release>:<report_ref>`, e.g. `05-parent-migration:migration/equivalency_report_12.md#orders`). Blank when the parent register was unreachable at relocate time — an evidence gap the relocate-mode comparator treats as unproven (see `equivalency-validate`, Relocate-mode comparison) |
| `notes` | free text (e.g. reason for `deferred`/`failed`; for a `rebuild_from_T` snapshot, the required data-owner sign-off — name + date) |

**Why `bq_target` is physical, not dbt-relative (#201).** A dbt-relative name forces every consumer to guess the physical `project.dataset.table`, and one wave-1 post-merge verification run (2026-08-20) showed guessing fail three ways: a model whose dbt `schema` + `alias` config produces a prefix-stripped physical name (`salesforce_case` materialises as `salesforce.case`; a name-equality guess finds nothing); the same table name under two datasets, where the wrong-dataset guess produced a false divergence of 70,229 rows that a manual trace showed was an exact match (23,298 = 23,298) in the right dataset; and the reverse case, a comparison against a non-existent table that returned a silent empty result. The command that builds the relation knows the exact physical path at build time: the register records it then, and consumers resolve from the register, never by guessing. This is the physical-side counterpart of the node-identity rule (`model.<package_name>.<model_name>`, `specs/utils/dbt_manifest_parse.md` Step 3): a model name is a join key, never a physical name.

## Maintenance contract (which command writes which columns)

- **`dbt-migration-generate`** — on a successful per-model migration, upserts the row: `source_path`, `source_layer`, `last_migrated_commit` (the source snapshot SHA, from `migration_sources.dbt.commit`), `bq_target` (the fully qualified relation the build just produced, from the target-side manifest node's resolved `database`/`project` + `schema` + `alias`; never recomposed from the model name, #201), `state = migrated` (or `failed` after 5 iterations, `deferred` if its source object isn't built on target). For a **snapshot** (`object_type = snapshot`), it upserts the same way after translating the inner SELECT and running the target `dbt snapshot` adopt-and-continue, leaving `snapshot_strategy` as seeded.
- **`migration-strategy-generate` / this command** — sets each snapshot row's `snapshot_strategy` (`copy_and_continue` default; `rebuild_from_T` only with the sign-off recorded in `notes`).
- **`equivalency-validate`** — on each run, writes `last_equivalence_result` (the taxonomy verdict), `last_equivalence_t` (the baseline `T` when in baseline mode, else `null`), and `last_validated_commit` for each model checked, and appends one row per verdict to the verdict log (below). It never touches `delivery_stage`.
- **`reverse-etl-equivalency-validate`**: writes `last_equivalence_result` and `last_equivalence_t` on `object_type = reverse_etl_sync` rows and appends each sync verdict to the verdict log, exactly as `equivalency-validate` does for models. It never touches `delivery_stage`. It updates rows; this command is what creates them (#191).
- **`migration-drift-generate`** — flips `state` to `drifted` (modified upstream) or `removed`, and records the drifting commit in `notes`. It never touches `delivery_stage` — a merged model that drifts keeps its delivery progress and gains a health flag.
- **`dbt-migration-batch-raise`** — sets `delivery_stage: in_pr` + `pr_url` when a model enters a client PR, advances to `merged` on merge detection, and clears both if the PR closes unmerged.
- **`equivalency-post-merge-verify`** — advances `delivery_stage` to `production_verified` when the post-merge production comparison returns `pass` or `pass_qualified`.
- **`dbt-carveout-relocate-generate`** — on relocated rows only, writes the cross-release linkage columns `parent_release` / `parent_model` / `parent_verdict_ref` (#180), alongside the upsert it already performs.
- **`dbt-migration-reverse-port`** — writes `last_reverse_ported_commit` on a ported model, and blanks `last_equivalence_result` with an audit note, since the verdict bound to the file version the port replaced. It writes nothing else: a port changes the authored file, not the model's delivery stage.
- **`metabase-migration-generate` / `metabase-carveout-generate`** — upsert `object_type: metabase_card` rows for native cards (and `metabase_dashboard` rows derived from their cards) as manifest rows are signed off and applied; `metabase-equivalency-validate` writes their `last_equivalence_*` via the standard merge (#184).
- **`equivalency-sweep`** — blanks a superseded `last_equivalence_result` (with an audit note in `notes` naming the sweep and pattern id) when a defect-class sweep invalidates a standing verdict; it never deletes rows or verdict-log history.

This command does not duplicate that logic — it seeds and reconciles the file.

## Companion verdict log (append-only history)

The register is **current-state**: one row per object, reconciled in place, so a re-validation overwrites the previous verdict and its date is lost. The companion file `migration/migration_verdict_log.csv` (seeded from `TEMPLATES/migration/migration_verdict_log.csv`) is the **append-only** verdict history: every equivalency verdict, at every run point (`standard`, `pre_raise`, `post_merge_prod`), appends one row and no row is ever rewritten or deleted. Columns: `model, object_type, run_point, verdict, divergence_mechanism, method_class, mode, baseline_t, file_version, lane_id, report_ref, written_at`. `equivalency-validate` is the only writer (via its single-writer merge step, `specs/migration/equivalency/verdict_schema.md`). Throughput reporting and reviews read the log, not the register, for anything dated.

**Snapshot rows.** Snapshots are seeded here as `object_type = snapshot` rows from `audit/dbt_snapshots.csv`, and their `snapshot_strategy` is set from the migration strategy's "Snapshot migration" section (`copy_and_continue` by default; `rebuild_from_T` only when the strategy records a data-owner sign-off, which this command copies into `notes`). If the strategy doc has not yet assigned a strategy, seed the snapshot `copy_and_continue` and leave a note — never default a snapshot to `rebuild_from_T`, since that silently discards history.

**Reverse-ETL sync rows (#191).** Where `audit/reverse_etl_audit.csv` exists, seed one `object_type = reverse_etl_sync` row per audit row: every approach, regardless of `include_in_migration`, per the routing table in `specs/utils/reverse_etl_approach.md` (a `decommission` sync is out of scope for migration and in scope for retirement, and its row is how that retirement is tracked rather than forgotten). Before this seeding existed, no command could create the row `reverse-etl-equivalency-validate` updates, and validate's Check 2 rejected any that appeared: on one engagement, 643 in-scope syncs produced 621 branch-copy compliance checks and 8 tier-1 verdicts in one day, none with a register row to land on. Per row:

- `model`: the **normalised sync id**, the audit's `sync_id` normalised per `reverse-etl-twin-generate`'s Step 0 rule (basename, extension stripped, trailing target-warehouse marker `-bq`/`_bq`/`-bigquery`/`_bigquery` stripped, lower-cased). The audit keys on the original id and authored twins carry the marker, which is why the raw string is not the key: a raw-string join matched 6 of 609 on one engagement, the normalised join 575 of 643, with the residual explained (`decommission` syncs never get twins). Where the raw `sync_id` differs from the normalised id, record `sync_id: <raw>` in `notes`. Two audit rows normalising to the same id is an error naming both original ids, never a silent merge into one row.
- `state`: `migrated` when the twin manifest (`migration/reverse_etl_twin_manifest.csv`, or its wave-labelled variants) records the sync's twin as `authored`, joined on the normalised sync id; `pending` otherwise, which covers every `decommission` and `rebuild` sync, since neither gets a twin.
- `notes`: `approach: <migration_approach>` exactly as the audit writes it, per the closed vocabulary in `specs/utils/reverse_etl_approach.md` (an approach outside the closed set is an error naming the value and the sync, never seeded); plus `wave: <batch_id>` where `migration/migration_batching.csv` assigns the sync a wave.
- `source_path`: the sync's source config path from the twin manifest where recorded; blank otherwise.
- `last_equivalence_result`, `last_equivalence_t`, `last_validated_commit`: `null` at seed. A real verdict comes only from `reverse-etl-equivalency-validate`.
- `delivery_stage`: blank at seed. Step 2b's `--ingest-merge-state` backfills `in_pr`/`merged` from live PR state for twin files exactly as it does for models, joined back to the sync row via the normalised twin filename.

## Prerequisites

- `audit/dbt_audit.csv` exists (the in-scope model list); `audit/dbt_snapshots.csv` too if the project defines snapshots — **or**, under `--from region-tagging`, `migration/region_tags_adjudicated.csv` exists instead
- `audit/reverse_etl_audit.csv`, where the release has reverse-ETL scope: sync rows are seeded from it (#191). Its absence means no sync rows, not an error
- `migration_sources.dbt` registered (so `last_migrated_commit` can be resolved)

## Flags (#180)

- `--from region-tagging` — **carve-out bootstrap.** Seed the register from the adjudicated region-tagging output instead of the dbt audit: one row per `region_tags_adjudicated.csv` item with `adjudicated_ruling: carve_in`, mapped by `item_type` (`dbt_model` → `object_type: model`; snapshot rows from `audit/dbt_snapshots.csv` where present), `state: pending`, and the item's separation mechanism from `migration/tenant_predicate_registry.csv` recorded in `notes` (`mechanism: <value>`). This is the natural seed for a carve-out that reached delivery before its register existed — the adjudication is already the locked ruling on what is in scope. Items ruled `exclude`/`defer` are not seeded. Requires `migration.scope == tenant_carveout`; abort otherwise with `[wire] --from region-tagging applies to tenant_carveout releases only.`
- `--ingest-merge-state` — **retroactive PR ingestion.** For a release whose models reached client PRs (or main) before the register tracked them, backfill `delivery_stage` and `pr_url` from **live** repo state, and record PR-body verdicts as dated verdict-log evidence. See Step 2b. Composable with `--from region-tagging` (bootstrap then ingest) or usable alone against an existing register.

## Workflow

### Step 1: Seed or reconcile

If the register does not exist, create it from `TEMPLATES/migration/migration_register.csv` and seed one row per in-scope model from `dbt_audit.csv` (`object_type = model`), plus one row per snapshot from `dbt_snapshots.csv` (`object_type = snapshot`, `snapshot_strategy` from the strategy doc as above), all with `state = pending` and all migration/validation columns `null`, plus one row per sync from `audit/reverse_etl_audit.csv` where it exists (`object_type = reverse_etl_sync`, per Reverse-ETL sync rows above, #191). Under `--from region-tagging`, the seed source is `migration/region_tags_adjudicated.csv` filtered to `carve_in` instead (see Flags) — the seeded set is the adjudicated carve-in set, and each row's `notes` records its predicate-registry mechanism.

If it exists, **reconcile** rather than overwrite: add rows for any new in-scope models or audit syncs (`state = pending`, or `migrated` for a sync already twinned); never clobber `last_migrated_commit` / `last_equivalence_*` / `last_validated_commit` already recorded; mark rows whose model no longer exists in the dbt audit, or whose sync no longer exists in the reverse-ETL audit, as `state = removed` (do not delete the row — the history matters). A register that predates the sync seeding gains its `reverse_etl_sync` rows on the first reconcile after the reverse-ETL audit exists; nothing needs a flag for that. Where a `model` or `snapshot` row carries a legacy two-segment `bq_target` (pre-#201), re-resolve it from the target-side manifest exactly as `/wire:upgrade` Step 6c does. Never overwrite a three-segment value, and never compose a path from the model name when the manifest has no node for it: leave the legacy value and report the row.

### Step 2: Backfill from existing artifacts (first run)

On first creation, backfill state from what already happened: read the batch acceptance packs and per-model `.diff.md` files to set `state` (`migrated`/`failed`) and `last_migrated_commit` where derivable; read the latest equivalency report to set `last_equivalence_result` / `last_equivalence_t` / `last_validated_commit`. Leave unknown fields `null` rather than guessing.

### Step 2b: Retroactive PR ingestion (`--ingest-merge-state`, #180)

For each configured client repo (`migration.client_repos`), read the **live** PR series — `gh pr list --state merged` plus open PRs, filtered to this release's branches/authors — and resolve which register models each PR carried (from the PR's changed files mapped back to model names). Where the release has reverse-ETL scope, do the same over the sync config repo's PRs: a PR's twin config files map back to `reverse_etl_sync` rows via the normalised twin filename (the Step 0 rule), and the same delivery-stage mapping below applies to them.

- **`delivery_stage` comes from live repo state, never from the release folder's own status records.** A model whose file is merged to the client's base branch: `delivery_stage: merged` (+ `pr_url`); in an open PR: `in_pr` (+ `pr_url`); in a PR closed unmerged, or nowhere: `delivery_stage` blank. Where the folder's prior notes disagree with `gh`, `gh` wins and the correction is reported — stale local status is exactly the failure this flag exists to repair. Set `state: migrated` for any ingested model still `pending` (its file demonstrably shipped).
- **PR-body verdicts are evidence, ingested but marked.** A PR body carrying verdict-grade comparison evidence (counts, checksums, windows argued per model) appends one row per model to `migration/migration_verdict_log.csv`: `verdict` as stated, `run_point: standard`, `lane_id: retro-ingest`, `method_class: pr_body_evidence`, `report_ref: <pr_url>`, `written_at` = the PR's merge (or last-update) instant. These rows are dated history, not fresh proof — every ingested model is flagged **re-verify: post_merge** in `notes`, and `equivalency-post-merge-verify` is the command that replaces the prose evidence with a real production comparison. A PR body with no verdict-grade evidence ingests delivery state only, no log row.
- The ingestion is idempotent: re-running re-reads live state and reconciles; it never duplicates verdict-log rows for the same (model, pr_url) pair.

### Step 3: Write the register and update status

Write `migration/migration_register.csv`. Update status.md:

```yaml
artifacts:
  migration_register:
    generate: complete
    file: migration/migration_register.csv
    generated_date: "{{TODAY}}"
    models_total: N
    migrated: N
    drifted: N
    pending: N
    failed: N
    snapshots_total: N            # object_type = snapshot rows; 0 if none
    snapshots_rebuild_from_t: N   # snapshots assigned rebuild_from_T (each requires a recorded sign-off)
    reverse_etl_syncs_total: N    # object_type = reverse_etl_sync rows (#191); 0 if none
```

### Step 4: Output next command

```
/wire:migration-register-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact_id, `Migration Register` as artifact_name, and the `file` value from `artifacts.migration_register` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_register` as artifact, `generate` as action.

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
