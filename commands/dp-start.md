---
description: Project startup - shows all data platform projects and helps user select which to work on
---

# Project startup - shows all data platform projects and helps user select which to work on

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Project startup - shows all data platform projects and helps user select which to work on
---

# DP Start Command

## Purpose

Entry point when starting Claude Code for data platform delivery work. Shows status of all projects and guides user to select which project to work on.

## Workflow

### Step 1: Load Context

**Process**:
1. Read `COMMANDS.md` (in the framework root directory) to understand the available commands and delivery process structure

### Step 2: Scan Project Statuses

**Process**:
1. Use Glob to find all status files: `.wire/[0-9]*_*/status.md`
2. Read each status.md and parse the frontmatter artifacts section
3. **Determine "Next Action"** by finding the first incomplete lifecycle step

**Next Action Logic:**

First, read the `project_type` from each project's status.md frontmatter. Use the appropriate phase ordering below.

**Default phase ordering** (for `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `enablement`):

Check artifacts in this order by phase:

**Requirements Phase:**
- `requirements → workshops`

**Design Phase:**
- `pipeline_design → data_model → mockups`

**Development Phase:**
- `pipeline → dbt → semantic_layer → dashboards`

**Testing Phase:**
- `data_quality → uat`

**Deployment Phase:**
- `deployment`

**Enablement Phase:**
- `training → documentation`

**Dashboard-first phase ordering** (for `dashboard_first`):

Check artifacts in this order by phase:

**Requirements Phase:**
- `requirements`

**Mock Phase:**
- `mockups → viz_catalog`

**Design Phase:**
- `data_model`

**Seed Phase:**
- `seed_data`

**Development Phase:**
- `dbt → semantic_layer → dashboards`

**Refactor Phase:**
- `data_refactor`

**Testing Phase:**
- `data_quality → uat`

**Deployment Phase:**
- `deployment`

**Enablement Phase:**
- `training → documentation`

For each artifact, check lifecycle steps in order: `generate → validate → review`

**Skip artifacts with state `not_applicable`** (used when artifacts are out-of-scope).

The first incomplete step becomes the "Next Action".

**Completion states:**
- `generate`: complete = done
- `validate`: pass = done (fail/pending/not_started = incomplete)
- `review`: approved = done (changes_requested/pending/not_started = incomplete)
- `not_applicable`: skip (artifact is out of scope)

### Step 3: Present Overview

**Invoke `/wire:dp-status`** (no argument) to show the overview.

This displays a detailed artifact lifecycle table per project with **Next** action line under each.

### Step 4: Ask User to Select Project

Use `AskUserQuestion` to prompt user selection:

**Question:** "Which data platform project do you want to work on?"

**Options** (dynamically built from scanned projects):
- One option per project:
  - Label: `YYYYMMDD_name (Type: project_type)`
  - Description: Current next action from status.md
- Plus static options:
  - Label: "Create new project"
  - Description: "Set up a new data platform project interactively"
  - Label: "Wire Autopilot"
  - Description: "Autonomous end-to-end execution from a SOW — generates, validates, and reviews all artifacts automatically"
  - Label: "Skip"
  - Description: "Just exploring, no specific project"

### Step 5: Handle Selection

**If specific project selected:**

Show the overview and suggest the next command based on the first incomplete artifact step:

| Artifact | Incomplete Step | Suggested Command |
|----------|-----------------|-------------------|
| (no artifacts) | - | "Add source materials to `.wire/<folder>/artifacts/`" |
| requirements | generate | `/wire:dp-requirements-generate <folder>` |
| requirements | validate | `/wire:dp-requirements-validate <folder>` |
| requirements | review | `/wire:dp-requirements-review <folder>` |
| workshops | generate | `/wire:dp-workshops-generate <folder>` |
| workshops | review | `/wire:dp-workshops-review <folder>` |
| pipeline_design | generate | `/wire:dp-pipeline_design-generate <folder>` |
| pipeline_design | validate | `/wire:dp-pipeline_design-validate <folder>` |
| pipeline_design | review | `/wire:dp-pipeline_design-review <folder>` |
| data_model | generate | `/wire:dp-data_model-generate <folder>` |
| data_model | validate | `/wire:dp-data_model-validate <folder>` |
| data_model | review | `/wire:dp-data_model-review <folder>` |
| mockups | generate | `/wire:dp-mockups-generate <folder>` |
| mockups | review | `/wire:dp-mockups-review <folder>` |
| pipeline | generate | `/wire:dp-pipeline-generate <folder>` |
| pipeline | validate | `/wire:dp-pipeline-validate <folder>` |
| pipeline | review | `/wire:dp-pipeline-review <folder>` |
| dbt | generate | `/wire:dp-dbt-generate <folder>` |
| dbt | validate | `/wire:dp-dbt-validate <folder>` |
| dbt | review | `/wire:dp-dbt-review <folder>` |
| semantic_layer | generate | `/wire:dp-semantic_layer-generate <folder>` |
| semantic_layer | validate | `/wire:dp-semantic_layer-validate <folder>` |
| semantic_layer | review | `/wire:dp-semantic_layer-review <folder>` |
| dashboards | generate | `/wire:dp-dashboards-generate <folder>` |
| dashboards | validate | `/wire:dp-dashboards-validate <folder>` |
| dashboards | review | `/wire:dp-dashboards-review <folder>` |
| viz_catalog | generate | `/wire:dp-viz_catalog-generate <folder>` |
| seed_data | generate | `/wire:dp-seed_data-generate <folder>` |
| seed_data | validate | `/wire:dp-seed_data-validate <folder>` |
| seed_data | review | `/wire:dp-seed_data-review <folder>` |
| data_refactor | generate | `/wire:dp-data_refactor-generate <folder>` |
| data_refactor | validate | `/wire:dp-data_refactor-validate <folder>` |
| data_refactor | review | `/wire:dp-data_refactor-review <folder>` |
| data_quality | generate | `/wire:dp-data_quality-generate <folder>` |
| data_quality | validate | `/wire:dp-data_quality-validate <folder>` |
| data_quality | review | `/wire:dp-data_quality-review <folder>` |
| uat | generate | `/wire:dp-uat-generate <folder>` |
| uat | review | `/wire:dp-uat-review <folder>` |
| deployment | generate | `/wire:dp-deployment-generate <folder>` |
| deployment | validate | `/wire:dp-deployment-validate <folder>` |
| deployment | review | `/wire:dp-deployment-review <folder>` |
| training | generate | `/wire:dp-training-generate <folder>` |
| training | validate | `/wire:dp-training-validate <folder>` |
| training | review | `/wire:dp-training-review <folder>` |
| documentation | generate | `/wire:dp-documentation-generate <folder>` |
| documentation | validate | `/wire:dp-documentation-validate <folder>` |
| documentation | review | `/wire:dp-documentation-review <folder>` |
| (all complete) | - | "All artifacts complete! Ready for handover." |

**If "Create new project" selected:**

Invoke the `/wire:dp-new` command to run the interactive project creation workflow.

**If "Wire Autopilot" selected:**

Invoke the `/wire:dp-autopilot` command to begin autonomous end-to-end project execution. Autopilot will ask a small set of clarifying questions (SOW path, project type, client name, Jira preferences), then autonomously generate, validate, and self-review every artifact without further user involvement.

**If "Skip" selected:**

Acknowledge and exit:
```
No problem! You can run `/wire:dp-start` anytime to see project status and select a project.

Quick commands:
- `/wire:dp-status` - View all project statuses
- `/wire:dp-status <folder>` - View specific project details
- `/wire:dp-requirements-generate <folder>` - Start with requirements
```

## Edge Cases

### No Projects Found

If no status files found in `.wire/`:

```
# Data Platform Project Status

No projects found.

Would you like to create your first project?
```

Then use AskUserQuestion with:
- "Create first project" (with instructions)
- "Skip" (acknowledge and exit)

### All Projects Complete

If all projects have `current_phase: complete`:

```
# Data Platform Project Status

🎉 All projects complete!

| ID | Name | Type | Client | Completed |
|----|------|------|--------|-----------|
| ... | ... | ... | ... | [date] |

Would you like to create a new project or review a completed one?
```

## Output

This command outputs directly to the conversation - no files are written. It's designed to orient the user at the start of a session and guide them to productive work.

Execute the complete workflow as specified above.
