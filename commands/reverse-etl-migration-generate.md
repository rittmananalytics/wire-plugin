---
description: Generate Hightouch sync migration runbook — repoint, rewrite, rebuild
argument-hint: <release-folder> [--wave id]
---

# Generate Hightouch sync migration runbook — repoint, rewrite, rebuild

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

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'reverse-etl-migration-generate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: reverse_etl_migration
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: reverse_etl_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Generate Hightouch reverse ETL migration runbook — add target-warehouse syncs to the existing GitHub-Sync repo as PR-gated changes, reuse destinations in place, translate models drift-aware, and cut over with two client-merged PRs
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_migration` and `artifact_file_path: migration/reverse_etl_migration_runbook.md` before proceeding.
Follow `specs/utils/migration_preflight.md` with `caller: reverse_etl_migration` and `batch_ref: reverse_etl` — run Checks 1–3 before generating; if any fail, output the blockers and stop. Check 4 (decoy mapping + scoped credential) is run after Step 4b and again before the cutover PRs are prepared.

---

## Data Safety — Read Before Proceeding

Before modifying any Hightouch configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT modify, disable, or re-point any source-backed Hightouch syncs.
  The existing source-warehouse syncs remain active as the rollback path
  throughout this entire phase.

All changes are staged as PULL REQUESTS for the client to review and merge.
  RA does NOT enable/disable syncs or mutate the workspace directly. The PR
  gate is the safety control.

New test syncs carry DECOY destination IDs only (see Step 4b). Production
  destination IDs are ABSENT from the test syncs until the cutover PR.
  Exception: under the additive_dedicated_destination topology, dedicated-mode
  syncs carry their confirmed dedicated destination ID from authoring — a
  destination the Step 2 gate proved no existing sync writes to. Step 4b is
  skipped for those syncs.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not create syncs pointing to these):
  [list each production project ID]
```

If any action would modify a source-backed sync, enable/disable a sync outside a client-merged PR, send a test sync to a production destination ID, or create a sync pointing to a production project listed in `data_safety.production_projects`, stop and report the conflict before proceeding.

---

# Reverse ETL Migration — Generate

## Purpose

Generates a step-by-step runbook for migrating every in-scope Hightouch sync from the source warehouse to the target warehouse. The default topology is **additive PR-gated syncs in the existing GitHub-Sync repo**: Hightouch's config (models, syncs, destinations) lives in a Git repository, and GitHub Sync carries models and syncs but **not destinations** — so a separate workspace would force re-creating and re-authenticating every destination. Instead, add a new batch of target-warehouse syncs alongside the existing source-warehouse syncs in that same repo, reusing the existing destination definitions in place. Every change is staged as a pull request for the client to review and merge — the PR gate is the safety control, the same model used for dbt and Fivetran migration. RA never executes enable/disable or mutates the workspace directly. Cutover is two client-merged PRs: one disables every source-origin sync, one enables every target-origin sync. The runbook covers model SQL translation (drift-aware), Customer Studio rebuilds, Lightning schema provisioning, sync-level transformation review, a decoy destination mapping that keeps production destination IDs out of the test syncs until cutover, and a preview-based validation procedure run against a frozen source baseline.

Parallel-workspace and in-place API re-point remain documented as alternatives, no longer the default — see Step 2. A fourth topology, `additive_dedicated_destination`, covers the carve-out shape where every new destination is already provisioned, dedicated to the new syncs, and never shared with an existing sync: no decoys, and cutover collapses to one client-merged PR (Step 2, Step 8).


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Prerequisites

- `target_setup review: approved` — target warehouse schemas and objects exist
- `reverse_etl_audit review: approved`
- `dbt_migration: complete` for any batch containing models referenced by Hightouch dbt-type syncs (cannot validate those syncs until their dbt models exist on target)
- **Per-sync source-model scope check** — each in-scope sync's source object must exist on the target before that sync is translated. Syncs whose source object is not yet built on target are deferred, not included (enforced per-sync in Step 4-pre).
- `migration/migration_batching.csv` exists — required only when running with `--wave`

## Flags

- `--wave <id>` — restrict this run to the syncs `migration/migration_batching.csv` assigns to this wave. Resolution is identical to `dbt-migration-generate`'s Step 1w: normalise the wave id, load `migration_batching. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).csv` (abort if missing), filter to rows where `batch_id` matches **and** `object_type == "reverse_etl_sync"`, then cross-reference each matched `object_id` against `reverse_etl_audit.md`'s sync identifiers for the full per-sync detail. Print the mandatory resolved-sync preview before proceeding. If rows match the wave but none are `reverse_etl_sync` rows, print `[wire] Wave <id> has no reverse-ETL sync objects — nothing to migrate for this command.` and stop cleanly.
- No flag — process every sync with `include_in_migration: true` (today's behaviour, unchanged).

When `--wave` is supplied, the runbook and decoy-mapping outputs are wave-labelled (`migration/reverse_etl_migration_runbook_{wave_id}.md`, `migration/reverse_etl_decoy_mapping_{wave_id}.csv`), and each wave gets its own PR sequence (Step 8) — a wave's target-warehouse syncs are additive alongside any prior wave's, exactly as a wave's dbt models are additive alongside prior waves in the same GitHub-Sync repo.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode
- `.wire/releases/$ARGUMENTS/status.md`
- `.wire/releases/$ARGUMENTS/audit/ingestion/mds_variant_columns.csv` — per-release **type-drift manifest**: columns whose source type does not carry over to the target landing format (e.g. a Snowflake `VARIANT` that lands as `STRING` under BigLake Iceberg rather than as BigQuery `JSON`). Optional — if absent, treat as empty and proceed, but note in the runbook that no drift manifest was available. Expected columns: `source_object, column_name, source_type, target_landing_type, notes`.
- `.wire/releases/$ARGUMENTS/migration/dbt/**/*.diff.md` — the dbt_migration per-model diffs. Where a referenced model was already migrated by dbt_migration, mirror any type reconciliation it recorded rather than re-deriving it.
- Canonical platform pair files at `wire/platform_pairs/<source>_to_<target>/` (translation guide, type mapping) — the generic translation source, overridden by the drift manifest per Step 4c.

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved`. Confirm `reverse_etl_audit review: approved`. If `dbt_migration` exists, confirm which batches are complete and note which rewrite_model and dbt-type syncs are unblocked.

If prerequisites are not met, output the blockers and stop.

Activate the `hightouch` skill for API connection details and the workspace / GitHub Sync model.

### Step 1w: Resolve `--wave` (only when `--wave` is used)

Resolve the in-scope sync set per the **Flags** section above. This replaces "every sync with `include_in_migration: true`" in Step 4 with the wave-resolved subset — the rest of the workflow (topology, translation, decoy mapping, validation, PR sequence) is otherwise unchanged.

### Step 2: Choose the migration topology

Decide and record which topology the runbook follows. **Default to additive syncs in the existing GitHub-Sync repo.**

- **Additive syncs in the existing GitHub-Sync repo (default).** Detect — or, where the deployment mechanism cannot be confirmed from the audit, assume — that GitHub Sync is the deployment mechanism: the Hightouch config (models, syncs, destinations) lives in a Git repository and is synced to the one production workspace. Add a **new batch of target-warehouse syncs** in that same repo, each reading from the target warehouse, **alongside** the existing source-warehouse syncs. **Reuse the existing destination definitions in place** — never re-create or re-authenticate them. Every change is staged as a pull request for the client to review and merge; RA does not execute enable/disable or mutate the workspace directly. This is the recommended path: GitHub Sync carries models and syncs but **not destinations**, so a separate workspace would force re-creating and re-authenticating every destination, and the PR gate gives the same review-and-merge safety control already used for dbt and Fivetran.

- **Parallel workspace (alternative).** Available when the Hightouch plan supports multiple workspaces (Business and above) **and** destinations can be re-authenticated without operational cost. Build a new workspace for the target warehouse and validate there, leaving the production source-backed workspace running and unmodified. **Limitation:** GitHub Sync is per-workspace and does not carry destinations — a new workspace requires re-creating and re-authenticating every destination connection, which is why this is no longer the default. If this path is chosen, record why, and account for the destination re-authentication work.

- **In-place API re-point (alternative).** Only when neither GitHub Sync nor a second workspace is available. The existing syncs' source connection is re-pointed from source to target warehouse within the one workspace via the API. Highest risk: there is no parallel environment, no PR gate, and the production config is mutated directly. If this path is chosen, record why in the runbook.

- **Additive syncs to dedicated, never-shared destinations (`additive_dedicated_destination`).** Same additive PR-gated mechanics as the default, selectable when the destinations for the new syncs are confirmed already-provisioned **and** not shared with any existing sync — the tenant carve-out shape, where the client provisions a new tenant-only destination (e.g. a fresh ad-platform audience or messaging workspace) before any sync exists. There is no live shared object for the decoy mechanic to protect, and no re-authentication burden the parallel-workspace path avoids, so neither applies.

  **Selection gate, per destination.** The topology requires per-destination confirmation that (a) the destination object exists on the target side, and (b) no existing sync writes to it. Evidence for (b) reuses Check 14's machinery (`reverse-etl-migration-validate`): build once the complete destination set of every source-warehouse sync on the config repo's default branch; a candidate dedicated destination id appearing in that set **is shared**, and the topology is refused for that sync. Evidence for (a) is a workspace/API read of the destination object, or the client's written confirmation, recorded in the mapping's `notes` (Step 4b). If the default branch cannot be read, the set is unknown and no sync is eligible — the gate refuses, it never assumes; record `gate_unverified` in the sync's notes. When both conditions fail, record the refusal as shared: set membership is the error-severity condition.

  **Per-release topology, per-sync fallback.** Topology is recorded once per release — `topology:` in status.md is a scalar (Step 9), and the twin manifest carries no topology column, so per-release is what the existing structure supports cleanly. The per-sync outcome lives in the destination mapping's `destination_mode` column (Step 4b): a mixed estate is allowed, and a sync whose destination fails the gate falls back to the default decoy path (`destination_mode: decoy`) without changing the release topology. Tests mirror the gate, the PR-sequence selection, and the twin pointing rule: `wire/tests/platform_migration/validate_dedicated_destination.py`.

Confirm the deployment mechanism (GitHub Sync repo present?), the plan tier, and the chosen topology with the user before continuing.

### Step 3 — Default: prepare the additive PR-gated branch in the existing repo

(Use Step 3-alt-A for the parallel-workspace alternative, Step 3-alt-B for the in-place API re-point alternative, or Step 3-alt-C for the dedicated-destination topology.)

The Hightouch config repo reflects the one production workspace. Work additively inside it — never in a fork or a second workspace:

1. **Branch the existing Hightouch config repository.** Create a working branch off the repo's default branch (e.g. `migration/reverse-etl-target-syncs`). All new syncs and any model changes are committed here and raised as PRs — never committed to the default branch directly.
2. **Add the target-warehouse source connection** to the workspace config in the repo (the source definition reading from the target warehouse). This is additive — the existing source-warehouse source connection is left in place.
3. **Author the new batch of target-warehouse syncs** as new config files alongside the existing ones. Each new sync reads from the target-warehouse source (Step 4 translates its model), and points at the **decoy destination ID** for its production destination (Step 4b) — never the production destination ID.
4. **Reuse the existing destination definitions in place.** Do not create, rename, or re-authenticate any destination. The new test syncs reference the existing destination *type* via their decoy IDs (Step 4b); production destination IDs are swapped in only by the cutover PR.
5. **Open PR A — "add target-warehouse test syncs"** for the client to review and merge. This PR is purely additive: new source connection + new disabled/decoy test syncs. It touches no existing source-backed sync. Merging it deploys the test syncs via GitHub Sync.
6. Proceed to Step 4 — model translation is committed to the same working branch and flows through PRs.

The existing source-warehouse syncs are not modified by any PR until cutover (Step 8 sequence).

### Step 3-alt-C — Dedicated-destination variant of the additive path

(Only if `additive_dedicated_destination` was chosen in Step 2.) Follow the default Step 3 with two differences:

1. **Dedicated-mode syncs point directly at the real dedicated destination id from the start** — no decoy. The Step 2 gate has already proven the id appears in no existing sync's destination set, so there is no live shared object a mistaken enable could reach.
2. **Step 4b is skipped for dedicated-mode syncs** — the decoy mechanic's own justification is destination reuse, and a dedicated destination is not reused, so there is nothing for a decoy to protect. In a mixed estate the fallback (decoy-mode) syncs follow the default Step 3 and Step 4b unchanged.

The twin rules are unchanged in every other respect: twins are authored paused, and no command enables a sync.

### Step 3-alt-A — Parallel-workspace alternative: build the target environment

(Only if the parallel-workspace alternative was chosen in Step 2.)

GitHub Sync is configured per workspace — a repository reflects one workspace's configuration, not the whole organisation, and **does not carry destinations**. Build the parallel environment, and budget for destination re-authentication:

1. **Clone the Hightouch config repository** the production workspace syncs to; rename the clone to mark it as the target-warehouse migration workspace.
2. **Create a new Hightouch workspace** for the target warehouse environment.
3. **Configure GitHub Sync** in the new workspace to point at the cloned repository.
4. **Re-create and re-authenticate every destination connection** in the new workspace — GitHub Sync does not carry these. Record the destinations requiring re-auth.
5. **Create the target-warehouse source connection** in the new workspace.
6. Proceed to Step 4 — model translation is committed to the cloned repo and deployed into the new workspace via GitHub Sync (or applied via the API against the new workspace's objects).

The production workspace is not modified at any point in this path.

### Step 3-alt-B — In-place API re-point alternative: prepare the re-point

(Only if the in-place API re-point alternative was chosen in Step 2.)

Add the target-warehouse source connection to the existing workspace alongside the source one. Syncs will be re-pointed to it per Step 4, via:

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sourceId": "<TARGET_SOURCE_ID>"}' \
  "https://api.hightouch.com/api/v1/syncs/<SYNC_ID>"
```

Rollback: re-apply the original `sourceId` via the same endpoint. Keep syncs disabled until validated (Step 5).

### Step 4: Translate models by approach

Load the in-scope syncs — the Step 1w-resolved set under `--wave`, otherwise every sync from the audit with `include_in_migration: true` — and group by migration approach. Process repoint first (lowest risk), then rewrite_model, then rebuild. In the default additive path these changes are committed to the working branch and flow through PRs (deployed via GitHub Sync on merge); in the parallel-workspace alternative they are committed to the cloned repo and deployed via GitHub Sync; in the in-place alternative they are applied to the existing models.

Before translating any sync, run the scope gate (Step 4-pre) and the approach re-verification (Step 4-verify) below.

#### Step 4-pre: Source-model scope gate

For each in-scope sync, confirm its **source object exists on the target** — i.e. the model (or table) the sync reads from was built on the target warehouse by a completed `dbt_migration` batch (or is otherwise present and populated on target). Resolve the sync's source object from the audit's `warehouse_objects` and check it against the target.

- If the source object **is present** on target → keep the sync in scope.
- If the source object **is not present** (not yet built, or its `dbt_migration` batch is incomplete — e.g. the `de_leasing_engine_promotions` case) → **exclude the sync** and list it under **"Deferred — source model not built on target"** in the runbook, with the missing object named.

Do not silently include a sync whose source object cannot be validated on target. Roll the excluded count up to `deferred_count` in status.md.

#### Step 4-verify: Re-verify the audit's approach tags

**Do not trust the audit's `approach` / `sf_funcs` tags.** In one pilot audit, 4 syncs tagged `repoint` actually contained `RRP :: NUMBER` — a `::` cast the audit missed. Re-scan each in-scope sync's model SQL proactively for non-portable source-dialect constructs before deciding it needs no translation. At minimum, scan for:

- the `::` cast operator
- `FLATTEN`
- `QUALIFY`
- `IFF`
- `NVL`
- `CONVERT_TIMEZONE`
- `:`-style variant path access (e.g. `col:field`)

If any appear on a sync tagged `repoint`, **reclassify it to `rewrite_model`** and log the change: `{ sync_id, sync_name, construct_found, old_approach: repoint, new_approach: rewrite_model }`. Roll the count up to `reclassified_count` in status.md and list the reclassifications in the runbook.

Keep the **reactive downgrade** in the `repoint` bullet below as a backstop — if a `repoint` model still fails to return rows / a non-null primary key on target, downgrade it to `rewrite_model` even if this scan passed.

- **repoint** — model SQL is portable (and survived the Step 4-verify scan); no SQL change. The model resolves against the target-warehouse source. Verify the model SQL returns rows and a non-null primary key on the target; if it fails, downgrade to `rewrite_model` (the reactive backstop).
- **rewrite_model** — translate the model SQL using the platform-pair guide (`wire/platform_pairs/<source>_to_<target>/translation_guide.md`) and feature-tag translations, applying the **drift-aware column translation** in Step 4c before the generic mapping. Test the translated SQL on the target warehouse — row count and primary-key integrity match the source model output. Record a before/after SQL diff in the runbook (noting any drift-adjusted columns). Update via PR on the working branch (additive default / parallel) or `PATCH /api/v1/models/<MODEL_ID>` (in-place).
- **rebuild** — Customer Studio audiences and Journeys are rebuilt against the target-warehouse source: new schema (parent + related models + events) on the target source, recreated audience filters, recreated Journeys, sync destinations re-mapped to the rebuilt audiences. Capture the existing definitions first via the `schemas`, `audiences`, and `journeys` endpoints.

**Every new test sync carries its decoy destination ID only** (Step 4b) — the production destination IDs must be absent from the test syncs until cutover. Under `additive_dedicated_destination` this applies to decoy-mode syncs only: dedicated-mode syncs carry their confirmed dedicated destination id from the start and skip Step 4b. Keep all new syncs disabled until validated (Step 5).

### Step 4b: Decoy destination mapping table

Destinations are reused in place (the existing definitions are not re-created), so safety cannot rely on a "disabled" flag — a single mistaken enable would write to a live downstream system. Use a structural decoy mechanic instead.

**Skipped entirely for dedicated-mode syncs** under `additive_dedicated_destination`: the decoy mechanic exists to protect destinations reused in place, and a dedicated destination is not reused — nothing else writes to it, so there is nothing for a decoy to protect. Dedicated-mode syncs still get a row in the mapping table (it is the per-sync record of `destination_mode` and the Step 2 gate evidence); only the decoy provisioning and decoy-pointing steps are skipped for them. Decoy-mode syncs in a mixed estate go through this step unchanged.

1. **Build the decoy mapping table** — one row per in-scope sync. Generate or consume `migration/reverse_etl_decoy_mapping.csv` (or `_{wave_id}.csv` under `--wave`) with columns:

   ```
   sync_id, sync_name, production_destination_id, production_destination_type,
   decoy_destination_id, decoy_destination_type, destination_mode, notes
   ```

   `destination_mode` is `decoy` (the default, and the only value outside `additive_dedicated_destination`) or `dedicated`. A `dedicated` row leaves both decoy columns blank **by design** (this is not the provisioning flag below), records the Step 2 gate evidence in `notes` (the existence confirmation and the destination-set check result), and its `production_destination_id` is the confirmed dedicated id the sync writes to from authoring.

   The decoy must be the **same destination type** as production — a decoy Google Sheet for a Google Sheets destination, a decoy Salesforce sandbox for a Salesforce destination, and so on. If a decoy of the right type does not yet exist, list it as a `decoy`-mode row with `decoy_destination_id` blank and flag it for the client to provision; do not substitute a different type. The provisioning flag applies to `decoy`-mode rows only.

2. **Point every new decoy-mode test sync at its decoy ID only.** The production destination IDs must be **absent** from those test syncs. A decoy-mode test sync that references a production destination ID is a defect — fail the pre-flight gate (below) rather than ship it.

3. **Require a scoped destination credential** — a service account with write access to the decoy targets only and **no permission** on production destinations. Record which credential each decoy destination uses. Validation (Step 5) and any preview run use this credential, so even an accidental live run can only reach a decoy.

4. **At cutover, reverse the mapping.** PR C (Step 8) swaps each `decoy_destination_id` back to its `production_destination_id` and enables the sync. The mapping table is the source of truth for that swap — every decoy-mode row must round-trip. Dedicated-mode rows have nothing to swap: their syncs carry the real id already.

**Hard pre-flight gates** (also enforced by `specs/utils/migration_preflight.md`):
- **Production destination IDs absent from test syncs** — scan every new decoy-mode test sync's config; if any references a `production_destination_id` from the mapping table, stop and report before generating. For a dedicated-mode sync the gate is instead: its destination id equals the row's confirmed dedicated id **and** appears in no existing sync's destination set (the Step 2 gate, re-checked).
- **Test credential has no grant on production destinations** — confirm the scoped credential cannot write to any production destination. If the grant cannot be confirmed, stop. (Decoy-mode syncs; a dedicated-mode sync's writes can only reach its own dedicated object.)

### Step 4c: Drift-aware column translation

The generic platform-pair mapping assumes a type carries over cleanly — e.g. Snowflake `VARIANT` → BigQuery `JSON`, with `col:field` → `JSON_VALUE(col, '$.field')`. That misfires when a column lands as a different type on the target. Under BigLake Iceberg a `VARIANT` column often lands as plain `STRING`, not `JSON` — applying `JSON_VALUE`/`JSON_QUERY_ARRAY` to it produces wrong results or errors. The pilot is safe by scope, but the estate is not (84 staging + 8 source + 2 raw syncs), so make translation drift-aware rather than assuming.

For each sync about to be translated (`rewrite_model`, and any `repoint` whose model SQL touches a possibly-drifted column):

1. **Resolve the columns the model SQL references** — the set of source columns the sync's model reads, especially those passed through variant/JSON extraction or cast.
2. **Cross-reference the drift manifest** (`mds_variant_columns.csv`). For each referenced column that appears in the manifest, read its `target_landing_type`.
3. **Translate to the actual target type, not the generic mapping.** Where a referenced column is drifted (e.g. `target_landing_type = STRING`), do **not** apply the generic `VARIANT → JSON` / `JSON_VALUE` / `JSON_QUERY_ARRAY` mapping. Translate against the type the column actually lands as — for a `STRING` landing, treat it as text (string functions, explicit `SAFE.PARSE_JSON(...)` only if the string genuinely holds JSON and downstream needs it), matching what the target schema exposes.
4. **Mirror any dbt_migration reconciliation.** If the referenced model was already migrated by dbt_migration, find its `*.diff.md` and reuse the type handling recorded there rather than re-deriving — the two must agree.
5. **Record per model whether any column was drift-adjusted** — list the adjusted columns and the type used, in the sync's runbook section and its SQL diff. Set the per-model `drift_adjusted` flag accordingly (rolled up to `drift_adjusted_count` in status.md).

If the drift manifest is absent, note that in the runbook and fall back to the generic mapping — but flag every `VARIANT`/variant-path translation as `medium` confidence and call out that drift was not checked.

### Step 5: Validate by model output and preview — decoy destinations only

Do **not** point any test sync at a production destination to validate. Activating a sync writes to whatever destination it carries; live downstream systems (Salesforce, HubSpot, Iterable, Braze, ad platforms, Google Sheets) must never be the target during validation. Test syncs carry **decoy destination IDs only**, written through the scoped decoy credential, and are validated via Hightouch's sync previews and record-level inspection — this confirms what *would* be written without touching production, and gives higher confidence than comparing SQL output alone.

Validate against a **frozen source baseline**, not moving production — the source warehouse keeps ingesting and rebuilding, so a moving comparison surfaces timing differences, not translation differences. Use the baseline defined in the migration strategy's equivalency section (e.g. a zero-copy snapshot of the source models at a fixed cutoff); align any target-side load to the same cutoff. Per in-scope model:

1. **Model output** — compare row count, primary-key uniqueness, aggregates, and representative samples between the target model and the frozen source baseline.
2. **Audience sizes** — where Customer Studio is in scope, compare audience membership and segment counts against the baseline (default tolerance ±2%).
3. **Sync preview** — run the sync in preview / dry-run; the sync carries its decoy destination ID and the scoped decoy credential, so any actual write lands on the decoy, never production. Confirm the planned record count and field-level payload match expectation. No live run against a production destination. A dedicated-mode sync has no decoy: its preview runs against the confirmed dedicated destination, which no existing sync writes to, so an accidental write can only reach the tenant's own dedicated object.

### Step 6: Review sync-level transformation logic

A matching model output does not prove a matching sync — transformation logic lives on the sync as well as in the model. For each sync, review and test: field mappings, computed fields, sync filters, match rules and identity resolution, and audience inclusion/exclusion logic. Record the review per sync in the runbook; differences here are a common source of silent divergence even when model output is identical.

### Step 7: Lightning engine provisioning

For all Lightning syncs, confirm the target warehouse has the required schemas before any sync is enabled:

```sql
-- Run on target warehouse
CREATE SCHEMA IF NOT EXISTS hightouch_planner;
CREATE SCHEMA IF NOT EXISTS hightouch_audit;

-- Grant the Hightouch service account access
GRANT USAGE ON SCHEMA hightouch_planner TO ROLE hightouch_role;
GRANT CREATE TABLE ON SCHEMA hightouch_planner TO ROLE hightouch_role;
GRANT USAGE ON SCHEMA hightouch_audit TO ROLE hightouch_role;
GRANT CREATE TABLE ON SCHEMA hightouch_audit TO ROLE hightouch_role;
```

Note: Hightouch creates the actual tables in these schemas on the first sync run. The grant only needs to be in place before that first run.

### Step 8: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md` — or `migration/reverse_etl_migration_runbook_{wave_id}.md` when run with `--wave`.

Structure:
1. Topology decision (additive PR-gated repo — default — vs additive to dedicated never-shared destinations vs parallel workspace vs in-place API re-point) and the rationale; for `additive_dedicated_destination`, the per-destination gate evidence (exists on the target side; appears in no existing sync's destination set)
2. Build steps for the chosen topology (default: branch existing repo, add target source, author decoy test syncs, open PR A — or the dedicated-destination variant, or parallel-workspace build with destination re-auth, or in-place re-point prep)
3. Pre-flight checklist (target warehouse ready, dbt batches complete, source baseline frozen, Lightning schemas provisioned, decoy mapping table + scoped credential in place, production destination IDs absent from decoy-mode test syncs) — per `specs/utils/migration_preflight.md`
4. Per-sync model translation — repoint / rewrite_model (with SQL diff, drift adjustments noted) / rebuild (schema mapping + steps), with reclassifications from the approach re-verification (Step 4-verify) and exclusions from the scope gate (Step 4-pre)
5. Destination mapping table (production ID → decoy ID per decoy-mode sync; `destination_mode` and gate evidence per dedicated-mode sync) and scoped credential definition
6. Validation procedure — model-output comparison vs frozen baseline, audience-size comparison, sync preview with destinations set to decoy IDs (or the confirmed dedicated id for dedicated-mode syncs)
7. Sync-level transformation review — per sync: field mappings, computed fields, filters, match/identity rules, audience include/exclude
8. **Sign-off and cutover sequence (two client-merged PRs)**: open PR A (add target-warehouse test syncs with decoy IDs) → client merges PR A → translate/validate model outputs → validate audience sizes + sync previews → review sync-level logic → business sign-off → prepare the cutover PRs:
   - **PR B (disable source)** — disables every sync whose origin is the source warehouse.
   - **PR C (enable target)** — swaps the decoy destination IDs back to production destination IDs on the new target-warehouse syncs and enables them.
   The client merges **PR B and PR C together in one cutover window**. → monitor initial runs → decommission the source-warehouse syncs (a later PR) once confidence is established.
   **Dedicated-mode syncs collapse to one client-merged PR**: a single cutover PR adds the new target-warehouse syncs — pointed at their confirmed dedicated destination ids, still authored paused per the twin rules — and disables the old source-warehouse syncs together. Enabling the new syncs stays the client's action at merge. The three-PR A/B/C sequence continues to apply to decoy-mode syncs in a mixed estate.
   (Parallel-workspace / in-place alternatives keep their own enable sequences, untouched.)
9. Rollback procedures for the chosen topology and approach types: **additive (default)** — re-merge a revert of PR C (disable target syncs / restore decoy IDs) and revert PR B (re-enable source syncs), by PR; **dedicated** — revert the single cutover PR (re-enables the old source-warehouse syncs, removes the new dedicated-destination syncs); **parallel** — don't enable / disable new-workspace syncs and re-enable source workspace; **in-place** — re-apply original `sourceId`.

The existing source-warehouse syncs stay active and untouched as the rollback path until cutover — never disable them outside PR B (or, for dedicated-mode syncs, the single cutover PR), and never before PR C is ready to merge alongside it.

### Step 9: Update status

```yaml
artifacts:
  reverse_etl_migration:
    generate: complete
    file: migration/reverse_etl_migration_runbook.md
    generated_date: "{{TODAY}}"
    topology: additive_repo | additive_dedicated_destination | parallel_workspace | in_place_repoint
    repoint_count: N
    rewrite_model_count: N
    rebuild_count: N
    reclassified_count: N         # syncs moved repoint → rewrite_model by Step 4-verify
    deferred_count: N             # syncs excluded by the Step 4-pre scope gate
    dedicated_destination_count: N   # destination_mode: dedicated syncs (additive_dedicated_destination only)
    dedicated_fallback_count: N      # syncs refused by the Step 2 gate, fell back to the decoy path
    drift_adjusted_count: N       # syncs with at least one drift-adjusted column (Step 4c)
    decoy_mapping_file: migration/reverse_etl_decoy_mapping.csv
    wave: "B01"                   # set only when run with --wave; the wave id just processed
    waves_complete: ["B01"]       # set only when run with --wave; accumulates across runs
```

### Step 10: Output next command

```
/wire:reverse-etl-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md` (`_{wave_id}` suffix when run with `--wave`)
- `.wire/releases/$ARGUMENTS/migration/reverse_etl_decoy_mapping.csv` — production → decoy destination ID mapping, one row per in-scope sync (`_{wave_id}` suffix when run with `--wave`)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact_id, `Reverse ETL Migration` as artifact_name, and the `file` value from `artifacts.reverse_etl_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_migration` as artifact, `generate` as action.

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

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
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
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
