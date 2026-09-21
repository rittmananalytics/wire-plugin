---
description: Clone the private wire-data-model-registry repo to this machine, for RA staff with access
argument-hint: (no arguments - interactive)
---

# Clone the private wire-data-model-registry repo to this machine, for RA staff with access

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
    'command': 'utils-data-model-registry-setup',
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
artifact: data_model_registry_setup
domain: utils
release_types: []
action_type: utility
logs_execution: false
description: Clone the private wire-data-model-registry repo to this machine, for RA staff with access
argument-hint: (no arguments - interactive)

---

# Data Model Registry Setup

## Purpose

One-time, per-machine setup for the optional data model registry feature used by `/wire:data_model-generate` and `/wire:data_model-validate` (see `wire/schemas/data-model-registry.md`). This is **not** part of the Wire plugin's bundled content — `rittmananalytics/wire-data-model-registry` is a private repo containing proprietary reference implementations generalized from real RA client engagements, and the plugin itself is public. Running this command clones it to your own machine using your own git credentials; it is not fetched or bundled any other way.

If you don't have access to the private repo, this command isn't for you — Wire works completely normally without it. `data_model-generate`/`data_model-validate` silently skip the canonical-vertical feature when the local copy isn't present; nothing else is affected.

## Usage

```bash
/wire:utils-data-model-registry-setup
```

Not scoped to a release or engagement — this sets up your machine once, and every engagement you work on afterward can use it.

## Workflow

### Step 1: Check for an existing local copy

```bash
ls ~/.wire/data-model-registry/.git 2>/dev/null
```

If present:
```
Data model registry already set up at ~/.wire/data-model-registry/.
Pull the latest? (yes / no)
```
- **yes** — `cd ~/.wire/data-model-registry && git pull`, report the result, stop.
- **no** — stop.

If absent, continue to Step 2.

### Step 1.5: The attempted marker (for other commands calling this non-interactively)

Some Wire commands (`/wire:new`, `/wire:autopilot`) attempt this setup automatically and silently when they're about to work on an artifact that could use the registry, rather than requiring a consultant to have run this command manually first. When invoked that way (no interactive session, not run directly by a person), skip Step 1's interactive prompt — if a local copy already exists, just proceed as normal; don't ask about pulling. After Step 3 completes (success or failure), always write:

```bash
mkdir -p ~/.wire
date -u +%Y-%m-%dT%H:%M:%SZ > ~/.wire/data_model_registry_setup_attempted
```

This marker means: "a clone was attempted on this machine, at this time — don't automatically re-attempt from an automated caller." It does not mean the clone succeeded. Automated callers check for this marker's existence before invoking this workflow at all, so they only ever attempt once per machine, not once per engagement or release. A person running this command directly and interactively should feel free to re-run it any time regardless of the marker — the marker only gates *automatic* invocation, never a consultant's own deliberate one.

### Step 2: Clone

Prefer the `gh` CLI — it uses whatever `gh auth login` token is already active, which works non-interactively and fails cleanly on an auth error. Plain `git clone` over HTTPS depends on a credential helper being separately configured (keychain, Git Credential Manager, a PAT) and, run non-interactively via this command, either hangs prompting for a username/password or fails outright if that isn't set up — so it's a fallback only.

```bash
mkdir -p ~/.wire
if command -v gh >/dev/null 2>&1; then
  gh repo clone rittmananalytics/wire-data-model-registry ~/.wire/data-model-registry
else
  git clone https://github.com/rittmananalytics/wire-data-model-registry.git ~/.wire/data-model-registry
fi
```

### Step 3: Handle the result

**If the clone succeeds**, report:
```
✅ Data model registry set up at ~/.wire/data-model-registry/.

/wire:data_model-generate and /wire:data_model-validate will now automatically check
this for a canonical vertical match on every engagement. This is advisory only — it
proposes, never forces, and any engagement can decline the match at generate time.
```

**If the clone fails** (403, 404, or any authentication/access error), report plainly — this is an expected, unremarkable outcome for anyone outside RA, not an error to troubleshoot:
```
Could not clone rittmananalytics/wire-data-model-registry — this is a private RA-internal
repo. If you're not sure you should have access, this command isn't relevant to you: Wire
works completely normally without it, this just skips the canonical-vertical proposal step
in data_model-generate/validate. If you believe you should have access, check with whoever
manages RA's GitHub org.
```

The one exception worth a distinct message: if `gh` isn't installed and the fallback `git clone` fails with a credential/authentication error specifically (not a 404), it may just mean git isn't authenticated yet rather than lacking access — mention that installing `gh` and running `gh auth login` is the fastest fix, then re-running this command.

Do not retry automatically beyond that one distinction, and do not treat a plain access-denied outcome as a bug — a failed clone here is a normal, expected outcome for the majority of people who might run this command.

**When invoked automatically** (not directly by a person — see Step 1.5), skip the messages above entirely. Write the attempted marker (Step 1.5) and, on success only, note it briefly and unobtrusively in the calling command's own output (e.g. one line: "Data model registry found — canonical-vertical matching available for this engagement"). On failure, say nothing at all — an automated attempt failing is not news to surface, since it's the default outcome for most people.

## Notes

- This is a personal, per-machine setup, not a framework-level sync. There's no pinned version — you get whatever's on the registry's `main` branch when you run this, and `git pull` to refresh whenever you like. Contrast with `wire/scripts/sync-data-model-registry.sh`, which is the *framework maintainers'* pinned, reviewed sync into the Wire repo's own `wire/data-model-registry/` (used only when developing Wire itself, not by consultants running engagements).
- `data_model-generate`/`validate` check `wire/data-model-registry/` first (present only inside the Wire framework source repo) and fall back to `~/.wire/data-model-registry/` (this command's output) — same two-tier "dev mode / personal setup" pattern `droughty-setup.md` uses for its own pinned version file.

Execute the complete workflow as specified above.
