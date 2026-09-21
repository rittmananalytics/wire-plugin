---
description: Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared
argument-hint: <release-folder>
---

# Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared

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
    'command': 'migration-batching-validate',
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

## Workflow Specification

---
wire_schema: "1.0"
command: validate
artifact: migration_batching
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
  - artifact: migration_batching
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared, parallel-safe claims hold

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Batching — Validate

## Purpose

Independently re-derives the ground truth for every check — the inventory object list, the object-level dependency graph, the macro flags — rather than trusting generate's self-report. This independence is the entire point: it is what catches a batch plan that has drifted out of sync with the real dependency graph.

## Validation Checks

Read `migration/migration_batching.csv`, `migration/migration_batching.md`, `migration/migration_inventory.md`, `audit/dbt_audit.csv`, and status.md.

**Read the partition mode first.** Take `artifacts.migration_batching.partition_mode` from status.md (`domain`, `build_ordered_waves`, or `readiness_waves`; treat absent as `domain` for backward compatibility). The mode changes what Checks 2b, 3, 5, 8, 9, 10, and 11 expect — Checks 1, 2, 4, 6, 7 are identical in every mode. All modes must still pass C2 (acyclic) and C3 (every cross-batch edge declared); the two wave modes satisfy both trivially via the full-prefix dependency. Check 8 runs only in `build_ordered_waves`; Checks 10 and 11 only in `readiness_waves`; Check 9 in both wave modes. Readiness mode also reads `migration/tenant_predicate_registry.csv`, `migration/region_tags_adjudicated.csv`, the parent register at `.wire/releases/<migration.parent_release>/migration/migration_register.csv`, and this release's own `migration/migration_register.csv`.

**Check 1 — Every inventory object classified exactly once**
Rebuild the union of objects from `migration_inventory.md`'s unified catalog. Confirm a 1:1 match against `migration_batching.csv` rows — no object missing, none duplicated, no CSV row without a matching inventory object. A row with `batch_id: NO-DEP` counts as classified — it is a deliberate, named bucket for objects with no model consumer (Check 3 confirms none exist), not a gap. Do not flag `NO-DEP` rows as missing, duplicate, or orphaned on that basis alone. In readiness mode, `B00` and `PEN-*` rows count as classified on the same terms.
PASS: one-to-one match. Report the `NO-DEP` count alongside the pass (e.g. "168 objects, 1:1 match, 12 routed to NO-DEP"), and in readiness mode the `B00` and per-pen counts too, so they're visible in the check output, not just the narrative.
FAIL: list missing objects, duplicates, and orphan CSV rows, with counts of each.

**Check 2 — Batch dependency DAG is acyclic**
Rebuild the batch-level dependency graph from the CSV's `depends_on_batches` column alone. Confirm no cycles.
PASS: acyclic.
FAIL: list the cycle (the sequence of batch_ids).

**Check 2b — `batch_id` token form (v3.11.7)**
Every row's `batch_id` matches the canonical form in `specs/utils/wave_resolution.md`: zero-padded upper-case `B` plus digits (`B01`, `B02`, … `B10`), or the reserved `NO-DEP`. In `readiness_waves` mode the reserved readiness tokens are also canonical: `B00`, and `PEN-<NAME>` (upper-case letters and hyphens, starting and ending with a letter). In the other two modes `B00` and `PEN-*` are token-form failures: only readiness mode mints them. Nothing else, in any mode.
PASS: every row canonical for the mode. FAIL: list each offending row with the value found and the expected form.

This check exists because the form was documented here and in 18 consuming specs, agreed on by all of them, and then a produced CSV carried `b1..b10` anyway (wire#192). Every `--wave` command downstream aborted with "no rows found" for a wave that existed, and a lane agent was blocked. The consumers now normalise case- and pad-insensitively as defence in depth, but the file is still wrong and this is the gate that says so. A validation that only checks what `batch_id` *means* (coverage, cycles, cross-batch edges) and never what it *is* leaves the cheapest failure to be found by the most expensive reader.

**Check 3 — Every real cross-batch graph edge is declared**
Independently rebuild the object-level dependency graph from `migration_inventory.md`'s adjacency list plus `dbt_audit.csv`'s manifest-derived model dependencies. Do **not** read `migration_batching.md`'s own DAG as ground truth. For every graph edge whose two endpoints land in different batches (per the CSV's `batch_id` assignments), confirm the dependency direction is represented in `depends_on_batches` for the dependent batch. This is the check that directly answers "does this batch plan actually hold against the real dependencies."

For every object classified `NO-DEP`, independently confirm it genuinely has **zero** graph edges to any model in the Check 3 graph. `NO-DEP` is for objects with no real consumer, not an escape hatch for skipping a batch/wave assignment on an object that does have one — a `NO-DEP` object with an actual model edge is a FAIL on this check, same as an undeclared cross-batch edge.

Readiness-mode `PEN-*` rows are different: a pen member is expected to have edges (its rule, not its graph position, is what parks it), and a pen is not a batch, so edges touching a pen are exempt from the edge-declaration requirement above. Check 11 is what polices them (pen readers confined to the residue wave).

PASS: every cross-batch edge declared, and every `NO-DEP` object confirmed edge-free.
FAIL: list every undeclared cross-batch edge — the two objects, their batches, and the correct direction — and separately list any `NO-DEP` object that in fact has a model consumer (the object, the model, and the edge).

**Check 4 — Batch-zero macro dependency present where required**
For every batch containing a model with a non-empty `platform_macros` value (re-read from `dbt_audit.csv`, not from generate's output), confirm the narrative declares the batch-zero macro translation pass as a prerequisite of that batch.
PASS: all affected batches declare it.
FAIL: list batches missing the prerequisite.

**Check 5 — Parallel-safe claims hold**
For every batch pair listed as parallel-safe in the narrative, confirm zero graph edges (either direction) between their member objects, per the Check 3 graph.
PASS: no parallel-safe claim contradicted.
FAIL: list each contradicted claim with the edge (objects, batches, direction) that breaks it.
In `build_ordered_waves` and `readiness_waves` modes the parallel-safe set must be **empty** (full-prefix dependencies make every wave sequential) — a non-empty parallel-safe list in either wave mode is a FAIL. `NO-DEP` must never appear in a parallel-safe grouping in any mode — it is a holding pen, not a batch, and having zero edges to everything is not evidence it's safe to schedule; a parallel-safe claim naming `NO-DEP`, or a readiness `PEN-*` id, is a FAIL.

**Check 6 — Every CSV row complete**
Each row has a non-empty `object_id`, `object_type`, `source_audit`, `domain`, `batch_id`, and `batch_name`. `depends_on_batches` may be empty. A row with `batch_id: NO-DEP` and `batch_name: "No model dependency — review"` is complete on the same terms as any other row — `NO-DEP` is a valid classification, not a placeholder for a missing one, and must not be flagged incomplete on that basis. `depends_on_batches` empty on a `NO-DEP` row is expected, not a defect. Readiness-mode `B00` and `PEN-*` rows are complete on the same terms, with `depends_on_batches` empty by design.
PASS/FAIL with incomplete rows listed.

**Check 7 — Candidates only, no premature lock-in**
Neither `migration_batching.md` nor `status.md` marks any batch "approved" or "final", and no batch carries a committed date or owner — that is `/wire:migration-batching-review`'s job.
PASS: no lock-in language.
FAIL: quote the offending lines.

**Check 8 — Build-ordered waves are well-formed (only when `partition_mode: build_ordered_waves`)**
Skip in `domain` and `readiness_waves` modes (readiness waves have their own Check 10). When the SCC fallback fired, independently confirm the waves are a valid build order:
- **Fallback is justified and recorded** — re-derive the domain-level SCC condition from the Check 3 object graph (a single SCC spanning the domains). Confirm the narrative and status (`scc_fallback: true`) record it. A build-ordered partition emitted when a viable acyclic *domain* partition existed is a FAIL (the fallback should only fire when it must).
- **Topological order holds** — for every object edge, the dependency's wave id ≤ the dependent's wave id (0 forward references across waves).
- **Full-prefix dependencies** — each wave `Bk`'s `depends_on_batches` is exactly `B01;…;B(k-1)` (wave 1 empty). A missing or partial prefix is a FAIL.
- **Domain tag retained** — every CSV row still carries a non-empty `domain` value for rollup.
PASS/FAIL with the specific violation(s) listed.

**Check 9 — Cutover partition present (only in the wave modes: `build_ordered_waves` or `readiness_waves`)**
Skip in `domain` mode. Confirm `migration_batching.md` has a non-empty `### Cutover partition (secondary view)` section: a domain-grouped rollup, independently re-derivable from the CSV's `domain` and `batch_id` columns, showing which wave(s) each domain's objects actually landed in. Confirm it states — in words, not just implied by the table — that build order and cutover/domain order diverge (because the SCC fallback fired, or because readiness waves are readiness bands rather than domains), and names at least the domains whose objects are split across the most waves. An empty or missing section, or one that just repeats the wave DAG without the domain rollup, is a FAIL — this is the check that stops a reader from mistaking a wave number for a client milestone grouping.
PASS: section present, non-empty, domain/wave mapping independently reproducible from the CSV, divergence stated explicitly.
FAIL: state which of the above is missing.

**Check 10 — Readiness waves are well-formed (only when `partition_mode: readiness_waves`)**
Skip in the other modes. Independently re-derive every model's readiness class from the ground-truth inputs (the registry's rule states and approval groups, the adjudicated `defer`/`split` rulings, the parent register's `delivery_stage` with a live repo read when reachable, this release's own register, and the dependency-closure fixpoint), following `migration-batching-generate` Step 4d exactly, and confirm the CSV agrees. Specifically:

- **Selection is justified and recorded**: status.md carries `migration.scope: tenant_carveout` and a non-null `migration.parent_release`, or the narrative records the `--partition-mode` override. A readiness partition emitted for a non-carve-out release with no override is a FAIL.
- **Every model's wave matches the re-derived class**: shipped models (own register `merged`/`production_verified`, or prior-`B00` preservation) in `B00` and nowhere else; unresolved or row-less registry items in `PEN-UNRESOLVED`; `defer`/`split`-ruled items in `PEN-EXCLUSION-PENDING`; parent-unmerged models (or their transitive dependents, per the fixpoint) no earlier than the waiting-on-parent wave; pen readers and mixed-gate closures in the residue wave.
- **Each gated wave is exactly one approval group and self-contained**: every member's pending-approval closure lies within that one group (plus ready/shipped upstreams). A member whose closure touches a second pending group belongs in residue.
- **Full-prefix dependencies**: each numbered wave's `depends_on_batches` is the full prefix of numbered waves including `B00`; empty on `B00`, pens, and `NO-DEP`.
- **Domain tag retained** on every row for rollup.
PASS/FAIL with each mismatched model listed: the CSV wave, the re-derived class, and the input that decides it.

**Check 11 — No forward-wave or holding-pen reads (only when `partition_mode: readiness_waves`)**
Skip in the other modes. Over the Check 3 object graph and the CSV's wave assignments:

- **Zero forward-wave reads**: for every model edge, the dependency's numbered wave ≤ the dependent's. A model in a shippable wave (the ready and gated waves, `B01` through the last gated wave) reading a model in any later wave is the schedule-breaking case: it would ship a model before its input exists on target.
- **Holding-pen readers are confined to the residue wave**: no model in any numbered wave except residue has an upstream in a `PEN-*` pen. A shippable-wave model reading a pen member is a FAIL, same as a forward read.
- **`B00` is history, not schedule**: exempt `B00` rows from both rules, but report any `B00` model whose upstream now sits in a pen or a numbered wave as an advisory for `/wire:migration-drift-generate`: shipped state has drifted against the current readiness inputs, which is that command's problem, not a batching failure.
PASS: no violations (state the advisory count, 0 included).
FAIL: list each violation (the two models, their waves, the direction) and, per violating model, the downstream closure it would drag forward, so the reader sees the size of the cascade, not just its first edge. On the reference engagement this check caught a real 7-model forward-read cascade during generation.

### Update status

```yaml
artifacts:
  migration_batching:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `validate` as action.

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
