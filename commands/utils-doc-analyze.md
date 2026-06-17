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

## Workflow Specification

---
description: Extract deliverables, acceptance criteria, timeline, and stakeholders from SoW or project documents
argument-hint: <file-path-or-url> [<file-path-2> ...]
---

# Document Analysis Utility

## Purpose

Read one or more source documents (SoW, kick-off notes, agreed delivery plan, proposal) and extract a structured `DeliverableList` object containing deliverables with acceptance criteria, timeline milestones, and stakeholders. Each deliverable is scored against the Wire artifact keyword table to determine whether a standard Wire command can handle it or a custom spec is needed.

Called automatically by `/wire:custom-release-define` (Phase 1). Can also be invoked standalone to preview what Wire would extract before committing to a custom release definition.

## Usage

```bash
/wire:utils-doc-analyze path/to/SoW.pdf [path/to/kickoff-notes.md] [path/to/plan.pdf]
```

When called internally from `/wire:custom-release-define`, the caller passes pre-read document content rather than re-reading files.

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

If the deliverable's implied mode differs from `generate-from-scratch`, set `workflow_mismatch: true` and add a note. This causes `/wire:custom-release-define` to recommend custom even for mid-band scores.

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
