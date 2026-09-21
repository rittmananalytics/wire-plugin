---
description: Relocate already-translated dbt models into a post-migration tenant carve-out instead of re-translating them
argument-hint: <release-folder> [--wave id \
---

# Relocate already-translated dbt models into a post-migration tenant carve-out instead of re-translating them

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
    'command': 'dbt-carveout-relocate-generate',
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
artifact: dbt_carveout_relocate
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
  - artifact: target_setup
    action: review
    outcome: approved
  - artifact: region_tagging
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Relocate already-translated, already-correct dbt models into a new carve-out dbt project instead of re-translating them, injecting a tenant row filter where a model is shared
argument-hint: <release-folder> [--wave id | --batch N | --select selector] --source-dbt-project-path <path> --target-dbt-project-path <path> --target-project <name> [--target-dataset <name>] [--config <path>]

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_carveout_relocate` and `artifact_file_path: migration/dbt_carveout_relocate_manifest.md` before proceeding.

---

## Data Safety — Read Before Proceeding

This command never re-translates and never touches the original source platform. Before relocating any model, output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source dbt project ([--source-dbt-project-path]): READ ONLY.
  This command reads already-translated, already-correct target-dialect SQL
  from here. It is never written to, and no source-platform MCP is touched.

Target writes go to: [--target-dbt-project-path], compiled against
  [--target-project]/[--target-dataset or default schema].
```

If any generated step would write to `--source-dbt-project-path`, stop immediately and report the conflict before proceeding.

---

# dbt Carveout Relocate — Generate

## Purpose

Relocates already-translated, already-correct target-dialect dbt SQL for a tenant carve-out that is scoped **after** its parent platform migration has already landed — the carve-out does not touch the original source platform at all, so re-running `dbt-migration-generate`'s translate-and-equivalency loop against it would be pointless work re-deriving SQL that is already correct. This command is `dbt_migration`'s relocation-only counterpart, in the same relationship `bulk_copy_migration` (copy data instead of re-ingesting) has to `ingestion_migration` (re-ingest from source).

For each in-scope model:
- **`bucket: confident-region`** (tenant-exclusive) — the `.sql` file and its companion schema/properties YAML are copied unchanged.
- **`bucket: shared-row-level`** (serves every tenant) — the file is copied, then the model's filter, resolved per model from the tenant predicate registry, is injected at the point the resolution ladder identifies (Step 1.8). Where the ladder cannot resolve the model, the file is copied unmodified and flagged `predicate_injection: manual_review_required` rather than guessed.

From v3.11.3 the ladder does the work that used to land in the reviewer's queue as "ambiguous": it strips comments before scanning, builds the wave's `ref()` graph up front, parenthesizes unconditionally, restructures a `WHERE` trapped inside a Jinja conditional, resolves SELECT-list aliases, probes the row distribution where live evidence is what decides, and resolves models with no tenant column of their own by inheritance from a covered upstream. `manual_review_required` narrows to what is genuinely novel.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`), and only after the carve-out's `region_tagging` output has been through human adjudication — it consumes that adjudication, it never re-derives it.

## Prerequisites

- `migration.scope == tenant_carveout` and `migration.tenant_predicate` is set
- `region_tagging review: approved`
- `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` exists (written by `region-tagging-review`)
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` exists (seeded by `region-tagging-generate`; `/wire:upgrade` adds it to a pre-v3.11.3 release)
- `--target-dbt-project-path` is an already-initialized dbt project (`dbt_project.yml` and a working profile exist) pointed at the carve-out's target warehouse — this command relocates models into it, it does not scaffold the project itself

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — scope resolution. Identical grammar, normalisation, and mutual-exclusivity rules to `dbt-migration-generate`'s Steps 1/1a/1w (same abort messages, substituting this command's name) — see that spec for the full algorithm. Resolved against the **source** dbt project (`--source-dbt-project-path`), since that is where the audit/batching/manifest data this grammar reads was produced. No flag — abort: `[wire] One of --wave, --batch, or --select is required to determine relocation scope.` (unlike `dbt-migration-generate`, there is no "next incomplete batch" default here, since relocation scope is always driven by an explicit wave/batch/selector tied to the adjudicated carve-out plan.)
- `--source-dbt-project-path <path>` — **required.** The dbt project holding the already-translated, already-correct target-dialect SQL (typically the parent platform-migration release's dbt repo). Never written to.
- `--target-dbt-project-path <path>` — **required.** The dbt project this command writes into.
- `--target-project <name>` — **required.** The target warehouse project/account this run's models should compile against (the caller runs this command once per environment — playground, then production — this flag doesn't distinguish between them).
- `--target-dataset <name>` — optional target dataset/schema override, when the target project's default isn't the intended destination.
- `--config <path>` — load a per-run config overlay file; see **Config overlay** below.

### Config overlay (`--config`)

`--config <path>` points at a small YAML or JSON file that can set `dbt_carveout_relocate.source_dbt_project_path`, `dbt_carveout_relocate.target_dbt_project_path`, `dbt_carveout_relocate.target_project`, `dbt_carveout_relocate.target_dataset`, and `migration.tenant_predicate`, read once at Step 0 and held in memory for this invocation only — never written back to status.md. Where a discrete CLI flag (`--source-dbt-project-path`, `--target-dbt-project-path`, `--target-project`, `--target-dataset`) is also supplied, the discrete flag wins for that key. This exists for the repeated-invocation case the worked example below shows — running the same source/target pair across several waves — so the operator sets the shared fields once instead of retyping them on every call.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` — the adjudicated region-tagging output (see `region-tagging-review`); columns `item_id,item_type,source_audit,bucket,signal,confidence_score,adjudicated_ruling,adjudication_note`
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` — per-item resolution mechanisms; read at Step 1.6, written back at Step 2c (`specs/utils/tenant_predicate_registry.md`)
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — model catalog (used by `--batch` resolution)
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — authoritative execution schedule (used by `--wave` resolution)
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`
- Source dbt project at `--source-dbt-project-path` (or the `--config` overlay equivalent) — model `.sql` and companion schema/properties YAML
- **`--config <path>` overlay (optional)** — see **Config overlay** above

## Workflow

### Step 0: Confirm prerequisites and load config overlay

1. Confirm `migration.scope == tenant_carveout`. If it is `full_migration` or absent, stop: `[wire] dbt-carveout-relocate runs in tenant carve-out scope only.`
2. Confirm `migration.tenant_predicate` is set (unless overridden by `--config`, see below). If null everywhere, stop: `[wire] migration.tenant_predicate is required to inject the shared-row-level filter.`
3. Confirm `region_tagging review: approved` in status.md. If not, stop: `[wire] region-tagging-review has not been approved yet. This command consumes adjudicated region tags — it does not run ahead of that gate.`
4. Confirm `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` exists. If not, stop: `[wire] No region_tags_adjudicated.csv found. Run /wire:region-tagging-review $ARGUMENTS first.`
5. If `--config <path>` was supplied: read and parse the file (YAML or JSON by extension/content-sniff). If it does not exist or fails to parse, abort: `[wire] --config file <path> not found or invalid. Aborting.` Hold the parsed overlay in memory; every field below checks the overlay first, then the discrete CLI flag (which wins over the overlay per-key), then status.md for `migration.tenant_predicate`.
6. Confirm `--target-dbt-project-path/dbt_project.yml` exists. If not, stop: `[wire] No dbt_project.yml found at <path>. Initialize the target dbt project (dbt init, or clone the project skeleton) before relocating models into it.`

### Step 1: Determine scope

Resolve the source dbt project via `specs/utils/dbt_manifest_parse.md` Steps 1–2, pointed at `--source-dbt-project-path`. Then resolve the model set exactly as `dbt-migration-generate` Steps 1/1a/1w describe for `--select`/`--batch`/`--wave` respectively, reading `dbt_audit.csv` and `migration/migration_batching.csv` from `$ARGUMENTS`. Print the same mandatory resolved-list preview those steps require before proceeding.

If neither `--wave`, `--batch`, nor `--select` was supplied, abort per the **Flags** section above.

### Step 1.5: Filter to the adjudicated carve-in set

Load `migration/region_tags_adjudicated.csv`. Filter to rows where `item_type == "dbt_model"` **and** `adjudicated_ruling == "carve_in"`. Intersect this set with Step 1's resolved model list, matching `item_id` against the model name.

- A Step 1 model with no matching adjudicated row at all is **not in scope for this command** — print it as skipped (`[wire] <model>: no carve_in adjudication — not relocated by this run.`) rather than treating it as an error; the wave/batch may legitimately mix carve-in and non-carve-in models.
- If the intersection is empty, stop cleanly: `[wire] No carve_in dbt_model rows in this scope. Nothing to relocate.`
- Print the resolved relocation set (model name, bucket) before proceeding, mirroring the mandatory preview pattern used elsewhere.

### Step 1.6: Load the tenant predicate registry (v3.11.3)

Read `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` (seeded by `region-tagging-generate`, rulings added by `region-tagging-review`). The contract, the five mechanisms, and the read order are in `specs/utils/tenant_predicate_registry.md`.

If the file does not exist, stop: `[wire] No tenant_predicate_registry.csv found. Re-run /wire:region-tagging-generate $ARGUMENTS to seed it (this command resolves per-model mechanisms, it does not invent them).` A carve-out release created before v3.11.3 gets the registry from `/wire:upgrade`.

The registry, not `migration.tenant_predicate`, is what this command injects from. The global string remains only as the seed's default row predicate.

### Step 1.7: Build the wave dependency graph (v3.11.3)

Build the `ref()`/`source()` dependency graph over the **entire** Step 1.5 set before touching any single model, from the source project's manifest (already parsed in Step 1). Record for each in-scope model its direct upstream nodes, and mark each node `covered` when either its registry row carries a mechanism other than `unresolved`, or its adjudicated bucket is `confident-region`.

This runs before the per-model work and not after it, which is the opposite of the intuitive order. Most models that carry no tenant column at all are scoped by an upstream that does, and most branches of a top-level set operation read from models in the same wave. Neither can be classified without knowing whether its upstream is already resolved, so resolving them one at a time means re-deriving the same graph once per model. One engagement's wave had 128 models needing predicate review, of which 102 carried no tenant column and 17 were top-level `UNION ALL`s — a single traversal, not 119 judgment calls. Triaging the no-tenant-column pile last, which the per-model ordering encourages, is the expensive way round.

### Step 1.8: Resolve each shared-row-level model's filter (v3.11.3)

For every `shared-row-level` model, classify its SQL shape and then walk the ladder. Each rung either resolves the model — writing its mechanism and provenance into the registry (Step 2c) — or hands it to the next. Only a model that falls off the end is `manual_review_required`, and that is what the flag should mean: genuinely novel, not merely unexamined.

**Rung 0 — strip comments before scanning.** Remove `/* ... */` blocks and `-- ...` line remainders from a working copy of the SQL before looking for tenant-column references, injection points, or set operations. A tenant column name inside a comment is not a column reference. This is a scanner correctness fix, not a heuristic: without it a commented-out `country` filter reads as a live one and the model is confidently mis-shaped. Injection still writes into the original text, comments intact.

**Grain classification — SCD-shaped models take the entity-grain form (#219).** Before any injection rung applies, classify the model against the SCD-shape signals in `specs/utils/tenant_predicate_registry.md` (snapshot materialisation, `dbt_valid_from`/`dbt_valid_to`, a `valid_from`+`valid_to` pair, an `is_current` flag). An SCD/history-shaped model takes the **entity-grain** form of its registry filter: `<entity_key> IN (SELECT DISTINCT <entity_key> FROM <relation> WHERE <expression>)`, never the raw row expression. A row-grain predicate on a history table truncates an entity's version history with no NULL to signal it, and the two forms are row-identical on live data whenever every version happens to carry the tenant value, so nothing downstream catches the swap. The entity key resolves from the model's `unique_key`/snapshot config or the registry row's `notes`; where no entity key resolves, the model is `manual_review_required` with reason `scd_entity_key_unresolved`. Record `grain: entity | row` per injected model in the manifest.

**Rung 1 — always parenthesize the existing `WHERE` body.** When appending the filter to an existing `WHERE`, wrap the original body in parentheses first: `WHERE (<original body>) AND <filter>`. Do this unconditionally, not only when the original contains a top-level `OR`. Parenthesizing is precedence-safe either way, so the unconditional form is strictly safer than detecting the `OR` case, and it removes depth-0 `OR` as a category of failure rather than adding a special case to detect. Record `resolved_by` unchanged (the registry mechanism is what resolved it); note the parenthesization in the manifest.

**Rung 2 — restructure a `WHERE` inside a Jinja conditional.** When the outermost `WHERE` sits inside a Jinja conditional (`{% if is_incremental() %} WHERE ... {% endif %}`), the tenant filter must not inherit that condition — it applies on every run. Emit an unconditional top-level `WHERE <filter>` and re-nest the original conditional body as an `AND (...)` inside its own `{% if %}`:

```sql
-- before
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

-- after
WHERE country = 'DE'
{% if is_incremental() %}
  AND (updated_at > (SELECT MAX(updated_at) FROM {{ this }}))
{% endif %}
```

The shape was already detected before v3.11.3; only the restructure was missing.

**Rung 3 — resolve a SELECT-list alias.** If the registry row's `tenant_column` is not a real column at the target `WHERE`'s query depth but a SELECT-list alias defined at that same depth, the `WHERE` cannot reference it (BigQuery does not resolve a flat query's own select-list alias in its `WHERE`). Substitute the alias's defining expression into the filter and inject that. Inside a CTE the alias is legitimately visible to an outer query, so this rung applies only when the alias and the `WHERE` share a depth. Write the substituted expression to the registry with `mechanism: derived_expr`, `resolved_by: alias_resolution`, and the original alias in `notes`.

**Rung 4 — probe the row distribution.** Two shapes need live evidence rather than more parsing, and both take the same query:

- **Two plausible tenant columns in scope** and the registry row does not say which. Run a row-count-by-each-candidate-column query over the source relation and compare the distributions.
- **A hardcoded literal where a per-row signal exists elsewhere** — the model pins a market as a constant, but another column carries the tenant per row (an account id, a naming convention in a key).

Run the count, compare it against registry rows already resolved for the same column or the same upstream, and emit a **proposed** disposition with the query and its result as provenance: `mechanism` set, `resolved_by: row_distribution_probe`, `confidence: medium`, `verified_date` today. A proposal is written to the registry and listed in the manifest for the reviewer; it is not treated as a ruling, and `dbt-carveout-relocate-review` is where it becomes one. The same probe belongs in the reviewer's hands for the reverse case too: it has reclassified items from `exclude` to `carve_in` on live evidence, and an object-level adjudication that the row distribution contradicts is worth re-opening.

**Rung 5 — resolve by upstream inheritance.** Using Step 1.7's graph:

- **No tenant column present at all.** Walk each upstream path to the nearest `covered` node. If **every** path reaches one, the model needs no filter of its own — its rows are already tenant-only. Write `mechanism: inherited`, `resolved_by: upstream_inheritance`, `resolving_node` set to the nearest covering node (naming one per path in `notes` where there are several), and record `predicate_injection: not_applicable_inherited`. If any path reaches an `unresolved` node or a source outside the wave, the model stays unresolved — and the reason names the uncovered upstream, so fixing that one model resolves this one on the next run.
- **Top-level `UNION`/`UNION ALL`/`INTERSECT`/`EXCEPT`.** Classify each branch separately before deciding anything about the model. A branch reading from a `covered` upstream needs no injection of its own; a branch that already yields no tenant rows (its upstream is wholly outside the carve-out) needs none either, and that fact is a graph lookup, not a data read. Inject only into the branches that need it, and only when every branch is resolved one way or the other. If any branch is unresolved, the model is `manual_review_required` and the reason names **that branch**, not the whole model.

**Off the end — `manual_review_required`.** Multiple depth-0 `SELECT`s that are not a set operation, and any shape none of the rungs above fit. Record the shape, the rung that last examined it, and the specific reason. This list is the reviewer's queue.

**Re-run behaviour.** The ladder is idempotent and monotonic: re-running after an upstream model gains a mechanism resolves its descendants by Rung 5 without anyone re-triaging them. Rows whose `resolved_by` is `adjudication` or `manual` are read and never overwritten (`specs/utils/tenant_predicate_registry.md`).

Tests mirror this ladder (`wire/tests/platform_migration/validate_carveout_predicate_resolution.py`).

### Step 1.8b: Tenant predicate semantics check (#219)

For every model the ladder resolved from a **derived** registry row (a row whose `resolved_by` is anything other than `adjudication` or `manual`, with a `tenant_column`), run and record the semantics check defined in `specs/utils/tenant_predicate_registry.md` before injecting: measure the predicate column's value distribution on the source relation (`distinct_values`, `tenant_share`) and classify it under that contract's plausibility rule.

- **`plausible`** — proceed to injection. Record the measured figures and the verdict in the registry row (`provenance`/`notes`, `verified_date`; written back at Step 2c) and in the manifest.
- **`implausible_zero_share` / `implausible_dispersed`** — do **not** inject. Route the model to `manual_review_required` with reason `predicate_semantics_implausible`, recording the distribution figures as the evidence. A column named like a tenant column can carry something else entirely (one engagement's was the install geography of a global app: 231 distinct ISO codes, tenant share zero), and injecting it silently changes the measure's meaning while every gate stays green.

The check runs once per derived row and re-runs when the row's `expression` or `tenant_column` changes. Rung 4's row-distribution probe already produces the same measurement; where a probe ran, reuse its result rather than querying twice.

### Step 1.9: Parent verdict gate (#180)

A relocated model inherits the parent release's proof that its SQL is correct — so read that proof before copying anything. Resolve the parent register at `.wire/releases/<migration.parent_release>/migration/migration_register.csv` (skip this step with a note in the manifest if `migration.parent_release` is null or the file is unreachable — every relocated row then carries a blank `parent_verdict_ref`, which the relocate-mode comparator treats as unproven).

For each model in the Step 1.5 set, read its parent row's `last_equivalence_result`:

- **`fail`** — **refuse to relocate the model.** Record it in the manifest with reason `parent_verdict_fail` and the parent reference (`<parent_release>:<model>`, plus the parent's evidence ref). Relocating SQL the parent release has proven wrong copies a known defect into the tenant project; the fix belongs in the parent first.
- **`pass` / `pass_qualified`** — relocate, and carry the linkage into Step 6b.
- **Any `diff_*`, `null`, or no parent row** — relocate (the SQL is not proven wrong), record the parent verdict as found (or `none`), and leave `parent_verdict_ref` blank when there is no evidence to reference. The relocate-mode comparator does not use the parent target as a trusted basis until the parent verdict is `pass`/`pass_qualified` (see `equivalency-validate`, Relocate-mode comparison).

### Step 2: Relocate each in-scope model

For each model in the Step 1.5 set, read its bucket from `region_tags_adjudicated.csv`:

- **`bucket: confident-region`** — read the model's relative path within `--source-dbt-project-path` (from the manifest node), copy the `.sql` file and its companion schema/properties YAML entry into the mirrored path under `--target-dbt-project-path`, unchanged. Record `predicate_injection: not_applicable`.
- **`bucket: shared-row-level`** — copy the file to the mirrored path, then apply the model's filter from its registry row (Step 1.6) at the injection point the resolution ladder (Step 1.8) identified. A resolved model records `predicate_injection: injected`, the exact filter text applied, and the `resolved_by` value that got it there. A model the ladder could not resolve is copied unmodified and records `predicate_injection: manual_review_required` with its shape and reason — **do not guess.**
- **Any other `bucket` value** (`global-deferred`, missing, or anything not `confident-region`/`shared-row-level`) that reached this scope despite Step 1.5's filter — this is a resolution bug upstream, not a case to paper over here. **Abort**: `[wire] <model> has bucket "<bucket>" but adjudicated_ruling carve_in — this combination should not exist. Check region-tagging-review's output before re-running.`

Preserve the exact subdirectory structure from the source project for both the `.sql` file and its companion YAML.

### Step 2a: Tenant-Bronze-only source reduction, verified (#219)

A union-then-filter model reads every market's Bronze sources and filters afterwards; the sovereign project discards the foreign-market sources, so the relocated model must read the tenant's sources only. The reduction itself is mechanical (hardcode the tenant source list; seed `all_columns()`-style column-listing macros from the tenant relation instead of the union), but a reduction applied without verification is a rewrite nobody checked. For every model reduced this way, verify **both** of the following before it counts as relocated, and record the evidence in the manifest:

1. **Column-set parity.** Compile the original and the reduced model and compare their output column lists: name-for-name, in the same order. A macro seeded from the tenant relation can emit a different column set than the union it replaced; parity is the proof it did not.
2. **Compiled-SQL diff limited to the intended reduction.** Diff the two compiled SQLs and confirm every hunk is the reduction and nothing else: a removed foreign-source branch, or the substituted source list. Any hunk outside that scope means the reduction changed logic it should not have touched.

Record per model: the column lists compared (or their matching count), and the diff hunk summary. Either check failing means the model is **not** relocated: flag it `manual_review_required` with reason `reduction_not_verified` and the failing evidence.

### Step 2b: Expected-empty markers (#219)

A zero-row model passes every downstream test vacuously: row counts match at 0 = 0, checksums agree on nothing, dbt tests find no rows to fail on. A model that is legitimately empty for the tenant must therefore say so in a form a later gate can read.

Measure the source-side tenant row count for every relocated model under its resolved registry filter (Step 1.8b's distribution check already returns it for derived rows; run the count for adjudicated rows). When the count is zero:

- Establish the reason: the adjudication note, the registry row's provenance, or the consultant. A reason names why the tenant has no rows in this model (a market-specific feature the tenant never used, a product line the tenant does not sell), with the measured source figures.
- Stamp a greppable header comment as the first line of the relocated `.sql` file: `-- EXPECTED EMPTY (<tenant>): <reason>, source measured 0 rows on <date>`.
- Record `expected_empty: true` for the model in the manifest.

When the count is zero and **no reason can be established**, do not stamp and do not ship silently: flag the model `manual_review_required` with reason `expected_empty_unexplained`. The marker is what `equivalency-validate`'s both-sides-empty gate greps for: a marked model earns an explicit verdict there; an unmarked both-sides-empty model is a named failure (`empty_unexplained`), never a vacuous pass. Distinguish this case from Step 1.8b: expected-empty is a plausible tenant column that keeps zero rows in this one model; an implausible distribution questions the column itself.

### Step 2c: Write resolutions back to the registry (v3.11.3)

Update `migration/tenant_predicate_registry.csv` in place for every model the ladder touched: `mechanism`, `expression`, `tenant_column`, `resolved_by`, `resolving_node`, `provenance` (the rule id, the evidence query and its result, or the resolving node), `verified_date`, and `confidence`. Back up the file before writing and re-read it after, per the single-writer discipline in `specs/utils/migration_fleet.md` — under a fleet this command may be running in one lane while another reads the registry.

Write with a CSV writer under the write contract in `specs/utils/tenant_predicate_registry.md`, never by string concatenation: the ladder's semi-join and regex expressions carry commas and quotes, and a concatenating writer truncates them at the first comma while the row keeps a valid column count (#200).

Never overwrite a row whose `resolved_by` is `adjudication` or `manual`. A model whose ladder result disagrees with such a row is reported as a conflict in the manifest and left as the ruling says: a command that silently reverses a human ruling is worse than one that stops.

### Step 3: Configure the target profile

Confirm `--target-dbt-project-path`'s active profile target resolves to `--target-project` (and `--target-dataset`, if supplied). This is the destination the caller passed — playground or production — the command does not distinguish between them; it runs once per environment.

### Step 4: Compile the target project

Parse/compile only — no materialisation. Run `dbt parse` (or `dbt compile`) against `--target-dbt-project-path` for the relocated models, via `specs/utils/dbt_manifest_parse.md` Step 2's scratch-directory pattern (never writing to the target project's own `target/`/`dbt_packages/`). Catch injection errors (a broken `WHERE` clause, a YAML the copy left inconsistent) before they reach a build.

If compile fails, list the failing models and the compile error; do not silently continue past a broken relocation.

### Step 5: Write the relocation manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/dbt_carveout_relocate_manifest.md` — or `migration/dbt_carveout_relocate_manifest_{wave_id}.md` when run with `--wave` (a `--batch`/`--select` run without `--wave` still writes the unscoped filename; running each wave separately without this suffix would silently overwrite the prior wave's manifest).

Include:
- Scope resolved (wave/batch/selector), source and target project paths, target project/dataset
- Every relocated model: bucket, `predicate_injection` state, the mechanism and `resolved_by` from the registry, and the exact filter text where injected
- **Resolution summary** — a count per rung of how many models each resolved, and the resulting `manual_review_required` count. This is the number a reviewer's queue is measured by, so it belongs at the top of the manifest, not buried per model.
- **Proposed dispositions** (Rung 4) — each with its evidence query, the result, and the precedent compared against. These need a reviewer's ruling; they are not resolved.
- **Inheritance resolutions** (Rung 5) — each with its resolving node, and each unresolved model's *uncovered upstream* named, so the reviewer can see which single upstream fix unblocks which descendants.
- **Semantics checks** (Step 1.8b) — per derived row injected: the measured `distinct_values` and `tenant_share`, and the plausibility verdict. Implausible rows appear in the manual-review-required list with reason `predicate_semantics_implausible`.
- **Grain per injected model** (`grain: entity | row`), with the entity key used for each entity-grain injection
- **Source reductions** (Step 2a) — per reduced model: the column-set parity result and the compiled-SQL diff summary
- **Expected-empty models** (Step 2b) — each with its stamped reason and measured source figures
- The manual-review-required list, each with its shape, the rung that last examined it, and its specific reason
- Registry conflicts (a ladder result disagreeing with an `adjudication`/`manual` row)
- Models skipped because they had no `carve_in` adjudication in this scope
- Compile result (pass/fail, per model on failure)

### Step 6: Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    generate: complete
    generated_date: "{{TODAY}}"
    file: migration/dbt_carveout_relocate_manifest.md   # or _{wave_id}.md when run with --wave
    source_dbt_project_path: "{{SOURCE_DBT_PROJECT_PATH}}"
    target_dbt_project_path: "{{TARGET_DBT_PROJECT_PATH}}"
    target_project: "{{TARGET_PROJECT}}"
    target_dataset: "{{TARGET_DATASET}}"
    models_relocated: N
    confident_region_count: N
    shared_row_level_count: N
    manual_review_required_count: N
    inherited_count: N              # Rung 5 — scoped by a covered upstream, no filter of their own
    proposed_disposition_count: N   # Rung 4 — awaiting a reviewer's ruling
    registry_conflict_count: N      # ladder result vs an adjudication/manual row
    semantics_implausible_count: N  # Step 1.8b — derived predicates routed to manual review (#219)
    expected_empty_count: N         # Step 2b — models stamped EXPECTED EMPTY (#219)
    predicate_registry: migration/tenant_predicate_registry.csv
    compile: pass | fail
    wave: "B01"          # set only when run with --wave
    waves_complete: ["B01"]   # set only when run with --wave; accumulates across runs
```

### Step 6b: Update the migration register (v3.11.1)

For every successfully relocated model, upsert its row in `migration/migration_register.csv` exactly as `dbt-migration-generate` does: `source_path`, `source_layer`, `last_migrated_commit` (the parent-release source snapshot SHA the relocated file was taken from), `bq_target` (the **fully qualified** tenant project relation: `project.dataset.table`, from the tenant-side manifest node's resolved `database`/`project` + `schema` + `alias`, never recomposed from the model name, #201), `state: migrated` (`failed` on a compile failure; a `manual_review_required` predicate injection stays `pending` until resolved; `not_applicable_inherited` is `migrated` — an inherited model is resolved, not pending). Record `origin: relocate` in `notes` — the ship-and-verify pipeline reads this to pick the relocate-mode comparator (`equivalency-validate`, Relocate-mode comparison). Without these rows, relocated models are invisible to `dbt-migration-batch-raise` candidate derivation and to the delivery stage ladder. Skip silently if the register doesn't exist.

**Cross-release linkage (#180).** On the same upsert, write the three linkage columns from Step 1.9: `parent_release` (from `migration.parent_release`), `parent_model` (the model's name in the parent register), and `parent_verdict_ref` (`<parent_release>:<parent evidence ref>` — the parent register row's `last_equivalence_result` evidence; blank when the parent register was unreachable, recording the evidence gap rather than inventing a reference). These columns are what let a parent defect-class fix find its relocated copies (`equivalency-sweep`, `cross_release_triggers`) and what the relocate-mode comparator checks before trusting the parent target as a comparison basis.

### Step 7: Output summary

Print a per-model results table (model, bucket, predicate_injection state, compile result), then:

```
/wire:dbt-carveout-relocate-validate $ARGUMENTS --target-dbt-project-path <path>
```

### Step 8: Chain the downstream gates (v3.11.1; `--no-chain` opts out)

Unless `--no-chain` was passed, run the same gate chain `dbt-migration-generate` runs over its scope, against the relocated set: `dbt-carveout-relocate-validate`, then `dbt-migration-lint`, `dbt-migration-fix`, and `dbt-migration-pre-pr-review` scoped to the relocated models. A relocate run then leaves the gates already applied rather than stopping at a next-step suggestion, and its models arrive at `dbt-migration-batch-raise` eligibility with rule 2 (gates clean) already satisfiable.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/dbt_carveout_relocate_manifest.md` (`_{wave_id}` suffix when run with `--wave`)
- Updated `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` (Step 2c)
- Relocated `.sql` and companion schema/properties YAML files under `--target-dbt-project-path`, mirroring the source project's subdirectory structure
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `generate` as action.

Execute the complete workflow as specified above.
