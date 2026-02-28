---
description: Autonomous end-to-end project execution from SOW
argument-hint: <path-to-sow>
---

# Autonomous end-to-end project execution from SOW

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
description: Autonomous end-to-end project execution from SOW
argument-hint: <path-to-sow>
---

# Wire Autopilot — Autonomous Project Execution

## Purpose

Wire Autopilot takes a Statement of Work (SOW), asks a small set of clarifying questions, then autonomously executes the entire project lifecycle — generating, validating, and self-reviewing every artifact without further human involvement. It produces a complete, demonstrable set of deliverables.

**Safety gates** automatically pause execution before any phase that could affect external systems — activating data connectors, running SQL against databases, or deploying to live environments. At each safety gate, Autopilot presents what it has done so far and asks for explicit confirmation before proceeding.

Autopilot shares the same state files (`status.md`, `execution_log.md`) as the individual commands. A user can switch between Autopilot and manual commands at any point.

## Inputs

**Required**:
- SOW or proposal document path (provided as argument or asked in Phase 1)

**Optional**:
- All other inputs are gathered via clarifying questions in Phase 1

---

# Phase 1: Clarifying Questions

Before going autonomous, Autopilot gathers all necessary context upfront. Ask each question in sequence, waiting for the user's response before proceeding.

## Step 1.1: SOW File Path

If a file path was provided as the command argument, verify the file exists using Glob. If found, proceed to Step 1.2.

If no argument was provided or the file was not found, ask directly in chat:

```
Please provide the path to your Statement of Work (SOW) or proposal document.
(e.g., "path/to/SOW.pdf" or "path/to/proposal.docx")
```

Wait for user response. Verify the file exists. If not found, inform the user and ask again.

Once the SOW is located, read it immediately to extract context for subsequent questions.

## Step 1.2: Infer and Confirm Project Type

After reading the SOW, infer the project type based on its content:
- SOW mentions dashboards + data pipelines + dbt + training/enablement → `full_platform`
- SOW mentions only pipeline/ETL/ingestion work → `pipeline_only`
- SOW mentions dbt/transformations/semantic layer without pipelines → `dbt_development`
- SOW mentions dashboards on an existing platform → `dashboard_extension`
- SOW mentions interactive mockups driving data model, or rapid prototyping → `dashboard_first`
- SOW mentions only training/documentation/enablement → `enablement`

Use `AskUserQuestion` to confirm:

```json
{
  "questions": [{
    "question": "Based on the SOW, this appears to be a [inferred_type] project. Is that correct?",
    "header": "Project Type",
    "options": [
      {"label": "[Inferred type]", "description": "[Description matching inferred type] (Recommended)"},
      {"label": "Full platform", "description": "Complete implementation (pipelines, dbt, BI, enablement)"},
      {"label": "Pipeline only", "description": "Data pipeline development"},
      {"label": "dbt development", "description": "dbt models and semantic layer"},
      {"label": "Dashboard extension", "description": "New dashboards on existing platform"}
    ],
    "multiSelect": false
  }]
}
```

Include all 6 project types as options. Place the inferred type first with "(Recommended)". Map selection to `project_type`.

## Step 1.3: Client Name and Project Name

Ask directly in chat:

```
What is the client name for this project? (e.g., "Acme Corporation")
```

Wait for response. Then ask:

```
What is the project name? (e.g., "acme_marketing_analytics")
```

Wait for response. Derive:
- `client_name`: Display name as provided
- `project_name`: Lowercase, underscores for spaces, no special chars
- `project_id`: Today's date as YYYYMMDD
- `folder_name`: `{project_id}_{project_name}`

Check if a folder with this date prefix already exists using Glob: `.wire/[0-9]*_*/`. If duplicate, append a letter suffix.

## Step 1.4: Jira Integration

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to track this project in Jira?",
    "header": "Jira Tracking",
    "options": [
      {"label": "Create new Jira issues", "description": "Create Epic, Tasks, and Sub-tasks in Jira"},
      {"label": "Link to existing Jira issues", "description": "Search a Jira project for existing issues"},
      {"label": "No, skip Jira", "description": "Track progress in status.md only"}
    ],
    "multiSelect": false
  }]
}
```

If Jira selected, ask in chat:

```
What is the Jira project key? (e.g., DP, ACME, PROJ)
```

Store `jira_project_key` and `jira_mode` ("create" or "link").

## Step 1.5: Dashboard-First Mockup Mode (Conditional)

Only ask if `project_type` is `dashboard_first`:

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Dashboard-first projects typically use Lovable for interactive mockups. For fully autonomous execution, I can generate wireframe mockups instead. Which approach?",
    "header": "Mockup Mode",
    "options": [
      {"label": "Wireframes (autonomous)", "description": "Generate ASCII wireframe mockups — fully autonomous execution (Recommended)"},
      {"label": "Pause for Lovable", "description": "I'll pause at the mockup stage for you to do the Lovable session, then resume"}
    ],
    "multiSelect": false
  }]
}
```

Store as `mockup_mode` ("wireframe" or "pause_for_lovable").

## Step 1.6: Additional Context (Optional)

Ask directly in chat:

```
Is there anything else I should know about this project? For example:
- Specific technologies or platforms (e.g., BigQuery, Snowflake, Looker)
- Naming conventions or coding standards
- Stakeholder preferences
- Existing codebase or infrastructure

Type "no" to skip.
```

Store any additional context as `additional_context`.

## Step 1.7: Confirm, Launch, and Request Permissions

After gathering all inputs, use plan mode to present the execution plan and pre-authorize the bash operations needed for autonomous execution. This prevents Claude Code from prompting for permission at every shell command during Phases 2 and 3.

1. Call `EnterPlanMode`
2. Write a plan file with the following content (replacing placeholders with actual values):

```markdown
# Wire Autopilot Execution Plan

## Configuration
- **Client**: [client_name]
- **Project**: [project_name]
- **Type**: [project_type]
- **SOW**: [sow_path]
- **Jira**: [project_key or "None"]
- **Mockups**: [wireframe/pause_for_lovable or "N/A"]
- **Additional Context**: [summary or "None"]

## Execution Sequence ([count] phases)
[List the numbered artifact sequence for the selected project_type]

## What Autopilot Will Do
For each phase, Autopilot will:
1. **Generate** the artifact from upstream outputs
2. **Validate** against quality criteria (up to 3 retry cycles)
3. **Self-review** for completeness and accuracy (up to 2 review cycles)
4. Update status tracking and execution log

## Safety Gates
These phases will **pause for explicit confirmation** before proceeding:
- **pipeline** — Activates data connectors
- **data_refactor** — Runs dbt against real databases
- **data_quality** — Executes SQL tests against databases
- **deployment** — Deploys to live environments

## Shell Operations Required
Autopilot needs to run shell commands for:
- Git operations (branch creation, status checks, commits)
- Directory and file management (mkdir, cp)
- dbt commands (compile, run, test, seed, deps)
- Data quality validation scripts
- File listing and existence checks
```

3. Call `ExitPlanMode` with the following `allowedPrompts` to pre-authorize shell operations:

```json
{
  "allowedPrompts": [
    {"tool": "Bash", "prompt": "git operations (checkout, branch, status, add, commit, rev-parse, diff)"},
    {"tool": "Bash", "prompt": "create project directories and copy files (mkdir, cp, mv)"},
    {"tool": "Bash", "prompt": "run dbt commands (compile, run, test, seed, deps, debug, ls)"},
    {"tool": "Bash", "prompt": "run data quality checks and validation scripts"},
    {"tool": "Bash", "prompt": "list files and check file existence (ls, find, wc, cat, head, tail)"}
  ]
}
```

4. If the user approves the plan, proceed to Phase 2.
5. If the user rejects or requests changes, return to Step 1.2 to reconfigure.

**Important**: Safety gates (`pipeline`, `data_refactor`, `data_quality`, `deployment`) still pause for explicit confirmation via `AskUserQuestion` regardless of pre-authorized permissions. The permissions only cover mechanical shell operations within each phase, not the decision to proceed with externally-impacting phases.

**Runtime note**: This step uses Claude Code's plan mode (`EnterPlanMode`/`ExitPlanMode`). In Gemini CLI or other runtimes that do not support these tools, skip this step and proceed directly to Phase 2. Gemini CLI users should launch with appropriate permission flags (e.g., `--yolo`) for autonomous execution.

---

# Phase 2: Project Setup

Execute the project setup logic (equivalent to `/wire:dp-new`) non-interactively using the values gathered in Phase 1.

## Step 2.1: Git Branch

1. Run `git rev-parse --abbrev-ref HEAD` to check the current branch
2. If on `main` or `master`, create and switch to `feature/{folder_name}`:
   ```bash
   git checkout -b feature/{folder_name}
   ```
3. If branch already exists, switch to it: `git checkout feature/{folder_name}`
4. Store `branch_name` for the final summary

## Step 2.2: Create Folder Structure

```bash
mkdir -p .wire/{folder_name}/{artifacts,requirements,design,dev,test,deploy,enablement}
```

## Step 2.3: Copy SOW

```bash
cp {sow_path} .wire/{folder_name}/artifacts/
```

## Step 2.4: Create Status File

Read the template from `TEMPLATES/status-template.md` and replace placeholders:
- `{{PROJECT_ID}}` → project_id
- `{{PROJECT_NAME}}` → project_name
- `{{PROJECT_TYPE}}` → project_type
- `{{CLIENT_NAME}}` → client_name
- `{{CREATED_DATE}}` → today's date (YYYY-MM-DD)
- `{{LAST_UPDATED}}` → today's date (YYYY-MM-DD)

Set artifact scope based on project_type (see Artifact Scope Reference below).
Write to `.wire/{folder_name}/status.md`.

## Step 2.5: Jira Setup (if opted in)

Follow the Jira workflow in `dp/utils/jira_create.md`:
- If `jira_mode` is "create": Create Epic → Task → Sub-task hierarchy
- If `jira_mode` is "link": Search existing issues, link them
- Update status.md with issue keys
- If Jira fails, note the failure and continue

## Step 2.6: Initialize Autopilot Checkpoint

Create `.wire/{folder_name}/autopilot_checkpoint.md`:

```markdown
# Autopilot Checkpoint

## Configuration
- Project: [project_name]
- Client: [client_name]
- Type: [project_type]
- SOW: [sow_filename]
- Mockup Mode: [wireframe/pause_for_lovable/N/A]
- Jira: [project_key or "None"]

## SOW Summary
[Write a condensed 500-word summary of the SOW covering: business context, deliverables, data sources, key stakeholders, timeline, and technology preferences]

## Completed Phases
(none yet)

## Current Phase
project_setup: complete

## Key Context
- Data sources: [list from SOW]
- Key entities: [list from SOW]
- Deliverables: [list from SOW]
- Technologies: [from SOW + additional_context]

## Decisions Made
- Project type: [project_type]
- Mockup mode: [if applicable]
- Data mode: [real/mock if applicable]

## Blocked Artifacts
(none)
```

## Step 2.7: Log Project Creation

Append to `.wire/{folder_name}/execution_log.md`:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| [timestamp] | /wire:dp-autopilot | created | Project created (type: [project_type], client: [client_name]) |
```

Output:
```
--- Project Setup Complete ---
Folder: .wire/{folder_name}/
Branch: {branch_name}
Type: {project_type}
Artifacts: {count} phases to execute
Beginning autonomous execution...
---
```

---

# Phase 3: Autonomous Execution Loop

## Artifact Sequence Reference

Process artifacts in the order specified by the project type:

**full_platform:**
1. requirements
2. workshops
3. conceptual_model
4. pipeline_design
5. data_model
6. mockups
7. pipeline
8. dbt
9. semantic_layer
10. dashboards
11. data_quality
12. uat
13. deployment
14. training
15. documentation

**pipeline_only:**
1. requirements
2. pipeline_design
3. pipeline
4. data_quality
5. deployment

**dbt_development:**
1. requirements
2. data_model
3. dbt
4. semantic_layer
5. data_quality
6. deployment

**dashboard_extension:**
1. requirements
2. mockups
3. dashboards
4. training

**dashboard_first:**
1. requirements
2. mockups
3. viz_catalog
4. data_model
5. seed_data
6. dbt
7. semantic_layer
8. dashboards
9. data_refactor
10. data_quality
11. uat
12. deployment
13. training
14. documentation

**enablement:**
1. training
2. documentation

## Safety Gates

Certain artifacts, when executed for real, can touch external systems — activating data connectors, running SQL against production databases, or deploying to live environments. Before processing any of these artifacts, Autopilot **must pause** and request explicit user confirmation.

**Safety-gated artifacts:**

| Artifact | Risk | Warning |
|----------|------|---------|
| `pipeline` | Activates real data connectors (Fivetran, Airbyte) that begin replicating from production sources | "This phase will generate pipeline configuration. When activated, this could start replicating data from your production source systems. Please confirm the target environment and connector credentials are correct before proceeding." |
| `data_refactor` | Modifies dbt source definitions to point to real client data; validate step runs dbt against a real database | "This phase will switch dbt models from seed data to real client data sources. The validate step will run `dbt compile` and potentially `dbt run` against your database. Please confirm the database connection is pointing to the correct (non-production) environment." |
| `data_quality` | Runs SQL-based data quality tests against the database | "This phase will run data quality tests that execute SQL queries against your database. Please confirm the target database connection is correct." |
| `deployment` | Creates and potentially executes deployment scripts against live environments | "This phase will generate deployment runbooks and scripts. Executing these would deploy changes to a live environment. Please confirm you are ready to proceed with deployment planning." |

**Safety gate behavior:**

When the execution loop reaches a safety-gated artifact, it MUST:

1. Pause execution
2. Present a summary of all completed phases so far (from the checkpoint)
3. Display the risk-specific warning message from the table above
4. Use `AskUserQuestion` to get explicit confirmation:

```json
{
  "questions": [{
    "question": "[Warning message for this artifact]. How would you like to proceed?",
    "header": "Safety Gate",
    "options": [
      {"label": "Proceed", "description": "Continue with this phase — I have verified the target environment"},
      {"label": "Review first", "description": "Pause here so I can review the artifacts generated so far before continuing"},
      {"label": "Stop here", "description": "End Autopilot execution — I will continue manually from this point"}
    ],
    "multiSelect": false
  }]
}
```

**Handling responses:**
- **Proceed**: Continue with the artifact's generate/validate/review cycle
- **Review first**: Output a summary of all files generated so far with their paths, then wait for the user to say "continue" before proceeding
- **Stop here**: Output the final summary (Phase 4) with current progress and exit. The user can resume later with manual commands or re-invoke Autopilot.

## Execution Loop

For each artifact in the sequence:

1. **Check status**: Read `.wire/{folder_name}/status.md`. If this artifact's generate state is already `complete` and review state is `approved`, skip it.

2. **Safety gate check**: If this artifact is in the safety-gated list (`pipeline`, `data_refactor`, `data_quality`, `deployment`), execute the Safety Gate protocol above before proceeding. If the user chooses "Stop here", jump to Phase 4 (Final Summary).

3. **Generate**: Execute the generate logic for this artifact (see Per-Artifact Blocks below).
   - Update status.md: set `generate: complete`, `generated_date: [today]`
   - Log to execution_log.md

4. **Validate** (if the artifact has a validate step): Execute validation checks.
   - If validation **passes**: Update status.md: `validate: pass`
   - If validation **fails**:
     - Re-generate the artifact incorporating the specific validation failures
     - Re-validate
     - Maximum 3 generate-validate cycles
     - If still failing after 3 cycles, set `validate: fail`, log as blocked, continue to next artifact
   - Log to execution_log.md

5. **Self-Review**: Execute the self-review for this artifact (see Self-Review Criteria below).
   - If self-review **approves**: Update status.md: `review: approved`, `reviewed_by: "Wire Autopilot (self-review)"`, `reviewed_date: [today]`
   - If self-review **finds issues**:
     - Re-generate incorporating review feedback
     - Re-validate
     - Re-review
     - Maximum 2 review cycles
     - If still failing, set `review: changes_requested`, add feedback to status.md, log as blocked
   - Log to execution_log.md

6. **Jira sync** (if configured): Follow `dp/utils/jira_sync.md` to update Jira. If Jira fails, continue.

7. **Update checkpoint**: Update `.wire/{folder_name}/autopilot_checkpoint.md` with:
   - Move this artifact to "Completed Phases" with a brief summary
   - Update "Current Phase" to the next artifact
   - Add any key context discovered during this phase to "Key Context"
   - Add any decisions made to "Decisions Made"

8. **Report progress**:
   ```
   --- Phase Complete: [artifact_name] ---
   Status: [approved/blocked]
   Files: [list of created/updated files]
   Progress: [N/total] phases complete
   Next: [next_artifact_name]
   ---
   ```

## Resumption Protocol

If this command is invoked on a project that already has artifacts in progress or complete:

1. Read `.wire/{folder_name}/status.md` to identify completed phases
2. Read `.wire/{folder_name}/autopilot_checkpoint.md` for compressed context from prior phases
3. Identify the first incomplete artifact in the project-type sequence
4. Resume execution from that point
5. Do NOT re-generate already-completed and approved artifacts

---

# Per-Artifact Execution Blocks

Each block describes the condensed generate, validate, and self-review logic for one artifact type.

---

## ARTIFACT: requirements

### Generate

**Input**: SOW/documents in `.wire/{folder_name}/artifacts/`
**Output**: `.wire/{folder_name}/requirements/requirements_specification.md`

**Process**:
1. Read all documents in `artifacts/` (PDFs, markdown, etc.)
2. Extract and structure into a requirements specification with these sections:
   - **Executive Summary**: 2-3 paragraph overview
   - **Business Context**: Client background, problem statement, strategic goals, success criteria
   - **Stakeholders**: Table with name, role, department, involvement level
   - **Functional Requirements**: Numbered list (FR-001, FR-002, etc.) with description and acceptance criteria
   - **Non-Functional Requirements**: Performance, security, availability, scalability
   - **Data Requirements**: Source systems table (name, type, owner, volume, refresh frequency)
   - **Technical Requirements**: Platform, tools, environments, constraints
   - **Deliverables**: Table mapping SOW deliverables to Wire artifacts with acceptance criteria
   - **Timeline**: Milestones with dates
   - **Assumptions and Dependencies**
   - **Risks and Mitigations**: Table with risk, impact, likelihood, mitigation
   - **Scope Management**: In-scope, out-of-scope, change process
3. Write to `requirements/requirements_specification.md`

### Validate

**Checks** (all must pass):
- [ ] Executive summary present and non-empty
- [ ] At least 3 functional requirements with acceptance criteria
- [ ] Non-functional requirements defined
- [ ] All data sources identified with owners
- [ ] All SOW deliverables documented
- [ ] Each deliverable has clear acceptance criteria
- [ ] Timeline with milestones
- [ ] Stakeholder roles defined
- [ ] Out-of-scope items documented
- [ ] Dependencies and assumptions documented

### Self-Review

**Criteria**:
1. **SOW Traceability**: Every deliverable in the SOW maps to at least one requirement
2. **Completeness**: No SOW sections were overlooked or skipped
3. **No Fabrication**: All requirements are traceable to the SOW — nothing invented
4. **Clarity**: Each functional requirement has testable acceptance criteria
5. **Consistency**: Requirements do not contradict each other

---

## ARTIFACT: workshops

### Generate

**Input**: `requirements/requirements_specification.md`
**Output**: `design/workshop_agenda.md`, `design/workshop_decision_matrix.md`

**Process**:
1. Parse requirements for `[NEEDS CLARIFICATION]` markers, TBD items, ambiguities
2. Categorize by topic: requirements, data, technical, timeline, scope
3. Generate workshop agenda with parts: requirements clarification (45 min), data source details (30 min), technical approach (30 min), wrap-up (15 min)
4. Create decision matrix template: topic, options, decision, rationale, owner

### Validate

No specific validation checks — workshops have no validate step.

### Self-Review

**Criteria**:
1. All ambiguities from requirements are addressed in workshop topics
2. Workshop agenda covers all TBD items
3. Decision matrix includes all open questions
4. **Autopilot Decision**: Since no actual workshop is conducted, auto-approve the workshop materials as reference documentation. Mark as `review: approved`, `reviewed_by: "Wire Autopilot (self-review)"`, with note: "Workshop materials generated as reference — no workshop conducted in Autopilot mode"

---

## ARTIFACT: conceptual_model

### Generate

**Input**: `requirements/requirements_specification.md`, `artifacts/` for source schemas
**Output**: `design/conceptual_model.md`

**Process**:
1. Extract business entities from requirements: nouns, deliverables, reporting subjects
2. For each entity: name (PascalCase), description, key attributes (3-6), approximate volume
3. Define relationships with verb phrases and cardinality
4. Generate Mermaid erDiagram (entity-only, no column definitions in the diagram)
5. Include relationship narratives explaining business meaning
6. Section for entities out of scope
7. Section for open questions

### Validate

**Checks**:
- [ ] Every business noun in Functional Requirements is represented or explicitly out-of-scope
- [ ] Every relationship has valid cardinality markers at both ends
- [ ] Every relationship has a quoted label
- [ ] No `{}` column definitions in erDiagram (entity-only format)
- [ ] Mermaid syntax valid (no unclosed quotes, no duplicate definitions)
- [ ] All entity names are singular PascalCase
- [ ] Each entity has description and at least 2 key business attributes
- [ ] At least one sentence per relationship narrative
- [ ] Out-of-scope section populated if entities excluded

### Self-Review

**Criteria**:
1. **Requirements Coverage**: All business entities from functional requirements are present
2. **Relationship Accuracy**: Cardinalities reflect real business rules (e.g., a Customer has many Orders, not vice versa)
3. **No Orphans**: Every entity participates in at least one relationship
4. **SOW Alignment**: Model scope matches SOW scope — no entities beyond what the SOW describes
5. **Domain Language**: Entity names use client terminology from the SOW

---

## ARTIFACT: pipeline_design

### Generate

**Input**: `requirements/requirements_specification.md`, `design/conceptual_model.md`, `artifacts/` for schemas
**Output**: `design/pipeline_architecture.md`

**Process**:
1. Analyze each source system: technology, schema, volume, availability, sensitivity
2. Cross-reference against conceptual model entities — flag data gaps
3. Define replication strategy per source (full refresh, incremental, CDC, API, batch)
4. Specify pipeline architecture: landing/raw naming, staging layer (`stg_<source>__<entity>`), warehouse layer, error handling, scheduling
5. Generate Mermaid Data Flow Diagram: sources → ingestion → staging → warehouse → BI
6. Document design decisions with context and rationale
7. Include technology stack table and security/governance section
8. **Autonomous Decision**: Where multiple scenarios exist (e.g., replication strategy), choose the most practical option based on SOW constraints and document the rationale

### Validate

**Checks**:
- [ ] Every source system from requirements appears in source analysis
- [ ] Every source has a replication method specified
- [ ] All staging models follow `stg_<source>__<entity>` naming
- [ ] All warehouse models follow `<entity>_fct` or `<entity>_dim` naming
- [ ] Error handling specified
- [ ] Scheduling defined with refresh cadences
- [ ] Technology stack complete
- [ ] DFD present with valid Mermaid syntax
- [ ] Every source system appears in DFD
- [ ] DFD uses subgraph blocks for layers
- [ ] PII handling addressed

### Self-Review

**Criteria**:
1. **Source Coverage**: All data sources from requirements are addressed
2. **Architecture Coherence**: Pipeline flows logically from source to warehouse
3. **Design Decisions Justified**: Each choice has a documented rationale
4. **DFD Completeness**: Diagram matches the written architecture
5. **Feasibility**: Chosen technologies and strategies are compatible with SOW constraints

---

## ARTIFACT: data_model

### Generate

**Input**:
- Default: `requirements/requirements_specification.md`, `design/conceptual_model.md`, `design/pipeline_architecture.md`
- Dashboard-first: `requirements/requirements_specification.md`, `design/visualization_catalog.md`
**Output**: `design/data_model_specification.md`, (dashboard_first also: `design/source_tables_ddl.sql`, `design/target_warehouse_ddl.sql`)

**Process**:
1. Define source definitions with freshness thresholds
2. Design staging models: `stg_<source>__<entity>`, view materialization, surrogate key composition, column renames, derived columns, tests
3. Design integration models: `int__<subject>__<description>`, ephemeral/view, for cross-system joins
4. Design warehouse models:
   - Fact tables: `<entity>_fct`, grain, surrogate key, foreign keys, measures
   - Dimension tables: `<entity>_dim`, SCD Type 1 or 2
   - Aggregates: `<subject>_<grain>`, pre-aggregated measures
5. Specify seed files for configurable business logic
6. Generate physical ERD as Mermaid erDiagram with all warehouse models, columns, PKs, FKs
7. Document cross-system join keys
8. Define dbt test coverage plan
9. **For dashboard_first**: Additionally generate `source_tables_ddl.sql` (expected source schema) and `target_warehouse_ddl.sql` (dimensional model DDL)

### Validate

**Checks**:
- [ ] Staging follows `stg_<source>__<entity>` with double underscore
- [ ] Warehouse facts use `<entity>_fct`, dimensions use `<entity>_dim`
- [ ] Surrogate keys follow `<entity>_pk`, foreign keys follow `<entity>_fk`
- [ ] All columns in snake_case
- [ ] Every conceptual entity appears as a warehouse model
- [ ] Every model has a grain statement
- [ ] Every model has a surrogate key
- [ ] Every FK references a defined PK in another model
- [ ] Minimum tests: `not_null(pk)` and `unique(pk)` on all models
- [ ] FK columns have `relationships` tests
- [ ] ERD present with valid Mermaid erDiagram syntax
- [ ] Column names in ERD match model specs
- [ ] PKs marked `PK`, FKs marked `FK` in ERD

### Self-Review

**Criteria**:
1. **Entity Coverage**: All conceptual model entities are represented in the physical model
2. **Grain Correctness**: Each fact table has a clearly defined, appropriate grain
3. **FK/PK Consistency**: All foreign key references resolve to valid primary keys
4. **Naming Conventions**: Consistent naming throughout (no mixed conventions)
5. **Test Coverage**: Adequate tests defined for data integrity
6. **ERD Accuracy**: ERD matches the written specifications

---

## ARTIFACT: mockups

### Generate

**Input**: `requirements/requirements_specification.md`
**Output**: `design/mockups/` directory with mockup files + `design/mockups/mockups_index.md`

**Process** (Wireframe Mode — used in Autopilot):
1. Identify dashboards/screens from requirements
2. For each dashboard, generate an ASCII wireframe mockup showing layout, chart placeholders, filter bar, data labels
3. Create `mockup_[dashboard_name].md` for each with: title, purpose, audience, wireframe, data requirements table, filters, interactions
4. Create `mockups_index.md` linking all mockups
5. Save all files to `design/mockups/`

**If dashboard_first AND mockup_mode is "pause_for_lovable"**:
1. Generate a Lovable session brief from requirements: use case, key questions, suggested dashboard pages, data domain context
2. Construct the getmock.rittmananalytics.com URL with URL-encoded use case
3. Present the URL and instructions to the user
4. Output: "Autopilot paused. Please complete the Lovable session and save the following files to `.wire/{folder_name}/design/`:"
   - `dashboard_visualization_catalog.csv`
   - `dashboard_spec.md`
5. Wait for user input to confirm files are ready
6. Verify both files exist and have expected content
7. Record Lovable URL in status.md

### Validate

No specific validation checks for mockups.

### Self-Review

**Criteria**:
1. **Requirements Coverage**: Every functional requirement that implies a visualization is addressed by at least one mockup
2. **Data Traceability**: Each chart references specific measures and dimensions
3. **Layout Clarity**: Wireframes are readable and show logical dashboard organization
4. **Audience Appropriateness**: Executive dashboards differ from operational dashboards

---

## ARTIFACT: viz_catalog (dashboard_first only)

### Generate

**Input**: `design/dashboard_visualization_catalog.csv`, `design/dashboard_spec.md`, `requirements/requirements_specification.md`
**Output**: `design/visualization_catalog.md`

**Process**:
1. Parse CSV: map dashboard page → visualization → chart type → measures/dimensions
2. Parse dashboard_spec.md: extract purposes, layout, filters, interactions
3. Cross-reference with requirements for coverage analysis
4. Generate structured catalog:
   - Summary: dashboard count, viz count, unique measures, dimensions, coverage %
   - Per-dashboard: purpose, visualization table (name, type, measures, dimensions, requirement links)
   - Measures index: measure name, used in (viz list), frequency
   - Dimensions index: dimension name, used in (viz list), frequency
   - Requirements coverage: requirement, addressed by (viz list), status
   - Gaps and suggestions

### Validate

No specific validate step for viz_catalog.

### Self-Review

**Criteria**:
1. **CSV Fidelity**: All rows from the CSV are represented in the catalog
2. **Requirements Coverage**: Coverage percentage is reasonable (>80% of relevant requirements addressed)
3. **Measure/Dimension Consistency**: Names are consistent across visualizations
4. **Gaps Identified**: Any uncovered requirements are called out

---

## ARTIFACT: seed_data (dashboard_first only)

### Generate

**Input**: `design/source_tables_ddl.sql`, `design/target_warehouse_ddl.sql`, `design/visualization_catalog.md` (if exists)
**Output**: `dev/seed_data/*.csv` files + `dev/seed_data/README.md`

**Process**:
1. Parse both DDL files: extract table names, columns, types, PKs, FKs
2. Read visualization catalog to identify which measures need non-zero values
3. Build dependency graph: dimensions before facts
4. For each source table in dependency order, generate CSV:
   - Header row = column names from DDL
   - Dimension tables: 10-50 rows with realistic values
   - Fact tables: 100-500 rows with varied distributions
   - Maintain referential integrity: all FK values exist in parent tables
   - No duplicate PKs, no NULLs in NOT NULL columns
   - Consistent date format (YYYY-MM-DD)
   - Domain-appropriate values (not lorem ipsum)
5. Create README.md: overview, files table, dependency order, FK relationships, dbt seed config snippet

### Validate

**Checks**:
- [ ] Every CSV parses without errors
- [ ] Header rows match expected columns from DDL
- [ ] No empty files (at least 1 data row)
- [ ] No duplicate values in PK columns
- [ ] No NULL values in PK columns
- [ ] Every FK value exists in referenced parent table PK
- [ ] Date columns contain valid dates (YYYY-MM-DD)
- [ ] Numeric columns contain valid numbers
- [ ] No NULL values in NOT NULL columns
- [ ] Fact tables have variation in measure columns

### Self-Review

**Criteria**:
1. **Referential Integrity**: All FK→PK relationships hold
2. **Realistic Data**: Values are domain-appropriate and varied
3. **Sufficient Volume**: Enough rows for meaningful dashboard visualizations
4. **DDL Alignment**: Column names and types match the DDL specifications

---

## ARTIFACT: pipeline

### Generate

**Input**: `requirements/requirements_specification.md`, `design/pipeline_architecture.md`
**Output**: Pipeline code and configuration in `dev/pipeline/`

**Process**:
1. Read pipeline architecture for source definitions and replication strategy
2. Generate pipeline configuration for the specified technology:
   - Fivetran: connector configuration files
   - Airbyte: connection specifications
   - Custom: Python scripts, scheduling config
3. Generate orchestration config (Airflow DAGs, Cloud Composer, cron)
4. Generate error handling and monitoring setup
5. Create pipeline documentation

### Validate

**Checks**:
- [ ] Pipeline configuration files are syntactically valid
- [ ] All source systems from pipeline_design are addressed
- [ ] Scheduling cadences match pipeline_design specifications
- [ ] Error handling is configured

### Self-Review

**Criteria**:
1. **Architecture Alignment**: Pipeline code matches the pipeline design
2. **Source Coverage**: All sources from the design are implemented
3. **Error Handling**: Failure scenarios are covered
4. **Documentation**: Pipeline is documented for operations

---

## ARTIFACT: dbt

### Generate

**Input**: `design/data_model_specification.md`, dbt conventions (if found)
**Output**: dbt project directory structure with models, tests, docs

**Process**:
1. Check for project-specific dbt conventions file
2. Determine dbt project location (detect existing or create new)
3. Generate staging models:
   - `stg_<source>__<entity>.sql` — source() calls, surrogate keys, renames, filters
   - `_sources.yml` per source system with freshness
   - Materialized as view
4. Generate integration models (if needed):
   - `int__<entity>__<description>.sql` — cross-system joins, complex logic
   - Ephemeral or view materialization
5. Generate warehouse models:
   - `<entity>_dim.sql` — dimensions with SCD handling
   - `<entity>_fct.sql` — facts with measures, FKs
   - `<entity>_agg.sql` — pre-aggregated tables (if needed)
   - Table materialization
6. Generate schema.yml files with:
   - Model descriptions
   - Column descriptions in business terms
   - Tests: unique/not_null on PKs, relationships on FKs, accepted_values on enums
7. Generate dbt_project.yml (if new project)
8. **For dashboard_first with seed data**: Generate seed-based source definitions using `ref('seed_name')` instead of `source()` in staging models. Include seed config in dbt_project.yml.
9. Create `dev/dbt_models_summary.md` with model counts, test coverage

**SQL Standards**:
- 4-space indentation, max 80 char lines
- All CTEs from refs/sources prefixed with `s_`
- Final CTE always named `final`, ending with `select * from final`
- Lowercase field names and functions
- Explicit join types (inner join, left join)
- Field ordering: keys, dates, attributes, metrics, metadata

### Validate

**Checks — Naming**:
- [ ] Staging: `stg_<source>__<entity>.sql`
- [ ] Integration: `int__<object>.sql` or `int__<object>__<action>.sql`
- [ ] Dimensions: `<object>_dim.sql`
- [ ] Facts: `<object>_fct.sql`
- [ ] PKs: `<object>_pk`, FKs: `<referenced_object>_fk`
- [ ] Timestamps: `<event>_ts`, Booleans: `is_`/`has_`
- [ ] All snake_case, singular names

**Checks — SQL Structure**:
- [ ] All ref/source in top CTEs with `s_` prefix
- [ ] Final CTE present with `select * from final`
- [ ] 4-space indentation
- [ ] Explicit join types (not bare `join`)
- [ ] `as` keyword used for all aliases

**Checks — Testing**:
- [ ] Every model appears in schema.yml
- [ ] Every PK has `unique` and `not_null` tests
- [ ] FK columns have `relationships` tests
- [ ] Enum/status fields have `accepted_values` tests

**Checks — Documentation**:
- [ ] All staging models and columns documented
- [ ] All warehouse models and columns documented
- [ ] Column descriptions use business terminology

**Checks — Dependencies**:
- [ ] All ref() references point to existing models
- [ ] No circular dependencies
- [ ] Proper layer order (staging → integration → warehouse)

### Self-Review

**Criteria**:
1. **Model Coverage**: Every model in the data_model specification has a corresponding SQL file
2. **SQL Quality**: Code follows conventions, CTEs are well-structured
3. **Test Coverage**: All PKs, FKs, and critical fields have tests
4. **Documentation**: All models and columns have business-friendly descriptions
5. **Seed/Source Correctness**: Source definitions match the data sources (or seeds for dashboard_first)

---

## ARTIFACT: semantic_layer

### Generate

**Input**: `requirements/requirements_specification.md`, `design/data_model_specification.md`, dbt schema.yml files
**Output**: LookML view files, model file updates, validation summary

**Process**:
1. Read requirements to understand business goals and measures
2. Examine existing LookML project structure (if any) for conventions
3. Map data types: STRING→string, INT64→number, DATE→time, TIMESTAMP→time, BOOLEAN→yesno
4. For each warehouse model, create a LookML view:
   - Primary key (hidden: yes)
   - Dimensions: string, time (dimension_group), numeric, yesno, derived
   - Measures: count, sum, average, count_distinct with value_format_name
   - Drill fields for exploration
   - Groups and labels for organization
5. Define explores with joins: relationship, join type, sql_on
6. Validate syntax: balanced braces, `;;` after SQL, type on all dimensions
7. Update model file with new explores
8. Create LookML summary document

### Validate

**Checks**:
- [ ] Balanced braces in all files
- [ ] SQL blocks end with `;;`
- [ ] Every dimension has `type:` specified
- [ ] All use `${TABLE}.column` syntax
- [ ] Primary keys defined with `primary_key: yes`
- [ ] Labels are business-friendly (not raw column names)
- [ ] Explores have `relationship:` defined
- [ ] Join SQL ON conditions reference correct fields
- [ ] Numeric measures have `value_format_name`
- [ ] Dates use `dimension_group` with timeframes

### Self-Review

**Criteria**:
1. **Model Coverage**: All warehouse models are represented as LookML views
2. **Measure Completeness**: All measures from requirements/data model are exposed
3. **Business Language**: Labels and descriptions use business terminology
4. **Explore Design**: Joins correctly reflect the data model relationships
5. **Syntax Validity**: All files would parse without errors

---

## ARTIFACT: dashboards

### Generate

**Input**: `requirements/requirements_specification.md`, `design/mockups/` or `design/visualization_catalog.md`, semantic layer definitions
**Output**: Dashboard specification files in `dev/dashboards/`

**Process**:
1. Read mockups/visualization catalog to identify all dashboards and their visualizations
2. Map each visualization to semantic layer fields (explores, dimensions, measures)
3. Generate LookML dashboard files (or Looker dashboard specs) for each dashboard:
   - Dashboard title, description
   - Tiles/elements with: type, explore, fields, filters, sorts, limits
   - Dashboard filters with field references
   - Layout positioning
4. Generate dashboard documentation: purpose, audience, key metrics, navigation guide
5. Create dashboard summary with tile counts and field references

### Validate

**Checks**:
- [ ] Every mockup/catalog visualization has a corresponding dashboard element
- [ ] All field references exist in the semantic layer
- [ ] Dashboard filters reference valid dimensions
- [ ] Layout is complete (no overlapping or missing tiles)

### Self-Review

**Criteria**:
1. **Visualization Coverage**: All mockup/catalog visualizations are implemented
2. **Field Accuracy**: All field references resolve to semantic layer definitions
3. **Requirements Alignment**: Dashboards address the functional requirements
4. **Usability**: Logical dashboard organization with appropriate filters

---

## ARTIFACT: data_refactor (dashboard_first only)

### Generate

**Input**: `design/source_tables_ddl.sql` (seed version), real data access or revised DDL
**Output**: `design/data_refactor_plan.md`, updated dbt files

**Process**:
1. **Autonomous Decision**: Since Autopilot may not have real database access, generate the refactoring plan based on the seed DDL and document what changes would be needed when real data is available
2. Compare seed-based DDL against expected real source schemas (from SOW/requirements)
3. Generate refactoring plan:
   - Schema comparison summary
   - Table-by-table analysis: seed columns vs expected real columns
   - dbt configuration changes needed
   - Staging model updates: `ref('seed')` → `source('real')`
   - Estimated impact
4. If real data access is available, execute the refactoring:
   - Update `_sources.yml` to point to real data
   - Change `ref('seed_name')` to `source('source_name', 'table_name')` in staging models
   - Update column references where names differ
   - Update dbt_project.yml (remove seed config)
   - Keep seed files as reference
5. If no real data access, note that refactoring plan is ready but execution requires real data

### Validate

**Checks** (if refactoring was executed):
- [ ] All staging models reference `source()` instead of `ref()` for data tables
- [ ] `_sources.yml` points to correct real data tables
- [ ] dbt_project.yml updated to remove seed config for source tables
- [ ] All ref() and source() calls resolve correctly
- [ ] Seed files are preserved (not deleted)

**Checks** (if plan only):
- [ ] Refactoring plan covers all seed-to-source mappings
- [ ] Column mapping differences are documented
- [ ] Impact assessment is complete

### Self-Review

**Criteria**:
1. **Mapping Completeness**: Every seed table has a corresponding real source mapping
2. **Plan Clarity**: Steps are clear enough for manual execution if needed
3. **No Regressions**: Warehouse models and tests would continue to work after refactoring
4. **Seed Preservation**: Seed files are explicitly preserved as reference

---

## ARTIFACT: data_quality

### Generate

**Input**: `requirements/requirements_specification.md`, dbt models, data model specification
**Output**: Data quality test files and monitoring configuration in `test/`

**Process**:
1. Read requirements for data quality expectations
2. Analyze dbt models for testable assertions
3. Generate data quality tests:
   - Freshness tests per source
   - Row count tests (minimum expected rows)
   - Business rule tests (e.g., revenue > 0, dates in valid range)
   - Cross-table consistency tests (FK integrity)
   - Anomaly detection rules (sudden changes in volume or values)
4. Generate monitoring configuration
5. Create data quality documentation

### Validate

**Checks**:
- [ ] Tests cover all critical data quality dimensions: freshness, completeness, consistency, accuracy
- [ ] All source systems have freshness tests
- [ ] Business rules from requirements are codified as tests
- [ ] Test documentation is complete

### Self-Review

**Criteria**:
1. **Requirements Coverage**: Data quality requirements from the SOW are addressed
2. **Test Adequacy**: Critical business rules have corresponding tests
3. **Monitoring**: Alert thresholds are reasonable
4. **Documentation**: Test purposes are clearly documented

---

## ARTIFACT: uat

### Generate

**Input**: `requirements/requirements_specification.md`, dashboard specs, dbt models
**Output**: `test/uat_plan.md`

**Process**:
1. Read requirements and deliverables with acceptance criteria
2. For each deliverable, generate test scenarios:
   - Test case ID, description
   - Prerequisites
   - Test steps (specific, executable)
   - Expected results
   - Pass/fail criteria
3. Create UAT plan document with:
   - Overview and scope
   - Test environment setup
   - Test cases grouped by deliverable
   - Sign-off template
   - Issue tracking process

### Validate

No specific validate checks for UAT.

### Self-Review

**Criteria**:
1. **Deliverable Coverage**: Every SOW deliverable has at least one test case
2. **Testability**: Each test case has clear, measurable pass/fail criteria
3. **Completeness**: UAT covers functional, non-functional, and integration aspects

---

## ARTIFACT: deployment

### Generate

**Input**: All completed development artifacts, requirements
**Output**: `deploy/deployment_runbook.md`, deployment scripts

**Process**:
1. Identify all components to deploy: dbt models, pipelines, dashboards, semantic layer
2. Generate deployment runbook:
   - Pre-deployment checklist
   - Deployment steps in order (with commands)
   - Post-deployment verification
   - Rollback procedure
   - Communication plan
3. Generate deployment scripts (if applicable)
4. Create production configuration files

### Validate

**Checks**:
- [ ] All project components are covered in deployment plan
- [ ] Rollback procedure is defined
- [ ] Pre/post-deployment verification steps are clear
- [ ] Deployment order handles dependencies

### Self-Review

**Criteria**:
1. **Component Coverage**: All deliverables are included in the deployment plan
2. **Rollback Safety**: Rollback procedure would restore previous state
3. **Verification**: Post-deployment checks would confirm successful deployment
4. **Clarity**: Steps are specific enough for someone unfamiliar to execute

---

## ARTIFACT: training

### Generate

**Input**: `requirements/requirements_specification.md`, dbt models, dashboards, semantic layer
**Output**: Training materials in `enablement/`:
- `training_[type]_session_plan.md`
- `training_[type]_slides.md` (Marp format)
- `training_[type]_exercises.md`
- `training_[type]_quick_reference.md`
- `training_delivery_checklist.md`

**Process**:
1. Determine training types from SOW deliverables:
   - Data team enablement: dbt structure, adding models, running/testing
   - BI developer training: semantic layer, dashboard development
   - End user training: dashboard navigation, interpreting data
   - Admin training: configuration, monitoring, troubleshooting
2. For each training type, generate:
   - **Session plan**: Learning objectives, prerequisites, agenda (4-5 parts), exercises, assessment criteria
   - **Slides**: Marp markdown format with introduction, core topics, exercises, Q&A
   - **Exercises**: Hands-on workbook with scenarios, steps, expected outcomes, solutions
   - **Quick reference**: Common tasks, step-by-step instructions, troubleshooting table
3. Create delivery checklist: pre-session, during session, post-session tasks

### Validate

**Checks**:
- [ ] All deliverable-related training types are covered
- [ ] Session plans have learning objectives and exercises
- [ ] Exercises reference actual project artifacts (real model names, dashboard names)
- [ ] Quick reference covers common tasks

### Self-Review

**Criteria**:
1. **Audience Appropriateness**: Content level matches the target audience
2. **Coverage**: All delivered features are covered in training
3. **Practical Exercises**: Exercises use real project artifacts and scenarios
4. **Completeness**: All required training types from SOW are included

---

## ARTIFACT: documentation

### Generate

**Input**: All project artifacts (requirements, design, development, deployment)
**Output**: Documentation in `enablement/`:
- `documentation/architecture_guide.md`
- `documentation/operations_guide.md`
- `documentation/user_guide.md`
- `documentation/glossary.md`

**Process**:
1. Read all completed project artifacts
2. Generate documentation suite:
   - **Architecture Guide**: System overview, data flow, component descriptions, technology stack, design decisions
   - **Operations Guide**: Monitoring, troubleshooting, common issues, runbooks, SLA management
   - **User Guide**: Dashboard navigation, report interpretation, FAQ, getting help
   - **Glossary**: Business terms, technical terms, metrics definitions
3. Cross-reference against requirements to ensure completeness

### Validate

**Checks**:
- [ ] Architecture guide covers all system components
- [ ] Operations guide includes troubleshooting for common scenarios
- [ ] User guide covers all delivered dashboards/reports
- [ ] Glossary includes all business and technical terms used in the project

### Self-Review

**Criteria**:
1. **Completeness**: All aspects of the delivered solution are documented
2. **Accuracy**: Documentation reflects the actual implementation
3. **Accessibility**: Written for the target audience (technical vs business)
4. **Cross-References**: Documents link to each other appropriately

---

# Artifact Scope Reference

## full_platform
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
workshops: {generate: not_started, review: not_started}
conceptual_model: {generate: not_started, validate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
```

## pipeline_only
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dbt_development
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dashboard_extension
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dashboard_first
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
viz_catalog: {generate: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
seed_data: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_refactor: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# workshops, conceptual_model, pipeline_design, pipeline: not_applicable
```

## enablement
```yaml
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

---

# Phase 4: Final Summary

After all artifacts have been processed, output a comprehensive summary:

```
## Wire Autopilot — Execution Complete

**Project:** [client_name] — [project_name]
**Type:** [project_type]
**Branch:** [branch_name]
**Folder:** .wire/[folder_name]/

### Results

| Phase | Generate | Validate | Review | Files |
|-------|----------|----------|--------|-------|
| [artifact] | [complete] | [pass/N/A] | [approved/N/A] | [count] |
| ... | ... | ... | ... | ... |

### Completed Phases: [count]/[total]
### Blocked Phases: [count] (if any)

[If any blocked phases, list them with reasons]

### Deliverables Summary
- Total artifact phases: [count]
- Files generated: [count]
- dbt models: [count] (if applicable)
- LookML views: [count] (if applicable)
- Dashboard specs: [count] (if applicable)
- Training sessions: [count] (if applicable)
- Documentation guides: [count] (if applicable)

### Jira Summary (if configured)
- Epic: [PROJ-123]
- Tasks completed: [X/Y]

### What's Ready for Demo
[List of concrete deliverables that can be shown to the client, with file paths]

### Next Steps
1. Review all generated artifacts in `.wire/[folder_name]/`
2. [If blocked phases] Address blocked phases manually, then re-run: `/wire:dp-autopilot [folder_name]`
3. [If dbt generated] Run dbt models against real data
4. Create a pull request: `/wire:dp-utils-create-pr [folder_name]`
5. [If applicable] Schedule stakeholder demos using training materials
```

Log final entry to execution_log.md:
```
| [timestamp] | /wire:dp-autopilot | complete | Autopilot finished — [completed]/[total] phases, [blocked] blocked |
```

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:dp-<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:dp-*` command that was invoked (e.g., `/wire:dp-requirements-generate`, `/wire:dp-new`, `/wire:dp-dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:dp-new` created a new project
  - `archived` — `/wire:dp-archive` archived a project
  - `removed` — `/wire:dp-remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /wire:dp-new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:dp-requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:dp-requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:dp-requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:dp-conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:dp-conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:dp-conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:dp-conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:dp-conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:dp-conceptual_model-review | approved | Reviewed by John Doe |
```
