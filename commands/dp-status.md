---
description: Report on all project statuses or specific project
argument-hint: [project-folder] or --archived
---

# Report on all project statuses or specific project

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
description: Report on all project statuses
---

# Data Platform Project Status Report

## Purpose

Generate a concise status report showing artifact lifecycle progress. Outputs a table format with minimal verbosity.

## Usage

```bash
/dp:status                    # Show all project statuses
/dp:status 20260210_rowcal    # Show detailed status for specific project
/dp:status --archived         # Show archived projects
```

## Workflow

### Step 1: Scan Project Folders

**Process**:
1. If `--archived` flag is present, use Glob: `.wire/archive/[0-9]*_*/status.md`
2. Otherwise, use Glob to find all status files: `.wire/[0-9]*_*/status.md`
3. Extract folder names from the matched file paths
4. Build list of all projects

### Step 2: Parse Status Files

**For each project**:
1. Read `status.md`
2. Parse YAML frontmatter to extract:
   - `project_id`, `project_name`, `client`
   - `current_phase`
   - `jira` section (if configured): `epic_key`, artifact issue keys
   - `artifacts` lifecycle states

**Artifact State Mapping**:
```
generate: not_started → ⬜, pending → ⏳, complete → ✅
validate: not_started → ⬜, pending → ⏳, pass → ✅, fail → ❌
review:   not_started → ⬜, pending → ⏳, approved → ✅, changes_requested → 🔄
ready:    auto-calculated from above
```

**Ready Calculation**:
```
# Standard artifacts (brief, wireframe, schema, lookml):
ready = ✅ if (generate=complete AND validate=pass AND review=approved)
ready = ⬜ otherwise

# Mock data (requires Snowflake table):
ready = ✅ if (generate=complete AND validate=pass AND review=approved AND snowflake_table is set)
ready = ⬜ otherwise
```

### Step 3: Generate Output

Both overview and detail modes use the same artifact lifecycle table format.

**Artifact lifecycle table** (used in both modes):

```
| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |
```

**Notes:**
- Catalog row shows "-" for Validate and Review columns since it's a generate-only artifact.
- Mock Data requires `snowflake_table` to be set for "Ready" status (shown in Highlights if missing)
- Artifacts with `not_applicable` state are hidden from the table
- If `jira.epic_key` exists, add a "Jira" column showing the artifact's `task_key` (e.g., `PROJ-124`)
- In overview mode, if Jira is configured, show the Epic key in the project header: `## name (ID | type | client | phase | PROJ-123)`

---

**If no specific project** (overview mode):

For each project, show a project header followed by the artifact lifecycle table and a Next action line:

```
# Data Platform Status

## omni_channel_retail_aws (20260205 | new_template | Internal | Prep)

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ⬜            | ⬜     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ⬜            | ⬜     |
| Mock Data  | ⬜          | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

**Next:** `/dp:wireframe:review 20260205_omni_channel_retail_aws`

---

Summary: 1 project(s) | 0 ready for Prod
```

**Overview format rules:**
- Each project gets an H2 header: `## name (ID | type | client | phase)`
- Followed by the standard artifact lifecycle table
- Followed by a single **Next:** line with the suggested command
- Projects separated by horizontal rules
- Summary line at the bottom

---

**If specific project requested** (detail mode):

Same artifact lifecycle table, plus a Highlights section with additional context:

```
# omni_channel_retail_aws - Status

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ⬜          | ⬜            | ⬜     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

### Highlights

- **Next:** Run `/dp:mockdata:validate 20260210_rowcal` to validate mock data
- **Wireframe:** https://lovable.dev/projects/[ID]
- **Snowflake:** Mock data not loaded yet (run `/dp:utils:load-mock-data` when ready)
```

**Highlights section rules:**
- Always include "Next:" with the suggested command
- Include "Jira:" line if `jira.epic_key` exists, showing Epic key and link
- Include "Wireframe:" line only if a Lovable URL exists in status.md
- Include "Snowflake:" line if mock data generated but `snowflake_table` not set
- Include "LookML:" line if LookML generated, showing file count (from `generated_files` array length)
- Include "Blockers:" only if there are open clarification items
- Include other notable items (e.g., "Brief approved by [stakeholder] on [date]")
- Keep to 2-5 bullet points max

### Step 4: Determine Next Action

**Logic for next action**:

First, read the `project_type` from status.md frontmatter. Use the appropriate phase ordering:

**Default ordering**: brief → wireframe → catalog → schema → mockdata → lookml (or for newer projects: requirements → workshops → pipeline_design → data_model → mockups → pipeline → dbt → semantic_layer → dashboards → data_quality → uat → deployment → training → documentation)

**Dashboard-first ordering** (for `dashboard_first` projects): requirements → mockups → viz_catalog → data_model → seed_data → dbt → semantic_layer → dashboards → data_refactor → data_quality → uat → deployment → training → documentation

For each artifact in the appropriate phase order:

**For Brief, Wireframe, Schema** (full lifecycle):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**For Catalog** (generate-only):
1. If `generate` is not `complete`: suggest generate command
2. Else: artifact is ready, check next artifact

**For Mock Data** (full lifecycle + snowflake_table for ready):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else if `snowflake_table` is not set: artifact NOT ready (show in Highlights)
5. Else: artifact is ready, check next artifact

**Note:** The load utility (`/dp:utils:load-mock-data`) is shown in Highlights when `snowflake_table` is not set, but does NOT block the normal lifecycle progression.

**For LookML** (full lifecycle):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, all Dev phase artifacts complete!

**Note:** When LookML is generated, show file count in Highlights (e.g., "LookML: 7 files generated").

**For Viz Catalog** (generate-only, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else: artifact is ready, check next artifact

**For Seed Data** (full lifecycle, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**For Data Refactor** (full lifecycle, `dashboard_first` projects only):
1. If `generate` is not `complete`: suggest generate command
2. Else if `validate` is not `pass`: suggest validate command
3. Else if `review` is not `approved`: suggest review command
4. Else: artifact is ready, check next artifact

**Command Mapping**:
```
Artifacts:
  brief.generate       → /dp:brief:generate
  brief.validate       → /dp:brief:validate
  brief.review         → /dp:brief:review
  wireframe.generate   → /dp:wireframe:generate
  wireframe.validate   → /dp:wireframe:validate
  wireframe.review     → /dp:wireframe:review
  catalog.generate     → /dp:catalog:generate
  schema.generate      → /dp:schema:generate
  schema.validate      → /dp:schema:validate
  schema.review        → /dp:schema:review
  mockdata.generate    → /dp:mockdata:generate
  mockdata.load        → /dp:utils:load-mock-data  ← utility, not lifecycle step
  mockdata.validate    → /dp:mockdata:validate
  mockdata.review      → /dp:mockdata:review
  lookml.generate      → /dp:lookml:generate
  lookml.validate      → /dp:lookml:validate
  lookml.review        → /dp:lookml:review

Dashboard-first artifacts:
  viz_catalog.generate    → /dp:viz_catalog:generate     ← generate-only (like catalog)
  seed_data.generate      → /dp:seed_data:generate
  seed_data.validate      → /dp:seed_data:validate
  seed_data.review        → /dp:seed_data:review
  data_refactor.generate  → /dp:data_refactor:generate
  data_refactor.validate  → /dp:data_refactor:validate
  data_refactor.review    → /dp:data_refactor:review
```

### Output Examples

**Overview (all projects)**:
```
# Data Platform Status

## rowcal (0001 | new_client | RowCal | Dev)

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| LookML     | ⬜          | ⬜          | ⬜            | ⬜     |

**Next:** `/dp:lookml:generate 0001_rowcal`

---

Summary: 1 project(s) | 0 ready for Prod
```

**Detail (specific project)**:
```
# rowcal - Status

| Artifact   | Generate   | Validate   | Review       | Ready |
|------------|------------|------------|--------------|-------|
| Brief      | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Wireframe  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Catalog    | ✅          | -          | -            | ✅     |
| Schema     | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| Mock Data  | ✅ complete | ✅ pass     | ✅ approved   | ✅     |
| LookML     | ✅ complete | ⬜          | ⬜            | ⬜     |

### Highlights

- **Next:** Run `/dp:lookml:validate 0001_rowcal` to validate LookML
- **Wireframe:** https://lovable.dev/projects/c3dbf5fc-a317-4698-a9b5-c6f0c82e9ff7
- **LookML:** 7 files generated (3 views, 1 explore, 3 dashboards)
```

### Step 4.5: Sync Jira Status (Optional)

If `jira` section exists in `status.md` and `jira.epic_key` is not null:

1. Follow the full reconciliation workflow in `dp/utils/jira_status_sync.md`
2. Pass the project folder
3. The utility will sync all local artifact states to Jira Sub-tasks, Tasks, and Epic
4. If any discrepancies are found, add them to the Highlights section
5. If Atlassian MCP is unavailable, skip silently

This ensures Jira stays in sync every time `/dp:status` is run.

## State Icons Reference

| Icon | Meaning |
|------|---------|
| ⬜ | Not started |
| ⏳ | In progress / Pending |
| ✅ | Complete / Pass / Approved |
| ❌ | Failed |
| 🔄 | Changes requested (needs iteration) |

## Error Handling

- **No projects found**: Display message suggesting to create a project folder
- **Invalid status file**: Skip project with warning
- **Missing frontmatter**: Use default "not_started" states

## Design Philosophy

**Minimal verbosity, maximum clarity.**

Key principles:
1. **Table-first**: Primary output is always a table
2. **Icon-driven**: Use emoji for quick visual scanning
3. **Next action**: Always show what to do next
4. **Auto-calculate Ready**: Don't require manual "ready" state management
5. **Phase awareness**: Group artifacts by their relevant phase

Execute the complete workflow as specified above.
