---
description: Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work
argument-hint: <release-folder> [--wave id 
---

# Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work

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
    'command': 'dbt-migration-reverse-port',
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
command: utility
artifact: dbt_migration
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work, recorded in the register
argument-hint: <release-folder> [--wave id | --models list] [--repo-role transformation] [--dry-run]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

---

## Data Safety — Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command WRITES into the delivery tree. It never writes to the client repo.

  Direction of travel: client default branch  ->  delivery tree.
  One direction only. Nothing here raises, pushes, or amends anything on
  the client side.

  A model whose delivery-tree copy is AHEAD of the client's is never
  overwritten. That is unraised work, not stale work.
```

If any step would write to the client repo, or would overwrite a delivery-tree file that is ahead of the client's, stop and report the conflict before writing anything.

---

# dbt Migration — Reverse Port

## Purpose

After a model's PR merges, the version on the client's default branch can differ from the delivery tree's copy: a CI fix applied in the PR, a reviewer's change, a conflict resolved during the merge. Nothing carried that back. The delivery tree, which the next wave's translations read from and which every later comparison and lint pass treats as the authored truth, quietly stops being true.

On one release **86 of 94 models drifted** this way, because the sweep existed only as a habit in an engagement process document. This command makes it a step with a state.

**This is a different axis from `migration-drift`.** That gate compares the **live source platform** against `last_migrated_commit`, asking "has the thing we translated changed underneath us". This asks "has the thing we shipped changed after we shipped it". Both can be true at once and neither substitutes for the other.

## Prerequisites

- `migration/migration_register.csv` exists with at least one row at `delivery_stage: merged` or `production_verified`
- `migration.client_repos` configured for the `--repo-role` (default `transformation`)
- The delivery tree is committed, or has only changes you are willing to have reported: this command reads working-tree state to tell delivery-ahead from stale

## Flags

- `--wave <id>` — restrict to that wave's models. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).
- `--models a,b` — restrict to named models. Mutually exclusive with `--wave`.
- `--repo-role <role>` — which client repo to read (default `transformation`).
- `--dry-run` — classify and report, write nothing. Produces exactly the same classification as a real run.
- No flag — every register row at `merged` or `production_verified`.

## The four-way classification (deterministic)

Tests mirror this table exactly (`wire/tests/platform_migration/validate_reverse_port.py`). For each in-scope model, compare three things: the file on the client's default branch (live read), the file in the delivery tree, and the delivery-tree file's content at `last_reverse_ported_commit` (or `last_migrated_commit` on the first sweep) as the common ancestor.

| # | Condition | Class | Action |
|---|---|---|---|
| 1 | Client and delivery identical | `in_sync` | Record the check. Write nothing |
| 2 | Client differs from delivery; delivery matches the ancestor | `client_ahead` | **Copy the client's version into the delivery tree.** Record the client commit |
| 3 | Client matches the ancestor; delivery differs from it | `delivery_ahead` | **Flag. Never write.** This is a local edit that was never raised |
| 4 | Both differ from the ancestor, and from each other | `diverged` | **Flag as a conflict.** Emit both diffs. A person resolves it |

**The never-clobber rule on `delivery_ahead` is mechanical, with no override flag.** A sweep that overwrites unraised local work in order to "fix" drift has destroyed more than the drift cost: the drift was a stale copy of something that exists in the client repo, while the local edit exists nowhere else. If the local edit is genuinely unwanted, deleting it is a deliberate act for a person, not a side effect of a sync.

`diverged` is likewise never auto-resolved. Two edits to the same file from two directions is the one case where the right answer needs to know why each was made.

## Workflow

### Step 1: Resolve scope and read both sides

Resolve the model set per **Flags**. Fetch the client repo live (`git fetch` plus a read of the default branch) for each model's target path; read the delivery tree's copy; resolve the ancestor content from `last_reverse_ported_commit`, falling back to `last_migrated_commit` on a model's first sweep.

If the client repo is unreachable, stop. Do not classify from the register's memory of what was merged: this command exists because the register's memory and the client's reality diverge, so trusting the former defeats it.

A model whose register row is `merged` but whose file is **absent** from the client's default branch is reported as `merge_state_stale` and skipped, not classified. The register believes something the repo does not, and that is a register correction (`migration-status` re-derives merge state live), not a port.

### Step 2: Classify

Apply the table above, per model. Normalise nothing before comparing: no whitespace trimming, no reformatting. A whitespace-only change made by the client's formatter in CI is a real change to the authored file and the delivery tree should carry it, or the next lint pass will keep proposing to undo it.

### Step 3: Port the `client_ahead` models

Copy each `client_ahead` model's client version into the delivery tree at its mirrored path, along with any companion schema/properties YAML the PR changed. Under `--dry-run`, skip this step entirely.

Do not reformat, re-lint, or "improve" the ported file in passing. It is the version the client merged and it is now the authored version; a change made during the port is a change nobody reviewed.

### Step 4: Update the register

For every ported model, set `last_reverse_ported_commit` to the client commit the content came from. Leave every other column alone: a port changes what the authored file is, not the model's delivery stage or its verdict.

**A ported model's standing equivalence verdict is superseded.** The verdict bound to a specific file version and the file has changed. Blank `last_equivalence_result` with an audit note naming the port, exactly as `equivalency-sweep` does when it supersedes a verdict, and emit the re-verify as owed. A port that silently keeps a verdict for a file that no longer exists is worse than no port at all.

### Step 5: Report

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_port_report_{run_number}.md`

- Counts per class, and the scope resolved
- `client_ahead`: model, client commit, a diff summary, and the re-verify now owed
- `delivery_ahead`: model, the local diff, and the observation that this work has never been raised. This list is a to-do, not an error
- `diverged`: model, both diffs, and the ancestor reference
- `merge_state_stale`: model and the register row that needs correcting
- `in_sync`: a count, not a list

### Step 6: Update status

```yaml
artifacts:
  reverse_port:
    last_run_date: "{{TODAY}}"
    last_run_number: N
    models_checked: N
    in_sync: N
    client_ahead: N          # ported
    delivery_ahead: N        # flagged, never written
    diverged: N              # flagged as conflicts
    merge_state_stale: N
    reverify_owed: N         # verdicts blanked by a port
```

### Step 7: Output next step

```
Ported <n> models from the client's default branch.
<m> verdicts superseded and owed re-verification:
/wire:equivalency-validate $ARGUMENTS --models <list>
<k> models are ahead in the delivery tree and have never been raised.
<j> diverged and need a person.
```

## When to run it

After every merge, before the next wave's translation starts. The cost of skipping it compounds: the next wave's models are translated against a delivery tree that is already wrong, so the drift is inherited rather than merely persisted. `migration-status exceptions` lists models at `merged` whose `last_reverse_ported_commit` is blank, which is the standing reminder.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_port_report_{run_number}.md`
- Ported `.sql` and companion YAML files in the delivery tree
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_port` as artifact, `generate` as action.

Execute the complete workflow as specified above.
