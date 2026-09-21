---
description: Extract deliverables, acceptance criteria, and timeline from SoW or project documents
argument-hint: <file-path-or-url> [<file-path-2> ...]
---

# Extract deliverables, acceptance criteria, and timeline from SoW or project documents

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
    'command': 'utils-doc-analyze',
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
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Extract deliverables, acceptance criteria, timeline, and stakeholders from SoW or project documents
argument-hint: <file-path-or-url> [<file-path-2> ...]

---

# Document Analysis Utility

## Purpose

Read one or more source documents (SoW, kick-off notes, agreed delivery plan, proposal) and extract a structured `DeliverableList` object containing deliverables with acceptance criteria, timeline milestones, and stakeholders. Each deliverable is scored against the Wire artifact keyword table to determine whether a standard Wire command can handle it or a custom spec is needed.

Called automatically by `/wire:custom-define` (Phase 1). Can also be invoked standalone to preview what Wire would extract before committing to a custom release definition.

## Usage

```bash
/wire:utils-doc-analyze path/to/SoW.pdf [path/to/kickoff-notes.md] [path/to/plan.pdf]
```

When called internally from `/wire:custom-define`, the caller passes pre-read document content rather than re-reading files.

## Prerequisites

- At least one document must be provided (file path, Google Drive URL, or Confluence URL)
- PDF files: use the Read tool
- `.md` / `.txt` files: use the Read tool directly
- `.docx` / `.pptx` / `.xlsx` files: prompt the user to paste the relevant sections if the Read tool cannot parse them

---

## Workflow

### Step 1: Ingest Documents

For each provided path or URL:

1. **Local PDF / Markdown / text**: Read using the Read tool. For multi-page PDFs, read all pages.
2. **Google Drive URL**: Use `google_drive_read_file_content` if available; otherwise ask the user to export and provide a local path.
3. **Confluence URL**: Use `mcp__claude_ai_Atlassian__getConfluencePage` if available; extract body text.
4. **Inline paste**: Accept text directly in the conversation.

Record:
```
source_documents: [
  { path: string, type: "pdf"|"md"|"txt"|"docx"|"confluence"|"gdrive", title: string }
]
```

---

### Step 2: Extract Deliverables

Scan each document for deliverables. Look for:

- Numbered or bulleted lists under headings: "Deliverables", "Outputs", "Milestones", "What we'll deliver", "Scope of Work", "Services"
- SOW line items with descriptions (e.g. "1.1 Architecture Document: A blueprint detailing...")
- Tables with columns like "Deliverable | Description | Due Date"
- Acceptance criteria sections (e.g. "The deliverable is complete when...")
- Paragraph-level descriptions that include verbs like "produce", "deliver", "create", "draft", "design", "develop", "write", "define"

For each identified deliverable, extract:

```
{
  name: string,                 # short canonical name (3-6 words, title case)
  description: string,          # one-paragraph description of what must be produced
  acceptance_criteria: string[], # list of measurable conditions for completion
  estimated_effort: string | null,  # e.g. "3 days", "Week 3", "12 hours" — if stated
  dependencies: string[],       # other deliverables this depends on
  source_doc: string,           # which document this came from (filename/title)
  phase_or_week: string | null  # if the document groups deliverables by phase/week
}
```

**Effort estimation**: if the document contains a phased delivery plan (e.g. a 4-week plan with hours per week), cross-reference the deliverable with the week in which it is scheduled. Record this as `estimated_effort` (e.g. "Week 3, 2.5 hrs").

**Acceptance criteria inference**: if explicit acceptance criteria are not stated, infer them from the deliverable description. For example, "Target State Architecture Document: a blueprint detailing data flow from Oracle to the AI layer" → infer criteria: covers storage tier, transformation tier, semantic layer, AI/presentation layer, reviewed and signed off by client.

---

### Step 3: Score Against Wire Artifact Keyword Table

For each extracted deliverable, score it against the Wire artifact keyword table:

| Keyword cluster | Artifact | Wire commands available |
|-----------------|----------|------------------------|
| requirements, user stories, functional spec, stakeholder needs | `requirements` | requirements-generate, requirements-validate, requirements-review |
| workshop, facilitation, discovery session, stakeholder interview | `workshops` | workshops-generate, workshops-review |
| stakeholder, org chart, stakeholder map, influence | `stakeholder_map` | stakeholder-map-generate, stakeholder-map-validate, stakeholder-map-review |
| problem definition, problem statement, pitch, shape up | `problem_definition` | problem-definition-generate, problem-definition-review |
| architecture, data model, entity relationship, star schema, dimensional model | `data_model` | data-model-generate, data-model-validate, data-model-review |
| pipeline, data pipeline, ETL, ELT, ingestion, connector, fivetran | `pipeline` | pipeline-design-generate, pipeline-generate, pipeline-validate, pipeline-review |
| dbt, transformation, SQL model, staging, mart, integration layer | `dbt` | dbt-generate, dbt-validate, dbt-review |
| semantic layer, LookML, metrics, business logic, Looker, Power BI semantic | `semantic_layer` | semantic-layer-generate, semantic-layer-validate, semantic-layer-review |
| dashboard, report, visualisation, chart, KPI, BI | `dashboards` | dashboards-generate, dashboards-validate, dashboards-review |
| data quality, testing, dbt test, assertion, SLA | `data_quality` | data-quality-generate, data-quality-validate, data-quality-review |
| deployment, release, CI/CD, cloud run, infrastructure | `deployment` | deployment-generate, deployment-validate, deployment-review |
| training, enablement, knowledge transfer, documentation, runbook | `training` / `documentation` | training-generate, training-validate, training-review |
| mockup, wireframe, prototype, Figma, screen design | `mockups` | mockups-generate, mockups-review |
| conceptual model, entity model, domain model, enterprise data model | `conceptual_model` | conceptual_model-generate, conceptual_model-validate, conceptual_model-review |
| logical model, cardinality, identity resolution, golden record, normalisation, attribution rules, source definitions, grain | `logical_model` | logical_model-generate, logical_model-validate, logical_model-review |
| current state, as-is, appraisal, platform audit, landscape review, source inventory | `current_state_appraisal` | current-state-appraisal-generate, current-state-appraisal-validate, current-state-appraisal-review |
| roadmap, phasing, now next later, delivery plan, initiative prioritisation | `delivery_roadmap` | delivery-roadmap-generate, delivery-roadmap-validate, delivery-roadmap-review |
| findings, playback, readout, discovery deck, sponsor presentation, sign-off session | `findings_playback` | findings-playback-generate, findings-playback-validate, findings-playback-review |
| requirements matrix, MoSCoW, business questions, requirement traceability | `requirements_matrix` | requirements-matrix-generate, requirements-matrix-validate, requirements-matrix-review |
| build plan, sprint plan, capacity, appetite, release schedule | `sprint_plan` | sprint-plan-generate, sprint-plan-validate, sprint-plan-review |
| mml, modality, existing model, model repository, `.mml` | `modality_link` | utils-modality-link |

**Scoring method**:
- Count keyword matches between the deliverable name + description and each cluster
- Normalise: `score = matches / max_matches_in_any_cluster`
- Round to 2 decimal places

**Score interpretation**:

| Score | Meaning | Action |
|-------|---------|--------|
| ≥ 0.70 | Strong match — standard Wire command covers this | Use standard command |
| 0.40–0.69 | Approximate match — standard command is related but workflow may differ | Surface to user with workflow comparison note |
| < 0.40 | No good match — custom spec needed | Generate custom spec |

**Workflow mismatch flag**: for scores in the 0.40–0.69 band, check whether the deliverable description implies a different working mode from the matched command's typical workflow:
- `generate-from-scratch` (Wire's standard mode for most artifacts)
- `audit-and-refine` (reviewing and improving existing work)
- `advisory-output` (producing a decision document or recommendation, not code/data)
- `knowledge-transfer` (structured teaching sessions rather than artifact production)

If the deliverable's implied mode differs from `generate-from-scratch`, set `workflow_mismatch: true` and add a note. This causes `/wire:custom-define` to recommend custom even for mid-band scores.

Record per deliverable:
```
wire_artifact_match: {
  artifact: string | null,       # best-matched artifact name
  score: float,                  # 0.00–1.00
  confidence: "high" | "medium" | "low",
  workflow_mode: string,         # implied mode of the deliverable
  workflow_mismatch: boolean,    # true if mode ≠ generate-from-scratch
  mismatch_note: string | null   # e.g. "Deliverable requires audit of existing PoC; Wire's dbt-generate builds from scratch"
}
```

---

### Step 4: Extract Timeline and Milestones

Scan documents for timeline information:

- Named phases (e.g. "Phase 1 — Discovery", "Week 2 — Architecture Decisions")
- Date ranges (e.g. "commencing May 2026", "complete by 31 May 2026")
- Per-day or per-week task tables (extract as milestones with dates where possible)
- Summary tables like "Week | Hours | Focus"

Return:
```
timeline: {
  start_date: date | null,       # ISO-8601
  end_date: date | null,         # ISO-8601
  duration_weeks: integer | null,
  milestones: [
    { name: string, date: date | null, week_number: integer | null, focus: string | null }
  ]
}
```

If dates are relative ("Week 1", "Late-May"), convert to absolute dates using the engagement start date where known, or leave as `null` with the relative label stored in `focus`.

---

### Step 5: Extract Stakeholders

Scan for named individuals and their roles:

- Attendee lists in meeting notes
- Responsibility matrices (RACI tables)
- "Contact" or "Team" sections in SoWs
- Signature blocks

Return:
```
stakeholders: [
  { name: string, role: string, organisation: string }
]
```

---

### Step 6: Assemble and Return DeliverableList Object

```
DeliverableList {
  source_documents: [{ path, type, title }],
  deliverables: [
    {
      name: string,
      description: string,
      acceptance_criteria: string[],
      estimated_effort: string | null,
      dependencies: string[],
      source_doc: string,
      phase_or_week: string | null,
      wire_artifact_match: {
        artifact: string | null,
        score: float,
        confidence: "high" | "medium" | "low",
        workflow_mode: string,
        workflow_mismatch: boolean,
        mismatch_note: string | null
      }
    }
  ],
  timeline: {
    start_date: date | null,
    end_date: date | null,
    duration_weeks: integer | null,
    milestones: [{ name, date, week_number, focus }]
  },
  stakeholders: [{ name, role, organisation }],
  extraction_notes: string[]   # any ambiguities or assumptions flagged during extraction
}
```

Do **not** write any files. Return the object to the caller (when invoked from another command) or render the standalone output below (when invoked directly).

---

### Step 7: Standalone Output (when invoked directly)

When called via `/wire:utils-doc-analyze`, render:

```markdown
## Document Analysis — [document titles]

**Sources**: [list of documents]
**Deliverables found**: [N]
**Timeline**: [start] → [end] ([N] weeks)
**Stakeholders**: [list of names]

---

### Extracted Deliverables

| # | Deliverable | Description (summary) | Wire Match | Score | Action |
|---|-------------|----------------------|------------|-------|--------|
| 1 | [name] | [one sentence] | [artifact or —] | [0.NN] | [Standard / Approximate ⚠️ / Custom] |
| 2 | ... | | | | |

---

### Timeline Milestones

| Week / Phase | Date | Focus |
|---|---|---|
| [name] | [date or TBC] | [focus] |

---

### Notes

[Any extraction_notes or ambiguities]
```

For deliverables flagged as `workflow_mismatch: true`, show a ⚠️ in the Action column and add a note below the table explaining the mismatch.

---

## Fail-Safe Behaviour

If no deliverables can be extracted (document is too short, unstructured, or not in a recognisable language):

```
⚠️ Document analysis: no deliverables extracted.
  The provided document(s) did not contain identifiable deliverable sections.
  Try providing a SoW, delivery plan, or kick-off notes.
  If the document uses an unusual format, paste the deliverable list directly.
```

Return a `DeliverableList` with `deliverables: []` and a populated `extraction_notes` explaining what was tried.

Execute the complete workflow as specified above.
