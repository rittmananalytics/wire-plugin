---
wire_schema: "1.0"
command: generate
artifact: droughty_qa
domain: droughty
release_types:
  - droughty
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: droughty_introspect
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Run the LangGraph data quality agent against the warehouse and produce a structured quality report
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Droughty QA Command

## Purpose

Run `droughty qa` to execute a LangGraph-based data quality agent against the configured warehouse schemas. The agent queries the live data, interprets results via an LLM, and produces a structured quality report covering null rates, value distributions, anomalies, and referential integrity signals. The report lands in Wire's artifact directory as evidence for discovery, problem definition, and sign-off phases.

**Important**: The QA agent uses the OpenAI API and produces non-deterministic results — output will vary between runs. Treat the report as a starting-point analysis that a consultant should review critically, not an automated pass/fail gate.

## Usage

```bash
/wire:droughty-qa <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete, with an OpenAI API key in `profile.yaml`
- Warehouse accessible with SELECT permissions on the schemas in scope
- LangSmith credentials optional (provide in `profile.yaml` for lineage tracing)

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Check for OpenAI API key

If no OpenAI key:
```
Error: droughty qa requires an OpenAI API key.

Re-run /wire:droughty-setup [release] and provide your OpenAI API key when prompted.
```

### Step 2: Scope Check

For large schemas (> 100 tables), warn:
```
⚠️  [n] tables are in scope. The QA agent will query each table and call OpenAI for interpretation.
This may take 10–30 minutes and will incur OpenAI API costs.

Proceed with all [n] tables, or restrict to specific schemas?
(Type 'all' to proceed, or a comma-separated list of schema names to limit scope)
```

### Step 3: Run droughty qa

```bash
droughty qa \
  --profile-dir ~/.droughty \
  --project-dir .
```

Stream output to the console. The agent produces a Mermaid DAG showing the quality check flow alongside the narrative report.

If the command exits non-zero, surface the full error output. Common failure modes:
- OpenAI rate limit exceeded — retry after a pause
- Warehouse query timeout — check that the role has SELECT on `INFORMATION_SCHEMA`
- LangGraph import error — verify Droughty installation: `pip show droughty`

### Step 4: Copy Report to Artifact Directory

The QA agent writes output to the configured paths. Copy and rename to Wire convention:

```bash
cp [droughty_output_path]/qa_report.* .wire/releases/[release]/artifacts/droughty/qa_report.md
```

### Step 5: Summarise Findings

Read the report and extract a brief summary for the consultant:
- Total checks run
- Issues flagged (by severity if available: critical / warning / info)
- Top 3–5 findings worth highlighting

### Step 6: Update status.md

```yaml
droughty:
  qa:
    status: complete
    checks_run: [n]
    issues_flagged: [n]
    critical_issues: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/qa_report.md
    completed_date: [today]
    review_notes: "Non-deterministic output — consultant review required"
```

### Step 7: Confirm Output

```
## Data Quality Report Generated ✅

[n] checks run — [n] issues flagged ([n] critical, [n] warnings)

Artifact: .wire/releases/[release]/artifacts/droughty/qa_report.md

Review guidance:
- The QA agent uses LLM interpretation — findings are probabilistic, not deterministic.
  Review all flagged issues before citing them in client-facing documents.
- Re-running the command may produce different findings. This is expected.
- Critical issues (if any): [brief list of top critical findings]

This report is available to:
  /wire:problem-definition-generate   — embed quality findings as evidence
  /wire:discovery-analyses-generate   — feed into the Maturity analysis
```

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/qa_report.md`
- Updated `droughty.qa` block in `status.md`
