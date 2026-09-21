---
description: Usage-ranked inventory, director rulings (parity or redesign, drop list, PDT disposition, permissions, topic design), model and content batches, register bootstrap
argument-hint: <release-folder>
---

# Usage-ranked inventory, director rulings (parity or redesign, drop list, PDT disposition, permissions, topic design), model and content batches, register bootstrap

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
    'command': 'bi-migration-plan-generate',
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
artifact: bi_migration_plan
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: document
    path: "migration/bi_migration_plan.md"
    description: "Usage-ranked inventory, the director's rulings, PDT disposition, permission map, topic architecture, parallel-run window and batches"
  - type: report
    path: "migration/bi_migration_batches.csv"
    description: "One row per in-scope object with its batch, kind, usage rank, ruling and batch dependency"
  - type: report
    path: "migration/migration_register.csv"
    description: "Register bootstrapped with one pending row per in-scope BI object"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Build the Looker to Omni migration plan: rank content by usage, capture the director's rulings, set PDT disposition and permission mapping, cut model and content batches, bootstrap the register"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding. The gate resolves this command's preconditions from `release-types/bi_migration.yaml`: `looker_audit` review approved (blocking), `business_rules` review approved (advisory), `omni_audit` review approved (advisory). An advisory gate that is unmet asks for a skip reason, or reads one already recorded as a ruling in `decisions.md`, and continues.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: bi_migration_plan` and `artifact_file_path: migration/bi_migration_plan.md` before proceeding.

---

# BI Migration Plan: Generate

## Purpose

Turns the approved Looker audit into a plan the rest of the release executes: which content moves, in what order, under what ruling, and what the Omni model will look like. It replaces three warehouse-migration artifacts (`migration_inventory`, `migration_strategy`, `migration_batching`) with one, because a BI migration has fewer object types and the decisions belong together.

Five things happen here:

1. **Rank by usage.** Dashboards and Looks are ranked by `views_90d`. The plan records the set that carries 80% of views (the Omni migration guide's observation: 20% of content gets 80% of use) and the set with no views in the stale window.
2. **Capture rulings.** The release director decides, per dashboard tier, parity or redesign; what to drop; what happens to each PDT; how Looker groups and user attributes map to Omni; the topic architecture; the parallel-run window; the parity scope. A ruling that has not been made is written as a parked decision, never guessed.
3. **Cut batches.** Model batches follow explore dependency order (a topic's views before the topic). Content batches follow usage rank, highest first. A content batch depends on the model batch that carries every explore its dashboards reference.
4. **Bootstrap the register.** One `pending` row per in-scope object in `migration/migration_register.csv`, so every downstream command has a row to advance.
5. **Write the plan** as one document plus the batches CSV.

## Prerequisites

- `looker_audit review: approved`
- `business_rules review: approved` if the business rules phase was run (advisory: skipping is allowed with a recorded reason)
- `omni_audit review: approved` if the target Omni instance already holds content (advisory)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/omni_audit.md` (if present: existing Omni topics and content to reuse or avoid colliding with)
- `.wire/releases/$ARGUMENTS/artifacts/business_rules.yaml` (if present: agreed metric definitions the Omni measures must implement)
- `.wire/releases/$ARGUMENTS/decisions.md` (rulings already recorded)
- `.wire/releases/$ARGUMENTS/status.md` (`bi_migration.stale_after_days`, `bi_migration.parallel_run_days`, `bi_migration.parity_scope`)
- `wire/bi_pairs/looker_to_omni/translation_guide.md` and `content_mapping.md`

## Workflow

### Step 1: Load the audit and existing rulings

Read both catalogs and the audit report. Read `decisions.md` and collect every ruling whose `Applies to:` line names `bi_migration_plan` or one of the ruling kinds in Step 3. Read `bi_migration.stale_after_days` (default 180) and `bi_migration.parity_scope` (default `prioritised`) from `status.md`.

### Step 2: Rank content by usage

For every `dashboard` and `look` row:

- Sort by `views_90d` descending. Assign `usage_rank` (1 = most viewed). Rows with `views_90d: unknown` sort last and carry `usage_rank: unknown`.
- Compute the cumulative share of views. Mark the smallest set of rows that reaches 80% of total views as **tier 1**. The remainder with any views in the window is **tier 2**. Rows with zero views and `last_viewed` older than `stale_after_days` are **stale**.
- Record in the plan: tier 1 count and share, tier 2 count, stale count, unknown count.

If `usage_source: unavailable` in `status.md`, every row is `usage_rank: unknown`, no tiers can be computed, and the plan records a parked decision: "Usage is unavailable. Rank by hand, or accept all content as tier 1."

### Step 3: Capture the director's rulings

Each ruling below is read from `decisions.md` if present. If absent, write a `parked_decisions` entry in `status.md` (kind `ruling`, artifact `bi_migration_plan`, the question as worded here) and record `ruling: parked` in the plan. Do not invent a default for any of them except where a default is stated.

| Ruling | Question | Default |
|---|---|---|
| Parity or redesign, per tier | "Tier 1: rebuild each dashboard as-is in Omni (parity), or redesign against the Omni model? Tier 2: same question." | none |
| Drop list | "Drop the stale set (N dashboards, M Looks, no views in {{stale_after_days}} days)? Any exceptions?" | none |
| PDT disposition | For each PDT in the redesign register: "Move this PDT's logic into a dbt model, rebuild it as an Omni query view, or drop it?" | none |
| Permission mapping | "Map these Looker groups and user attributes to Omni groups, user attributes and access grants as listed?" (the plan proposes a one-to-one map; the director confirms or amends) | proposed one-to-one map, pending confirmation |
| Topic architecture | "One Omni topic per Looker explore, or a schema, shared and workbook layering?" | one topic per explore |
| Parallel-run window | "Run Looker and Omni side by side for {{parallel_run_days}} days?" | `bi_migration.parallel_run_days` |
| Parity scope | "Compare every tile, or only tier 1 dashboards' tiles?" | `bi_migration.parity_scope` |

A dashboard the director rules `redesign` still gets a register row and a content batch; its tiles are built against the redesigned topic rather than mapped field by field, and `bi_equivalency` compares only the measures the director names as the redesign's acceptance set.

### Step 4: Decide the model scope

The in-scope model is every view and explore referenced by any dashboard or Look that is not dropped, plus every view those explores join. A view referenced by nothing in scope is **out of scope** and listed under "Model not carried" with the reason `no in-scope content references it`. Fields inside an in-scope view are all carried unless the director rules otherwise; hidden fields are carried hidden.

Every `redesign` model row in scope gets a disposition here: `redesign in Omni` (rebuild by hand on the branch), `drop` (no content needs it), or `defer` (carried as a `needs_human` item into the model batch). PDTs take the ruling from Step 3.

### Step 5: Cut batches

**Model batches** (`batch_kind: model`): group in-scope explores by shared views. Order batches so that a batch's views are all emitted before any topic that uses them; a view shared by several explores goes in the earliest batch that needs it. Target 5 to 15 views per batch. Name batches `b01`, `b02`, ...

**Content batches** (`batch_kind: content`): tier 1 dashboards first, ordered by `usage_rank`, then tier 2, then Looks. Target 5 to 10 dashboards per batch. Each content batch's `depends_on_batch` is the last model batch that carries any explore in its dashboards' `explore_refs`. Schedules and alerts join the batch of the dashboard they belong to. Groups form one `permissions` batch (`batch_kind: model`, first in order) so access grants exist before content is published.

Write `migration/bi_migration_batches.csv` with columns, in this order: `batch_id`, `batch_kind` (`model` | `content`), `object_type`, `object_id`, `object_name`, `explore_or_topic`, `usage_rank`, `ruling` (`parity` | `redesign` | `drop`), `depends_on_batch`. Dropped objects appear with `batch_id` empty and `ruling: drop`, so the drop list is in the same file as the plan.

### Step 6: Bootstrap the register

If `migration/migration_register.csv` does not exist, create it from `TEMPLATES/migration/migration_register.csv`. Insert one row per in-scope object (not dropped) with:

| Column | Value for BI rows |
|---|---|
| `model` | `view:<name>`, `topic:<explore>`, `dashboard:<id>`, `tile:<dashboard_id>/<element_id>`, `look:<id>`, `schedule:<id>`, `group:<name>` |
| `object_type` | `view` | `topic` | `dashboard` | `tile` | `look` | `schedule` | `group` |
| `source_path` | the `lkml_file` for model rows; the Looker URL path for content rows |
| `source_layer` | `looker_model` or `looker_content` |
| `bq_target` | empty until `omni_model` or `omni_content` writes the Omni reference (model id, branch and file, or document identifier). BI rows are exempt from the three-segment physical-path rule, like `metabase_card` rows |
| `state` | `pending` |
| every other column | `null` |

Every `view` and `topic` row carries `last_migrated_commit` = `looker_audit.lookml_commit` (the LookML commit the audit classified from; `omni-model-generate` advances it when the batch is emitted), and every `dashboard` and `look` row carries `source_updated_at` from the content catalog. These are the baselines `migration-drift-generate` compares against; a row without them cannot be drift-checked and is reported as `not_applicable`.

Rows that already exist are left as they are. Record `register_rows` in `status.md`.

### Step 6b: Write the baseline and the evidence file

`migration/baseline.yaml` records what every later verdict is measured against. A verdict that does not name a baseline is not evidence.

```yaml
baseline_id: b001                       # increments on every re-baseline
written_at: "{{TODAY}}"
written_by: <consultant>
lookml_commit: <migration_sources.lookml.last_commit>
looker_deployed_revision: <the production LookML commit Looker reports for the project, when it differs from lookml_commit>
looker_base_url: <bi_migration.looker_base_url>
omni_model_id: <bi_migration.omni_model_id>
omni_branch: <bi_migration.omni_branch>
warehouse: <bi_migration.warehouse>
converter_version: <from scripts/lookml_to_omni.py, recorded in conversion_summary.json>
pair_ruleset_sha: <SHA-256 over bi_pairs/looker_to_omni/*.md plus the engagement's overrides directory>
comparator_version: <from scripts/bi_parity.py>
parity_as_of: <bi_migration.parity_as_of>   # pinned here; bi-equivalency-validate refuses to run unpinned
```

Set `bi_migration.parity_as_of` now if it is null: the end of the last complete day before the first model batch, in the warehouse's timezone. Moving it later is a re-baseline (new `baseline_id`, every standing verdict invalidated), which is the point: a parity result at one instant is not evidence at another.

`migration/parity/evidence.csv` starts here with one row per `tile` and `view` register row. Compute `evidence_fingerprint` with `python3 <plugin-root>/scripts/bi_evidence.py fingerprint --components <json>` from the seven components; at bootstrap only `source_definition` (lookml_commit plus the object's `.lkml` file hash), `dependencies` (the object's closure from `audit/dependencies.jsonl`), `policy_context` (hash of the access filters, grants and user attributes the object is under), `data_context` (`parity_as_of`) and `adapters` (converter, pair ruleset and comparator versions) are known; `target_definition` and `test_contract` are the literal `absent` until `omni-model-generate` and `bi-equivalency-validate` fill them. `stale_kinds` is empty. `migration-drift-generate` is the only command that writes `stale_kinds`; `bi-equivalency-validate` is the only one that clears it.

### Step 7: Write the plan

**Output location**: `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`

Sections:
- Summary: in scope by object type, dropped by object type, batches by kind, rulings made and parked
- Usage ranking: the tier table and the 80% cut
- Rulings: one subsection per ruling in Step 3, with the decision, who made it and when (from `decisions.md`), or `parked`
- Model scope: carried views and explores per batch; model not carried, with reasons; redesign dispositions; PDT dispositions
- Permission map: Looker group or user attribute to Omni group, user attribute or access grant
- Topic architecture: the chosen design and the resulting topic list
- Batches: the batch table with dependencies, and the order they run in
- Parallel run and parity: window, `parity_scope`, the tiles that will be compared, the pinned as-of once set
- Reference key: every code used (batch ids, ruling ids) with its meaning and defining document, per `specs/utils/reference_legibility.md`

### Step 8: Update status

```yaml
artifacts:
  bi_migration_plan:
    generate: complete
    file: migration/bi_migration_plan.md
    data_file: migration/bi_migration_batches.csv
    generated_date: "{{TODAY}}"
    batch_count: N
    objects_in_scope: N
    objects_dropped: N
    register_rows: N
    rulings_parked: N
    generated_files:
      - migration/bi_migration_plan.md
      - migration/bi_migration_batches.csv
      - migration/migration_register.csv
```

### Step 9: Output summary

Print the scope totals, the batch count by kind, the rulings made and parked (with their questions), and the next command:

```
/wire:bi-migration-plan-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv`
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (created or extended)
- `.wire/releases/$ARGUMENTS/migration/baseline.yaml`
- `.wire/releases/$ARGUMENTS/migration/parity/evidence.csv` (created)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact_id, `BI Migration Plan` as artifact_name, and the `file` value from `artifacts.bi_migration_plan` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bi_migration_plan` as artifact, `generate` as action.

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
