---
description: Create a new Wire engagement or add a release to an existing engagement
argument-hint: (no arguments - interactive)
---

# Create a new Wire engagement or add a release to an existing engagement

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
description: Create a new Wire engagement or add a release to an existing engagement
---

# Wire New Command

## Purpose

Interactive workflow to create a new engagement or add a new release to an existing engagement. Handles two-tier folder structure (engagement + releases), status file setup, and artifact scope determination based on the selected release type.

## Terminology

- **Engagement**: A complete client engagement. Contains engagement-wide context (SOW, calls, org charts) and one or more releases.
- **Release**: A scoped, time-boxed unit of delivery within an engagement. Discovery release types (`discovery`, `sop_discovery`) and delivery release types (`full_platform`, `pipeline_only`, etc.) are all release types.

## Release Types

| Type | Description | Typical Artifacts |
|------|-------------|------------------|
| `discovery` | Discovery (Shape Up): scoped, problem-first, solution-shaped before commitment | problem_definition, pitch, release_brief, sprint_plan |
| `sop_discovery` | RA Canonical (SOP) discovery: wide-ranging structured discovery leading to a go/no-go decision on a program of work. Exit deliverable is the sponsor-facing Findings Playback deck. | engagement_brief, stakeholder_map, stakeholder_interview, requirements_matrix, discovery_analyses, findings_playback, delivery_roadmap |
| `full_platform` | Complete data platform (pipelines + dbt + BI + enablement) | All artifacts |
| `pipeline_only` | Data pipeline development only | pipeline_design, pipeline, data_quality, deployment |
| `dbt_development` | dbt models and semantic layer | data_model, dbt, semantic_layer, data_quality |
| `dashboard_extension` | New dashboards on existing platform | requirements, mockups, dashboards, training |
| `dashboard_first` | Interactive mocks drive data model | mockups, viz_catalog, data_model, seed_data, dbt, semantic_layer, dashboards, data_refactor |
| `enablement` | Training and documentation only | training, documentation |
| `agentic_data_stack` | Self-service agentic data stack: governed data layer + semantic layer + per-domain knowledge skills + eval suite. Delivers an installable Claude agentic data stack. | dataset_audit, metric_audit, query_audit, governance_design, semantic_layer_design, canonical_models, lookml_views (Looker only), semantic_layer, knowledge_skill, agent_config, eval_suite, adversarial_config, launch_gate, enablement |
| `droughty` | Schema-introspection and base-layer generation using Droughty. Covers discovery on an existing warehouse (ERD, field docs, QA) and post-dbt base-layer generation (staging SQL, schema tests, base LookML views). Works as a standalone release type or as an optional phase within any delivery release. | droughty_setup, droughty_introspect, droughty_dbml, droughty_docs, droughty_qa, droughty_stage, droughty_dbt_tests, droughty_lookml |
| `custom` | Bespoke scope from SoW or project docs — Wire analyses documents and proposes a tailored release structure with custom specs | Derived from source documents |

## Workflow

### Step 0: Duplicate release detection

Before doing anything else, check whether any release already exists in this repo.

```bash
ls .wire/releases/ 2>/dev/null
```

If `.wire/releases/` exists and contains one or more subdirectories, read each subdirectory name and check whether it contains a `status.md`. If any release with a `status.md` is found:

1. List the existing releases:
   ```
   Found existing releases in this repo:
     - [release_folder_1]  ([release_type from status.md] — [generate/validate/review state of first artifact])
     - [release_folder_2]  ...
   ```

2. Ask the user directly in chat:
   ```
   A release already exists in this repo. To add another release to this engagement, continue (yes).
   To work on an existing release instead, run /wire:start or /wire:status.

   Add a new release? (yes/no)
   ```

3. If "no": stop immediately. Output:
   ```
   Run /wire:status to see the current state of all releases.
   Run /wire:start to pick up where you left off.
   ```

4. If "yes": continue to Step 1 (the engagement context already exists — Step 1 will detect this and jump to Step 6).

This guard prevents a second consultant from accidentally running `/wire:new` on an already-initialised project and overwriting the engagement context or status files.

---

### Step 1: New Engagement or Additional Release?

Check whether `.wire/engagement/context.md` already exists:

```bash
ls .wire/engagement/context.md 2>/dev/null
```

**If `.wire/engagement/context.md` exists** (engagement already set up):
- Ask directly in chat:
  ```
  An engagement already exists in this repo. Add a new release to it? (yes/no)
  If yes, what is the release type?
  ```
- If yes, skip to **Step 6 (Determine Release ID)** and proceed from there.
- If no, confirm whether they want to create a new engagement in the same repo (unusual — confirm explicitly).

**If no engagement exists** (first time):
- Proceed to Step 2.

### Step 2: Ask for Engagement Details

Ask directly in chat (one question at a time):

```
What is the client name for this engagement?
(e.g. "Acme Corporation", "Client M", "Liberus")
```

Wait for user response.

```
What is the engagement name? (descriptive, used in folder names)
(e.g. "acme_data_platform", "power_digital_analytics", "liberus_reporting")
```

Wait for user response.

```
What is your name (engagement lead)?
```

Wait for user response.

**Derive**:
- `client_name`: Display name as provided
- `engagement_name`: Lowercase, underscores for spaces, no special chars
- `engagement_lead`: As provided

### Step 3: Repo Mode

Ask directly in chat:

```
Is this repo the client's code repo, or a dedicated delivery repo?

Option A — Combined: The .wire/ folder lives directly in the client's code repo.
           Simple setup. Default for most engagements.

Option B — Dedicated delivery repo: This repo is exclusively for Wire delivery
           artifacts. The client's code repo is separate.
           Use for regulated clients (where adding files to their code repo isn't
           acceptable) or clients with multiple code repos.

Which applies? (A/B)
```

Wait for user response.

**If Option B (dedicated delivery repo)**:

Ask:
```
Please provide the client code repo details:
1. GitHub URL (e.g. https://github.com/client-org/client-repo)
2. Local path on your machine (e.g. /Users/you/Projects/client-repo)
3. Default branch (default: main)
```

Store:
- `client_repo_url`
- `client_repo_local_path`
- `client_repo_branch`

### Step 4: Ask About SOW

Ask directly in chat:

```
Do you have a Statement of Work (SOW) or proposal document?
- If yes, provide the file path (e.g. "path/to/SOW.pdf")
- If no, type "no"
```

Wait for user response. If a path is provided, verify the file exists.

### Step 5: Ask About First Release Type

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What type is the first release for this engagement?",
    "header": "First Release Type",
    "options": [
      {"label": "Discovery (Shape Up)", "description": "Discovery (Shape Up): scoped problem-shaping. Problem definition → pitch → release brief → sprint plan. Use when the problem to solve is reasonably understood and you need to shape a single bet."},
      {"label": "Discovery (SOP / Canonical)", "description": "RA Canonical discovery: wide-ranging structured discovery leading to a go/no-go decision on a program of work. Engagement brief → stakeholder map → interviews → consolidation → three analyses → Findings Playback deck → roadmap. Use when scope is unclear at SoW signature or a new analytical domain is being introduced."},
      {"label": "Full platform", "description": "Complete implementation (pipelines, dbt, BI, enablement)"},
      {"label": "Pipeline only", "description": "Data pipeline development"},
      {"label": "dbt development", "description": "dbt models and semantic layer"},
      {"label": "Dashboard extension", "description": "New dashboards on existing platform"},
      {"label": "Dashboard-first rapid dev", "description": "Interactive mocks drive data model"},
      {"label": "Enablement", "description": "Training and documentation"},
      {"label": "Platform Migration", "description": "Full lifecycle migration of a data platform from one warehouse stack to another. Covers ingestion audit, db object audit, security audit, dbt audit, orchestration audit → migration inventory → strategy → target setup → parallel ingestion → batched dbt translation (models and snapshots, with SCD-2 snapshot history preserved) → orchestration migration → equivalency validation loop → cutover."},
      {"label": "Agentic Data Stack", "description": "Build a governed self-service agentic data stack — dataset governance, semantic layer expansion, per-domain knowledge skills, and an eval suite with per-domain accuracy gates. Delivers an installable Claude agentic data stack skill and maintenance infrastructure."},
      {"label": "Droughty", "description": "Schema introspection and base-layer generation using Droughty. Use for discovery sprints on existing warehouses (ERD, field docs, QA) or as a post-dbt phase to generate staging SQL, schema tests, and base LookML views. Can also be added as an optional phase to any delivery release."},
      {"label": "Custom", "description": "Bespoke scope not covered by a standard release type. Wire analyses your SoW or plan and proposes a tailored release structure — mapping deliverables to existing commands where possible, generating new project-scoped specs for the rest."}
    ],
    "multiSelect": false
  }]
}
```

Map selection to `release_type`:

| Selected label | `release_type` value |
|---|---|
| Discovery (Shape Up) | `discovery` |
| Discovery (SOP / Canonical) | `sop_discovery` |
| Full platform | `full_platform` |
| Pipeline only | `pipeline_only` |
| dbt development | `dbt_development` |
| Dashboard extension | `dashboard_extension` |
| Dashboard-first rapid dev | `dashboard_first` |
| Enablement | `enablement` |
| Platform Migration | `platform_migration` |
| Agentic Data Stack | `agentic_data_stack` |
| Droughty | `droughty` |
| Custom | `custom` |

### Step 6: Determine Release ID

**Process**:
1. Count existing releases in `.wire/releases/` — next release number = count + 1 (padded to 2 digits)
2. For the first release, `release_number = "01"`
3. Ask for a release name:
   ```
   What is the name for this release?
   (e.g. "discovery", "data-foundation", "reporting-layer")
   ```
4. `release_folder = "[release_number]-[release_name]"` (e.g. `01-discovery`)
5. Today's date as `release_id` = `YYYYMMDD` (for status file ID, distinct from folder name)

### Step 7: Confirm Settings

Show derived values:

```
I'll create this engagement and release with these settings:

Engagement:
  Client:         [client_name]
  Engagement:     [engagement_name]
  Lead:           [engagement_lead]
  Repo mode:      [Combined | Dedicated delivery]
  [If dedicated:] Client repo: [client_repo_url]
  SOW:            [sow_path or "none"]

First Release:
  Type:           [release_type]
  Folder:         .wire/releases/[release_folder]/
  Release ID:     [release_id]
```

Use `AskUserQuestion` to confirm:

```json
{
  "questions": [{
    "question": "Create this engagement and first release?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, create it", "description": "Create the engagement and release with these settings"},
      {"label": "Change settings", "description": "Let me provide different settings"}
    ],
    "multiSelect": false
  }]
}
```

If "Change settings", return to Step 2.

### Step 8: Git Branch Check

**Process**:
1. Run `git rev-parse --abbrev-ref HEAD` via Bash
2. If command fails (not a git repo), skip silently
3. If branch is `HEAD` (detached), skip silently
4. If branch is `main` or `master`:
   - Suggested branch: `feature/[engagement_name]`
   - Use `AskUserQuestion` to confirm or customise the branch name
   - Create and switch: `git checkout -b [branch_name]`
5. Store `branch_name` for display in the confirmation step

### Step 8.5: Tenant Carve-out Scope Check (existing engagements only)

This step only runs when **both** of these are true:
1. `.wire/engagement/context.md` already existed at the start of this run — this is the same detection used in Step 1 to distinguish "new engagement" from "new release in an existing engagement" (re-run `ls .wire/engagement/context.md 2>/dev/null` here if the result wasn't retained).
2. The release type selected for this new release is `platform_migration`.

If either is false, skip this step entirely and proceed to Step 9 — the `migration.scope` question stays in its normal place at Step 14 Question 9, and Steps 9/9.5 run unmodified.

If both are true, ask the scope question now (pulled forward from Step 14 Question 9) so Steps 9 and 9.5 below can branch on it:

"Is this a **full platform migration** or a **tenant carve-out** (extracting a single tenant's data into the target)?" (Options: Full migration (default) / Tenant carve-out). If **Tenant carve-out** is selected, also ask: "What is the **tenant predicate** that scopes the extracted tenant — the WHERE clause or tenant key? (e.g. `tenant_id = 4815`)".

Store `migration.scope` (`full_migration` | `tenant_carveout`) and `migration.tenant_predicate` here. Step 14 Question 9 must reuse these stored values instead of re-asking when they were already captured in this step.

**If `migration.scope` resolves to `tenant_carveout`**, identify the parent release this carve-out is being spawned from:
1. Read each subdirectory in `.wire/releases/` and check its `status.md` frontmatter for `project_type: "platform_migration"`.
2. If exactly one such release is found, store its folder name as `parent_release_folder`.
3. If more than one is found, ask the user directly: "Which existing release is the parent for this carve-out?" and list the candidates by folder name.
4. If none is found, there is no parent to share from — proceed to Steps 9 and 9.5 as normal (the carve-out branches below only fire when a `parent_release_folder` is identified).

### Step 9: Issue Tracker Integration (Optional)

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to track this engagement in an issue tracker?",
    "header": "Issue Tracker",
    "options": [
      {"label": "Jira", "description": "Create or link Jira Epic, Tasks, and Sub-tasks"},
      {"label": "Linear", "description": "Create or link a Linear Project, Issues, and Sub-issues"},
      {"label": "Both Jira and Linear", "description": "Track in both Jira and Linear simultaneously"},
      {"label": "No, skip issue tracking", "description": "Track progress in status.md only"}
    ],
    "multiSelect": false
  }]
}
```

**Tenant carve-out branch**: If Step 8.5 identified `migration.scope: tenant_carveout` with a `parent_release_folder`, replace the tracker-specific setup questions below with this upfront share-or-separate choice, asked once per tracker selected above. For non-carve-out releases, or when no `parent_release_folder` was identified, this branch does not fire — proceed with the setup questions exactly as written below.

If Jira or Both was selected:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Jira project, or use its own — which do you want?",
    "header": "Carve-out Jira Setup",
    "options": [
      {"label": "Share the parent's Jira project", "description": "Reuse [parent_release_folder]'s Jira project key — this release still gets its own Epic and Tasks, inside that same project"},
      {"label": "Use a separate Jira project", "description": "Set up a new, dedicated Jira project for this carve-out release"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Jira project": read `jira.project_key` from `parent_release_folder`'s `status.md` and use it directly as `jira_project_key`. Still ask the normal "How would you like to set up Jira?" mode question below to determine `jira_mode`/`jira_structure` for this release's own issue hierarchy — only the project key question is skipped.
- If "Use a separate Jira project": continue with the normal Jira setup questions below, unchanged (fresh project key + mode).

If Linear or Both was selected, ask the equivalent question for Linear:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Linear team/project, or use its own — which do you want?",
    "header": "Carve-out Linear Setup",
    "options": [
      {"label": "Share the parent's Linear team/project", "description": "Reuse [parent_release_folder]'s Linear team and project — this release's issues are created inside that same project"},
      {"label": "Use a separate Linear team/project", "description": "Set up a new, dedicated Linear team identifier and/or project for this carve-out release"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Linear team/project": read `linear.team_id` and `linear.project_id` from `parent_release_folder`'s `status.md` and use them directly, with `linear_mode: "create_in_existing"` — skip Questions 1–3 below.
- If "Use a separate Linear team/project": continue with the normal Linear setup Questions 1–3 below, unchanged.

**If Jira or Both selected**: Ask for the Jira project key and preferred mode:
```json
{
  "questions": [{
    "question": "How would you like to set up Jira?",
    "header": "Jira Setup",
    "options": [
      {"label": "Create new Jira issues — sub-tasks per command", "description": "Create Epic per release → one Task per artifact → three Sub-tasks per artifact (generate / validate / review). Each command transitions its own Sub-task."},
      {"label": "Create new Jira issues — single issue per artifact", "description": "Create Epic per release → one Task per artifact (no sub-tasks). The single Task moves through To Do → In Progress (generate) → In Review (validate) → Done (review approved). Requires the Jira project's workflow to support those four states."},
      {"label": "Link to existing Jira issues", "description": "Search a Jira project for existing issues and link them — sub-tasks structure assumed"}
    ],
    "multiSelect": false
  }]
}
```
Store `jira_project_key`, `jira_mode` (`create` or `link`), and `jira_structure` (`subtasks` for the first / third option, `single_issue` for the second). Pass all three to Step 15.

**If Linear or Both selected**: Ask the following as three separate questions in sequence:

**Question 1** — Ask directly in chat:
```
What is the Linear team identifier? (e.g., ENG, DATA, ACME)
```

**Question 2** — Use `AskUserQuestion`:
```json
{
  "questions": [{
    "question": "How would you like to set up Linear?",
    "header": "Linear Setup",
    "options": [
      {"label": "Create new project + new issues", "description": "Wire will create a new Linear project with issues and sub-issues from scratch"},
      {"label": "Use existing project + create new issues", "description": "Wire will create fresh issues inside an existing project — you'll provide the project URL or ID next"},
      {"label": "Link to existing project + existing issues", "description": "Wire will search the team for matching issues and link them to Wire artifacts — you'll provide the project URL or ID next"}
    ],
    "multiSelect": false
  }]
}
```

**Question 3** — Only if "Use existing project + create new issues" or "Link to existing project + existing issues" was selected, ask directly in chat:
```
Paste the Linear project URL or ID (e.g. https://linear.app/acme/project/my-project-abc123):
```

Store `linear_team_id`, `linear_project_id` (if provided, extract from URL or use as-is), and `linear_mode` ("create", "create_in_existing", or "link") for use in Step 15.

### Step 9.5: Document Store Integration (Optional)

**Question 1** — Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to replicate generated documents to a client-accessible document store for review and annotation?",
    "header": "Document Store",
    "options": [
      {"label": "Confluence", "description": "Publish documents to a Confluence space — reviewers can comment and annotate inline"},
      {"label": "Notion", "description": "Publish documents to a Notion workspace — reviewers can comment and edit pages"},
      {"label": "Both Confluence and Notion", "description": "Publish to both simultaneously"},
      {"label": "No, skip document store", "description": "Documents stay in GitHub only"}
    ],
    "multiSelect": false
  }]
}
```

**Tenant carve-out branch**: If Step 8.5 identified `migration.scope: tenant_carveout` with a `parent_release_folder`, replace Questions 2 and 3 below with this upfront share-or-separate choice, asked once per provider selected in Question 1. For non-carve-out releases, or when no `parent_release_folder` was identified, this branch does not fire — proceed with Questions 2 and 3 exactly as written below.

If Confluence or Both Confluence and Notion was selected:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Confluence space, or use its own — which do you want?",
    "header": "Carve-out Confluence Setup",
    "options": [
      {"label": "Share the parent's Confluence space", "description": "Publish this release's documents into [parent_release_folder]'s existing Confluence space"},
      {"label": "Use a separate Confluence space", "description": "Publish this release's documents into their own, dedicated Confluence space"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Confluence space": read `docstore.confluence.space_key` from `parent_release_folder`'s `status.md` and use it directly as `confluence_space_key` — skip Question 2 below.
- If "Use a separate Confluence space": continue with Question 2 below, unchanged (ask for a new space key).

If Notion or Both Confluence and Notion was selected, ask the equivalent question for Notion:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Notion parent page, or use its own — which do you want?",
    "header": "Carve-out Notion Setup",
    "options": [
      {"label": "Share the parent's Notion parent page", "description": "Publish this release's documents under [parent_release_folder]'s existing Notion parent page"},
      {"label": "Use a separate Notion parent page", "description": "Publish this release's documents under their own, dedicated Notion parent page"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Notion parent page": read `docstore.notion.parent_page_id` from `parent_release_folder`'s `status.md` and use it directly as `notion_parent_page_id` — skip Question 3 below.
- If "Use a separate Notion parent page": continue with Question 3 below, unchanged.

**Question 2** — If "Confluence" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Confluence space key where Wire documents should be published?
(e.g. PROJ, ACME, DATA — found in the space URL: /wiki/spaces/PROJ/...)
```
Store `confluence_space_key`.

**Question 3** — If "Notion" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Notion parent page for Wire documents?
Paste the page URL or ID (e.g. https://www.notion.so/My-Projects-abc123 or just the ID).
This page must already exist and be accessible via the Notion MCP.
```
Store `notion_parent_page_id` (extract ID from URL if a full URL was given).

If any document store is selected, follow the workflow in `specs/utils/docstore_setup.md`. Pass the engagement name, release folder, provider choice, `confluence_space_key` (if set), and `notion_parent_page_id` (if set) — the utility should skip re-asking for these when they are already supplied.

If skipped, continue to Step 10.

### Step 10: Create Engagement Folder Structure

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
mkdir -p .wire/research/sessions
touch .wire/engagement/calls/.gitkeep
touch .wire/engagement/org/.gitkeep
touch .wire/research/sessions/.gitkeep
```

### Step 10.5: Scaffold GitHub PR Template

Create `.github/pull_request_template.md` from the Wire PR template so that every PR raised against this repo is Wire-aware by default.

```bash
mkdir -p .github
```

Read `TEMPLATES/pr_template.md` and write it verbatim to `.github/pull_request_template.md`.

Skip this step silently if `.github/pull_request_template.md` already exists (do not overwrite a customised template).

### Step 11: Create Engagement Context File

Read `TEMPLATES/engagement-context-template.md` and populate:
- `{{ENGAGEMENT_NAME}}` → engagement_name
- `{{CLIENT_NAME}}` → client_name
- `{{CREATED_DATE}}` → today's date (YYYY-MM-DD)
- `{{ENGAGEMENT_LEAD}}` → engagement_lead
- `{{REPO_MODE}}` → `combined` or `dedicated_delivery`

If repo mode is `dedicated_delivery`, populate the `client_repo` section with the provided URL, local path, and branch.

Write to `.wire/engagement/context.md`.

### Step 12: Copy SOW (if provided)

```bash
cp [sow_path] .wire/engagement/sow.md   # or sow.pdf if PDF
```

### Step 13: Create Release Folder Structure

**For discovery release types (`discovery`, `sop_discovery`)**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,planning}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

For `sop_discovery`, also create the interview folder used by the per-stakeholder write-ups:
```bash
mkdir -p .wire/releases/[release_folder]/planning/interviews
touch .wire/releases/[release_folder]/planning/interviews/.gitkeep
```

**For `platform_migration` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/{audit,strategy,migration,migration/target_setup_scripts}
touch .wire/releases/[release_folder]/audit/.gitkeep
```

**For `agentic_data_stack` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,artifacts/eval_suite,artifacts/knowledge_skill}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

**For `droughty` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/artifacts/droughty
mkdir -p .wire/releases/[release_folder]/artifacts/droughty/field_descriptions
touch .wire/releases/[release_folder]/artifacts/droughty/.gitkeep
```

**For all other release types**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,planning,requirements,design,dev,test,deploy,enablement}
touch .wire/releases/[release_folder]/requirements/.gitkeep
touch .wire/releases/[release_folder]/design/.gitkeep
touch .wire/releases/[release_folder]/dev/.gitkeep
touch .wire/releases/[release_folder]/test/.gitkeep
touch .wire/releases/[release_folder]/deploy/.gitkeep
touch .wire/releases/[release_folder]/enablement/.gitkeep
```

### Step 14: Create Release Status File

**For `discovery` release type**:
1. Read `TEMPLATES/discovery-status-template.md`
2. Replace placeholders:
   - `{{RELEASE_ID}}` → release_id
   - `{{RELEASE_NAME}}` → release_folder (the human-readable name)
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
3. Write to `.wire/releases/[release_folder]/status.md`

**For `sop_discovery` release type**:
1. Read `TEMPLATES/sop-discovery-status-template.md`
2. Replace the same placeholders as above
3. Write to `.wire/releases/[release_folder]/status.md`

**For `platform_migration` release type**:

Ask the following additional questions (one at a time):

1. "What is the **source platform**?" (Options: BigQuery / Snowflake)
2. "What is the **target platform**?" (Must differ from source — re-ask if same platform selected)
3. "What is the **dbt project path**?" (Default: `./dbt` — accept if user presses Enter)
4. "What is the **orchestration tool**?" (Options: Dagster / dbt Cloud / Airflow / None)
5. "What is the **ingestion tool**?" (Options: Fivetran / RudderStack / Coupler.io / Segment / Airbyte / Other). Store as `migration.ingestion_tool` with values `fivetran` / `rudderstack` / `coupler-io` / `segment` / `airbyte` / `other`. Each named tool has a corresponding skill at `wire/skills/<tool>/SKILL.md` and a tool-specific branch in `ingestion-audit-generate`. "Other" covers Stitch, Estuary, and custom-built ingestion — falls back to CSV-driven audit.
6. "What is the **connectivity mode** to the source platform?" (Options: Public endpoint / Private network with MCP tunnel)
   - Also ask: "What **reporting / BI tool** does the client use?" (Options: Looker / Metabase / Omni / OAC / None / Other). Store as `migration.reporting_tool` with values `looker` / `metabase` / `omni` / `oac` / `none` / `other`. `metabase` enables the `metabase-audit` and `metabase-migration` commands; `omni` enables the `omni-audit` and `omni-migration` commands (same reporting-layer migration role, adapted to Omni's connection → model → topic → workbook/tile object hierarchy); `oac` enables the `oac-audit` and `oac-migration` commands (same reporting-layer migration role, adapted to OAC's SMML physical/logical/presentation layer object model); `looker` is the Wire default. This is independent of `migration.scope`.
   - Also ask: "Does the client use a **reverse ETL tool**?" (Options: Hightouch / None / Other). Store as `migration.reverse_etl_tool` with values `hightouch` / `none` / `other`. `hightouch` enables `reverse-etl-audit` and `reverse-etl-migration` as a sixth audit alongside the five core audits (see `wire/skills/hightouch/SKILL.md`); `none` is the default — the sixth audit simply doesn't run. "Other" covers Census and Polytomic, which `reverse-etl-audit`'s spec documents as following the same output shape via tool-specific API branches, but aren't implemented yet — falls back to the same manual `migration.reverse_etl_tool` value with a note that automated cataloguing isn't available for that tool.
7. "What is the **target project / account**?" (The GCP project ID for BigQuery, or Snowflake account identifier for the target environment — the place all migration writes will land.)
8. "Are there any **production project IDs** that should be treated as off-limits for writes?" (Comma-separated list, or press Enter to skip. These are client production environment IDs that Claude will refuse to write to during migration commands.) Store as `data_safety.production_projects` list.
9. "Is this a **full platform migration** or a **tenant carve-out** (extracting a single tenant's data into the target)?" (Options: Full migration (default) / Tenant carve-out). If **Tenant carve-out** is selected, also ask: "What is the **tenant predicate** that scopes the extracted tenant — the WHERE clause or tenant key? (e.g. `tenant_id = 4815`)". Store as `migration.scope` (`full_migration` | `tenant_carveout`) and `migration.tenant_predicate`. If the user selects Full migration or presses Enter, leave `migration.scope` at its default of `full_migration` and `migration.tenant_predicate` null. **If `migration.scope` and `migration.tenant_predicate` were already captured in Step 8.5** (adding a tenant-carve-out release to an existing engagement), skip this question entirely and reuse the stored values — do not ask again.

If **Private network with MCP tunnel** is selected, output these setup instructions and wait for confirmation before proceeding:

```
Private network connectivity selected.

To proceed, set up the MCP tunnel to your source platform:
1. Ensure the MCP tunnel agent is running on your network
2. Add the tunnel MCP server to .claude/settings.json under mcpServers
3. Test connectivity: the tunnel should expose source platform SQL access

Confirm when the tunnel is active and accessible. (Type "tunnel ready" to continue)
```

Wait for confirmation before continuing.

Store `source_platform`, `target_platform`, `dbt_project_path`, `orchestration_tool`, `ingestion_tool`, `reporting_tool`, `reverse_etl_tool`, `connectivity`, `target_project_or_account`, `production_projects`, `scope`, `tenant_predicate`.

1. Read `TEMPLATES/migration/status_migration.md`
2. Replace placeholders:
   - `{{PROJECT_ID}}` → release_id
   - `{{PROJECT_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{SOURCE_PLATFORM}}` → source_platform
   - `{{TARGET_PLATFORM}}` → target_platform
   - `{{DBT_PROJECT_PATH}}` → dbt_project_path
   - `{{ORCHESTRATION_TOOL}}` → orchestration_tool
   - `{{INGESTION_TOOL}}` → ingestion_tool
   - `migration.reporting_tool` → reporting_tool if captured; otherwise leave the template default `none` unchanged
   - `migration.reverse_etl_tool` → reverse_etl_tool if captured; otherwise leave the template default `none` unchanged
   - `{{CONNECTIVITY}}` → connectivity
   - `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake) → target_project_or_account
   - `data_safety.target_project` → target_project_or_account (same value — mirrors the migration section)
   - `data_safety.production_projects` → production_projects list (empty list if user skipped)
   - `migration.scope` → `tenant_carveout` if the user selected tenant carve-out; otherwise leave the template default `full_migration` unchanged
   - `migration.tenant_predicate` → tenant predicate string if captured; otherwise leave null
3. Write to `.wire/releases/[release_folder]/status.md`

> When `migration.scope` is left at `full_migration` (the default for any non-carve-out migration), every existing migration command behaves exactly as before — `scope` and `tenant_predicate` carry their default values and no command branches on them. The carve-out steps only activate when `scope` is explicitly `tenant_carveout`.

**For `agentic_data_stack` release type**:

Ask seven additional questions (one at a time):

1. "What **BI tool** is in use?" (Options: Looker / Tableau / Power BI / Metabase / Omni / Other)
2. "What **semantic layer** exists?" (Options: dbt Semantic Layer / MetricFlow / LookML explores / Cube / Omni model / OAC (SMML) / None)
3. "What is the **dbt project path**?" (Default: `./` — accept if user presses Enter; enter "none" if no dbt project)
4. "What **warehouse** does the client use?" (Options: BigQuery / Snowflake / Databricks / Redshift)
5. "What is the **primary business domain**?" (Options: ecommerce / SaaS / marketing analytics / finance / Other)
6. "Approximately how many tables are in the analytics schema?" (Free text — used to calibrate audit scope)
7. "Is **query history** accessible?" (Options: Yes — full query log access / Yes — limited (last 30 days) / No — will use stakeholder input)

Store `bi_tool`, `semantic_layer`, `dbt_project_path`, `warehouse`, `primary_domain`, `table_count_approx`, `query_history_access`.

1. Read `TEMPLATES/agentic_data_stack/status_agentic_data_stack.md`
2. Replace placeholders:
   - `YYYYMMDD_client_agentic_data_stack` → release_id
   - `Client Name` → client_name
   - `Consultant Name` → engagement_lead
   - `YYYY-MM-DD` (start_date) → today's date
   - Update `warehouse`, `bi_tool`, `semantic_layer`, `dbt_project_path`, `primary_domain`, `query_history_access` from answers above
3. Write to `.wire/releases/[release_folder]/status.md`

Also create the agentic_data_stack release folder structure:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,artifacts/eval_suite,artifacts/knowledge_skill}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

**For `droughty` release type**:

Ask two additional questions (one at a time):

1. "What **warehouse** does the client use?" (Options: BigQuery / Snowflake)
2. "What is the **Droughty context** for this release?" (Options: Discovery / audit on existing warehouse / Post-dbt deploy — generate base layer from deployed models / Both — full sequence)

Map context to `droughty_context` value: `discovery` / `post_dbt` / `full`

Store `warehouse` and `droughty_context`.

1. Read `TEMPLATES/droughty-status-template.md`
2. Replace placeholders:
   - `{{RELEASE_ID}}` → release_id
   - `{{RELEASE_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{DROUGHTY_CONTEXT}}` → droughty_context
3. Set `droughty.warehouse` from the warehouse answer
4. Write to `.wire/releases/[release_folder]/status.md`

**For `custom` release type**:
1. Read `TEMPLATES/custom-status-template.md`
2. Replace placeholders:
   - `{{PROJECT_ID}}` → release_id
   - `{{PROJECT_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{RELEASE_FOLDER}}` → release_folder
   - `{{SOURCE_DOCUMENTS}}` → "TBD — provided in /wire:custom-define"
3. Write to `.wire/releases/[release_folder]/status.md`
4. **Invoke `wire/specs/custom/define.md`** to handle document ingestion, deliverable mapping, custom spec generation, and `.claude/commands/` wrapper creation. The `define` command handles all remaining scaffolding — do not write a standard deliverables section to status.md; `define` does this after the user confirms the proposed structure.

**For all other release types**:
1. Read `TEMPLATES/status-template.md`
2. Replace placeholders (same pattern, using `{{PROJECT_ID}}` → release_id etc.)
3. Set artifact scope based on release type (same logic as prior `new.md` Step 8)
4. Write to `.wire/releases/[release_folder]/status.md`

### Step 15: Set Up Issue Tracker(s) (if opted in)

**If Jira or Both selected**: Follow the workflow in `specs/utils/jira_create.md`. Pass `jira_project_key`, `jira_mode`, `jira_structure`, release type, and artifact scope.

**If Linear or Both selected**: Follow the workflow in `specs/utils/linear_create.md`. Pass `linear_team_id`, `linear_mode`, release type, and artifact scope.

When **Both** is selected, run both workflows. They operate independently — failures in one do not block the other.

### Step 16: Confirm Creation and Guide Next Steps

```
## Engagement Created ✅

**Client**: [client_name]
**Engagement**: [engagement_name]
**Branch**: [branch_name]
**Repo mode**: [Combined | Dedicated delivery]

### Folder Structure

.wire/
├── engagement/
│   ├── context.md          # Engagement overview and stakeholders
│   ├── sow.md              # [if copied]
│   ├── calls/              # Call transcripts
│   └── org/                # Org charts and stakeholder details
├── releases/
│   └── [release_folder]/   # [release_type]
│       ├── status.md       # Release tracking
│       ├── artifacts/      # Source materials
│       └── planning/       # [discovery: planning docs; sop_discovery also has planning/interviews/]
└── research/
    └── sessions/           # Research findings (auto-populated)

### Next Steps

[If `discovery`]:
1. Generate the problem definition:
   /wire:problem-definition-generate [release_folder]

2. Or start a session first:
   /wire:session-start [release_folder]

[If `sop_discovery`]:
1. Draft the engagement brief from the signed SoW and deal record:
   /wire:engagement-brief-generate [release_folder]

2. Then build the stakeholder map:
   /wire:stakeholder-map-generate [release_folder]

3. Or start a session first:
   /wire:session-start [release_folder]

[If delivery release type]:
1. Add source materials to .wire/releases/[release_folder]/artifacts/
2. Generate requirements:
   /wire:requirements-generate releases/[release_folder]

3. Or start a session first:
   /wire:session-start [release_folder]

[If `droughty` release type]:
1. Configure Droughty — install and connect to the warehouse:
   /wire:droughty-setup releases/[release_folder]

2. Then run the Droughty phase (or individual commands):
   /wire:droughty-generate releases/[release_folder]

[If `custom` release type]:
Custom spec generation is already underway via /wire:custom-define.
Once complete, invoke your first custom generate command:
  /[first-artifact-name]-generate [release_folder]

Or check what commands were created:
  ls .wire/releases/[release_folder]/custom-commands/

### Quick Commands

| Command | Purpose |
|---------|---------|
| `/wire:session-start [folder]` | Start a focused working session |
| `/wire:status releases/[folder]` | Check release status |
| `/wire:problem-definition-generate [folder]` | [discovery] Start the Shape Up workflow |
| `/wire:engagement-brief-generate [folder]` | [sop_discovery] Start the SOP discovery workflow |
| `/wire:requirements-generate releases/[folder]` | [delivery] Generate requirements |
| `/wire:migration-audit-all [folder]` | [platform_migration] Run all 5 source platform audits in parallel |
| `/wire:ingestion-audit-generate [folder]` | [platform_migration] Audit Fivetran connectors on source platform |
| `/wire:ads-audit-all [folder]` | [agentic_data_stack] Run all three audits in parallel |
| `/wire:ads_dataset-audit-generate [folder]` | [agentic_data_stack] Inventory warehouse tables and grade governance maturity |
| `/wire:ads_metric-audit-generate [folder]` | [agentic_data_stack] Inventory metric definitions and coverage gaps |
| `/wire:ads_query-audit-generate [folder]` | [agentic_data_stack] Analyse query history for question patterns |
| `/wire:droughty-setup [folder]` | [droughty] Install Droughty and generate profile.yaml + droughty_project.yaml |
| `/wire:droughty-generate [folder]` | [droughty] Run the full Droughty phase in sequence |
```

## Edge Cases

### Adding a release to an existing engagement

If `.wire/engagement/context.md` already exists, skip Steps 2–5 (engagement setup) and jump to Step 6. Read the existing engagement context to pre-populate client name, engagement name, and lead. Only ask for the release type and name.

### Not a Git Repository

If `git rev-parse --abbrev-ref HEAD` fails, skip the branch check silently.

### Release name conflicts

If `.wire/releases/[release_folder]/` already exists, append a letter suffix (`-b`, `-c`).

### SOW File Not Found

If the SOW path provided doesn't exist, prompt again or offer to continue without SOW.

## Output

This command creates:
- `.wire/engagement/` directory and `context.md`
- `.wire/releases/[release_folder]/` directory structure
- `.wire/releases/[release_folder]/status.md`
- `.wire/research/sessions/` directory
- `.github/pull_request_template.md` (Wire-aware PR template)
- Copies SOW to `engagement/` if provided

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

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
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
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
