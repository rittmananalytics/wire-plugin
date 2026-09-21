---
description: Generate client kick-off presentation deck from SoW and engagement context
argument-hint: [release-folder]
---

# Generate client kick-off presentation deck from SoW and engagement context

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
    'command': 'kickoff-generate',
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
artifact: kickoff
domain: kickoff
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Generate client kick-off presentation deck from SoW and engagement context
argument-hint: "[release-folder]"

---

# Kickoff Deck — Generate

## Purpose

Builds a client kick-off presentation by populating the EDITMODE JSON block inside the deck HTML template. The primary source is the Statement of Work and engagement context created by `/wire:new`. If a release folder is specified, discovery artifacts from that release enrich the deck further.

Run immediately after `/wire:new` — no discovery or delivery artifacts are required for a first pass. Re-run at any time as more artifacts become available.

## Inputs

**Always required**:
- `.wire/engagement/context.md` — client name, engagement type, team members, SoW reference
- `wire/decks/kickoff/Project Kickoff.html` — blank template (installed with Wire)

**Optional — SoW (primary content source)**:
- `engagement/sow.md`, or a PDF referenced from `engagement/context.md`, or any file under `engagement/references/`

**Optional — release enrichment** (only if `<release-folder>` argument supplied). Sources depend on `release_type` in `.wire/releases/<release-folder>/status.md`:

For `discovery`:
- `.wire/releases/<release-folder>/planning/problem_definition.md`
- `.wire/releases/<release-folder>/planning/pitch.md`
- `.wire/releases/<release-folder>/planning/sprint_plan.md`

For `sop_discovery`:
- `.wire/releases/<release-folder>/planning/engagement_brief.md`
- `.wire/releases/<release-folder>/planning/stakeholder_map.md` (for the attendee list and named domain SMEs)

For all release types:
- `.wire/releases/<release-folder>/requirements/requirements_specification.md` (if present)
- `.wire/releases/<release-folder>/planning/pipeline_design.md` (if present)

## Workflow

### Step 1: Check prerequisites

1. Confirm `.wire/engagement/context.md` exists. If not: stop — "Run `/wire:new` first to initialise the engagement."

2. Locate the deck template. Check the following paths in order:
   a. `wire/decks/kickoff/Project Kickoff.html` — Wire source repo layout
   b. `decks/kickoff/Project Kickoff.html` — plugin installation layout (when installed via `/plugin install wire`)
   c. Run `find . -name "Project Kickoff.html" -path "*/kickoff/*" 2>/dev/null | head -1` to discover any other location

   If found at (b) or (c) but not (a), note the actual path and use it throughout the rest of the command in place of `wire/decks/kickoff/Project Kickoff.html`.

   If not found at any location: attempt to bootstrap by running:
   ```bash
   mkdir -p wire/decks/kickoff/assets
   ```
   Then instruct the user:
   > "The kickoff deck template could not be found. To install it, run:
   > `find ~/.claude -name 'Project Kickoff.html' 2>/dev/null`
   > If found, copy the `decks/kickoff/` folder from your Wire plugin installation to `wire/decks/kickoff/` in this directory.
   > If not found, pull the latest Wire plugin to get the template bundled with the plugin."
   Stop here.

3. If `<release-folder>` was supplied, confirm the folder exists at `.wire/releases/<release-folder>/`. If not: warn and continue without release enrichment.

4. **Ask the user about a title page image** — before reading any content, ask:
   > "Do you have an image you'd like to use as the title slide background? If so, please provide the file path (e.g. `/Users/you/photos/client-office.jpg`). Press Enter to skip and use the default RA background."

   If the user provides a path:
   - Verify the file exists.
   - Determine the output directory for the kickoff deck (see Step 6 for paths).
   - Copy the image into `$OUTPUT_DIR/kickoff/assets/` with a normalised filename: `title-photo.<original-extension>`.
   - Set `"titlePhoto": "kickoff/assets/title-photo.<ext>"` in the EDITMODE JSON.

   If the user skips: leave `"titlePhoto": ""` (the deck will use its built-in default background).

### Step 2: Read engagement context

Read `.wire/engagement/context.md`. Extract:

- `client_name` — formal client name for the title slide
- `engagement_type` — map to EDITMODE values:
  - `discovery` → `engagementType: "Discovery"` (discovery sprint kickoff mode)
  - any delivery type (`full_platform`, `pipeline_only`, `dbt_development`, `dashboard_first`, `dashboard_extension`) → `engagementType: "Project"`
- `team` or `presenters` — list of RA team members and roles presenting
- `start_date` or `engagement_date` — used as `engagementDate` (ISO format)
- `accent_color` — **ignore this field**. Always set `accentColor` to `#4F60FF` (RA indigo). The deck's `accentColor` overrides `--ra-indigo` across the entire design system (eyebrows, bullet dots, table headers, cards). Using a client's brand colour here replaces the RA design system; the RA indigo must be preserved.
- Any SoW file path referenced under `sow:` or `references:`

### Step 3: Read the Statement of Work

Look for a SoW in this order:
1. Path referenced in `engagement/context.md` under `sow:` or `references:`
2. `engagement/sow.md`
3. `engagement/references/sow.pdf` (or any PDF under `engagement/references/`)
4. Any `.md` file in `engagement/references/`

If found, extract:
- **Engagement objectives** — the headline goals the client wants to achieve. Synthesise as 3–5 bullet points describing current state and desired state. Use these for `slide4LeftCache` (current state) and `slide4RightCache` (desired state).
- **Headline metric** — any quantified business impact mentioned (cost saving, time reduction, risk reduction). Use for `slide5*` fields.
- **Proposed approach** — summarise as 3–5 outcome statements for `slide8Outcomes`.
- **Data sources / systems in scope** — list up to 4 distinct systems for `slide14Categories`. For each system, write a specific, actionable `needs` string describing exactly what access is required. Use the patterns below as a guide — match the type of system:
  - Database / data warehouse (Postgres, BigQuery, Snowflake, Redshift, SQL Server, etc.): "Login credentials and connection details — host, port, database name, and a read-only user account"
  - ETL / pipeline tool (Fivetran, Airbyte, Stitch, etc.): "Admin login and permission to view/edit connectors and destination configuration"
  - CRM / SaaS app (Salesforce, HubSpot, etc.): "Connected App or OAuth credentials with read-only API access to the relevant objects"
  - BI / reporting tool (Looker, Tableau, Power BI, etc.): "Viewer or developer login with access to the relevant content and underlying data source connections"
  - File storage / spreadsheets (Google Sheets, SharePoint, S3, etc.): "Service account or shared link with read access; bucket/folder path and any access keys if S3"
  - Adapt the pattern to the actual system — be specific about what the RA team will need on day one to begin the data audit.
- **Timeline / phases** — use to populate `slide12W1Focus` and `slide12W2Focus` if no sprint plan exists.
- **Team members named in the SoW** — supplement or replace the presenters list.

If no SoW is found, proceed in scaffold mode: all content fields remain as empty strings with a comment noting manual completion is required.

### Step 4: Enrich from release artifacts (if release-folder supplied)

If a release folder was specified, first read `.wire/releases/<release-folder>/status.md` and resolve `release_type`. Then enrich the deck content from the artifacts that match the release type. Both discovery flavours are supported; for delivery release types, only the cross-cutting fallbacks (requirements_specification, pipeline_design) apply.

---

#### For `release_type: discovery`

**From `problem_definition.md`** (if `problem_definition.review: complete`):
- `slide4Headline`: synthesise an 8–12 word headline naming the core friction from Section 3. Do not use the section heading verbatim.
- `slide4LeftCache`: current state — summarise Section 4 Impact table "Current State" column as 3–5 bullet points (HTML allowed; use `<strong>` for key terms).
- `slide4RightCache`: desired state — from Section 5 "What Solved Looks Like".
- `slide5*`: most impactful quantified metric from Section 4. Prefer cost, time savings, or risk. Format: `slide5Number` = the digit(s), `slide5Suffix` = unit symbol, `slide5Bold` = bold lead sentence, `slide5Tail` = supporting sentence.
- `slide6Problems` (exactly 8 entries): root causes from Sections 3 and 7. Generate 3–5 word headlines and 1–2 sentence details. Pad unused slots with `{"headline": "", "detail": ""}`. Set `slide6Count` to the number of non-empty entries.

**From `pitch.md`** (if `pitch.review: complete`):
- `slide8Outcomes` (exactly 5 entries): from Section 7 "Success Criteria". 3–5 word headline + 1–2 sentence detail per outcome. Pad to 5. Set `slide8Count`.

**From `sprint_plan.md`** (if `sprint_plan.review: complete`):
- `slide12W1Focus`: sprint goal for Sprint 1.
- `slide12W2Focus`: sprint goal for Sprint 2 (or "Continuous delivery and review" if single-sprint plan).
- `slide12W1Items` (exactly 6 strings): first 5 stories/epics from Sprint 1 — **cap at 5, never fill slot 6 with real content**. Pad slots 5 and 6 with `""`. Set `slide12W1Count` to the number of non-empty entries (max 5).
- `slide12W2Items` (exactly 6 strings): same from Sprint 2 — cap at 5. Pad slots 5 and 6 with `""`. Set `slide12W2Count` (max 5). The 6th slot exists to satisfy the fixed array length but must always be empty.

---

#### For `release_type: sop_discovery`

The SOP discovery kick-off is the playbook's Phase 1 meeting — its job is to align the sponsor and stakeholders on the discovery process about to run, not on a specific delivery scope. Enrichment is therefore lighter: there are no Shape Up artefacts yet, only the engagement brief and (optionally) the stakeholder map.

**From `engagement_brief.md`** (if `engagement_brief.review: complete`):
- `slide4Headline`: a 8–12 word headline naming the engagement's problem statement (from the Problem statement row in the brief). Do not use deliverable framing.
- `slide4LeftCache`: current-state context drawn from the "Known constraints" and "Known risks" rows — 3–5 bullets.
- `slide4RightCache`: desired-state framing drawn from the "Desired outcome" row plus the in-scope domain list.
- `slide5*`: most striking success-metric or named target from the "Success metrics" row.
- `slide6Problems` (exactly 8 entries): pre-discovery hypotheses — themes RA expects to investigate during interviews. Use the brief's "Known risks" and "Out-of-scope" rows for material. Pad unused slots.
- `slide8Outcomes` (exactly 5 entries): the standard SOP discovery exit deliverables — engagement brief, stakeholder interviews, requirements matrix, three analyses (Hierarchy/PPT/Maturity), Findings Playback deck. Use this to set the right expectation about what the sponsor will see at the end of the engagement.

**From `stakeholder_map.md`** (if `stakeholder_map.review: complete`):
- `slide12W1Focus`: "Stakeholder interviews — week 1" with the count of P0 interviews planned.
- `slide12W2Focus`: "Stakeholder interviews — week 2" with the count of P1 interviews planned.
- `slide12W1Items` (exactly 6): list of P0 stakeholder names with title. Cap at 5; pad slots 5 and 6 with `""`.
- `slide12W2Items` (exactly 6): list of P1 stakeholder names with title. Same cap and padding rules.

The intent: a SOP discovery kick-off should leave every stakeholder knowing whether they're being interviewed, by whom, in what week, and what the exit deliverable will be.

---

#### Cross-cutting fallbacks (all release types)

**From `requirements_specification.md`** (if present):
- `slide14Categories` (exactly 4 entries): data access requirements. For each system, write the `needs` field as a specific, actionable string (see the access patterns in Step 3 above — database, ETL tool, CRM, BI tool, file storage). Pad unused slots to 4 with `{"name":"","needs":""}`. Set `slide14Count`.

**From `pipeline_design.md`** (if present):
- `slide10MermaidCache`: raw Mermaid source (no fences). Set `slide10Direction` to `"TB"` if > 8 nodes, otherwise `"LR"`. Set `slide10Headline` and `slide10Prompt` from the document's purpose.
  **Mermaid label rules** — node labels must not contain `\n` escape sequences (they render as literal backslash-n in the diagram). Keep labels short (≤ 25 characters) and single-line. If a label needs a line break, use `<br/>` inside a quoted HTML label: `A["Line one<br/>Line two"]`. Never use `\n` in any Mermaid string.

Discovery artifact content overrides SoW-derived content for the same fields.

### Step 5: Assemble and validate the EDITMODE JSON

Build the complete JSON object. Validate before writing:

- `slide6Problems` is exactly 8 entries
- `slide8Outcomes` is exactly 5 entries
- `slide12W1Items` and `slide12W2Items` are exactly 6 entries each
- `slide14Categories` is exactly 4 entries
- Count fields do not exceed array length
- `slide12W1Count` and `slide12W2Count` are ≤ 5 (the 6th slot is always empty — the slide layout fits 5 items per column readably)
- `accentColor` is always `"#4F60FF"` (RA indigo). Never substitute a client brand colour here.
- `vignetteStrength` is an **integer 0–100** (the range slider unit). Default to `74`. Do not write a float like `0.5` — the JS divides by 100 at render time, so `0.5` renders as 0.5% opacity (invisible vignette).
- `titleVariant` is always `"pitch"` — this is the value that enables the full-bleed photo backdrop on the title slide. Do not use `"photo"` or any other value; the deck JS only recognises `"pitch"` as the photo variant.
- `slide10Direction` is `"LR"` or `"TB"` (or `""` if slide10 is empty)
- The full object parses as valid JSON (no trailing commas, no comments)
- **String values must not contain literal newlines** — multi-line bullet lists (e.g. `slide4LeftCache`, `slide4RightCache`) must have newlines escaped as `\n`. Literal newlines inside double-quoted JS strings cause a syntax error that silently prevents the entire deck from rendering. Serialise using `json.dumps()` or equivalent, never by hand-writing multi-line strings.

### Step 6: Write the output file

**If `.wire/releases/<release-folder>/artifacts/kickoff-deck.html` already exists**: read its EDITMODE block first and merge — preserve any fields manually set (e.g. `titlePhoto`, `accentColor`, `showPartnerBadge`, `presenters`) unless the new generated value is non-empty. This allows re-runs without losing manual edits.

Read `wire/decks/kickoff/Project Kickoff.html`. Locate the EDITMODE delimiters:
```
/*EDITMODE-BEGIN*/
...
/*EDITMODE-END*/
```

Replace the content between (and including) the delimiters with the new JSON. Write the result to:

- **Engagement-level run** (no release folder): `.wire/kickoff-deck.html`
- **Release-enriched run**: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

Do not modify the template file at `wire/decks/kickoff/Project Kickoff.html`.

**MANDATORY: Copy support files into a `kickoff/` subdirectory.** The deck HTML references CSS, JS, fonts, and assets using relative paths. Without these files next to the HTML, the deck will render with no styling, no fonts, and no images. **You must run the following bash commands immediately after writing the HTML file — do not skip this step, do not ask the user to do it.**

Substitute the actual paths for `TEMPLATE_DIR` and `OUTPUT_DIR`:
- `TEMPLATE_DIR` = the directory where the template was found (Step 1): `wire/decks/kickoff/` (Wire source repo) or `decks/kickoff/` (plugin install)
- `OUTPUT_DIR` = the directory containing `kickoff-deck.html`

**Run these bash commands now:**
```bash
mkdir -p "$OUTPUT_DIR/kickoff"
cp "$TEMPLATE_DIR/colors_and_type.css"  "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/deck.css"             "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/deck-stage.js"        "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/mermaid.min.js"       "$OUTPUT_DIR/kickoff/"
cp -r "$TEMPLATE_DIR/fonts"             "$OUTPUT_DIR/kickoff/"
cp -r "$TEMPLATE_DIR/assets"            "$OUTPUT_DIR/kickoff/"
```

After running those commands, rewrite all external file references in the output HTML. These substitutions are also mandatory — the HTML file still has the original relative paths from the template. Do all as simple string substitutions across the entire file:

| Find | Replace | Covers |
|------|---------|--------|
| `href="colors_and_type.css"` | `href="kickoff/colors_and_type.css"` | CSS link tag |
| `href="deck.css"` | `href="kickoff/deck.css"` | CSS link tag |
| `src="mermaid.min.js"` | `src="kickoff/mermaid.min.js"` | Script tag |
| `src="deck-stage.js"` | `src="kickoff/deck-stage.js"` | Script tag |
| `src="assets/` | `src="kickoff/assets/` | All `<img>` tags (logo, partner logos, title bg — 15+ occurrences) |
| `'assets/` | `'kickoff/assets/` | JavaScript string references to assets (fallback title photo path in JS) |
| `` `assets/team/ `` | `` `kickoff/assets/team/ `` | Backtick template literal in `checkPhoto()` — derives team headshot paths from presenter name slug; the `photo` field on presenter objects is ignored by the deck JS |

The resulting artifacts directory structure:
```
artifacts/
├── kickoff-deck.html        ← references kickoff/* for all external files
└── kickoff/
    ├── colors_and_type.css
    ├── deck.css
    ├── deck-stage.js
    ├── mermaid.min.js
    ├── fonts/
    │   └── GoogleSans-*.ttf
    └── assets/
        └── ...
```

**Verify the copy succeeded** by running:
```bash
ls "$OUTPUT_DIR/kickoff/colors_and_type.css" "$OUTPUT_DIR/kickoff/deck-stage.js" "$OUTPUT_DIR/kickoff/fonts/" "$OUTPUT_DIR/kickoff/assets/"
```
If any path is missing, copy it now before proceeding. Do not report success until all four exist.

### Step 7: Update status

**Engagement-level run**: add or update `kickoff_deck` in `.wire/engagement/context.md` (or a dedicated `kickoff_status.md` if context.md has no artifact section).

**Release-enriched run**: add or update in `.wire/releases/<release-folder>/status.md`:
```yaml
kickoff_deck:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "artifacts/kickoff-deck.html"
  generated_date: "<today>"
```

### Step 8: Report output

Show the consultant:
- Output file path (absolute, so they can open it directly)
- Which slides have content and which are placeholders requiring manual completion
- If discovery artifacts were available but not yet approved (not `review: complete`), list them and note what they would have contributed
- Next step: "Run `/wire:kickoff-validate` to check the deck, or open the file in Chrome to preview."

## Edge cases

- **No SoW, no discovery artifacts**: proceed in scaffold mode. All content slides are empty. Output a clear list of every field that needs manual completion.
- **Engagement type is `discovery` but no `--discovery` flag**: automatically set `engagementType: "Discovery"` since `context.md` already signals this.
- **Re-run after discovery artifacts become available**: merge, preserving manual edits. Log which fields were updated from newly approved artifacts.
- **Pipeline design has Mermaid with > 8 nodes**: set `slide10Direction: "TB"` automatically.
- **Multiple SoW files found**: read all, merge the content, note in the report.

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
