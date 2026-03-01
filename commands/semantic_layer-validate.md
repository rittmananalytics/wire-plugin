---
description: Validate semantic layer
argument-hint: <project-folder>
---

# Validate semantic layer

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"2.1.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"semantic_layer-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"2.1.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate semantic layer (LookML) against standards, schema references, and best practices
argument-hint: <project-folder>
---

# Semantic Layer (LookML) Validation Command

## Purpose

Validate generated LookML files against quality standards, verify all table and column references match the source schema, check preferred_slug compliance, and ensure syntax correctness. This validation is MANDATORY before marking semantic layer work as complete.

## Usage

```bash
/wire:semantic_layer-validate YYYYMMDD_project_name
```

## Prerequisites

- Semantic layer must be generated (`/wire:semantic_layer-generate` complete)
- Source schema files available (DDL, dbt schema.yml, or schema specs)

## Workflow

### Step 1: Verify Semantic Layer Exists

**Process**:
1. Check that `semantic_layer.generate == complete` in status.md
2. Verify LookML files exist in the project's `/looker/` directory
3. Identify all `.view.lkml`, `.model.lkml`, `.explore.lkml`, and `.dashboard.lkml` files

**If not generated**:
```
Error: Semantic layer not generated yet.

Run `/wire:semantic_layer-generate <project>` first.
```

### Step 2: Run Validation Checks

#### 2.1 Syntax Validation

Verify all generated LookML files:

| Check | Rule | Severity |
|-------|------|----------|
| Balanced braces | All `{}` properly nested | Critical |
| SQL terminators | All SQL blocks end with `;;` | Critical |
| Dimension types | Every dimension has `type:` specified | Critical |
| SQL references | All use `${TABLE}.column` or `${view.field}` syntax | Critical |
| Primary keys | Defined with `primary_key: yes` where appropriate | Major |
| Labels | Business-friendly (not raw column names) | Major |
| Trailing commas | No trailing commas in lists | Major |
| Indentation | 2-space standard | Info |

**Common Syntax Errors to Check**:

```lkml
# ❌ WRONG: Missing type
dimension: name {
  sql: ${TABLE}.name ;;
}

# ✅ CORRECT
dimension: name {
  type: string
  sql: ${TABLE}.name ;;
}

# ❌ WRONG: Missing semicolons after SQL
dimension: name {
  type: string
  sql: ${TABLE}.name
}

# ✅ CORRECT
dimension: name {
  type: string
  sql: ${TABLE}.name ;;
}

# ❌ WRONG: Unbalanced braces
view: test {
  dimension: id {
    type: number
    sql: ${TABLE}.id ;;
}

# ✅ CORRECT
view: test {
  dimension: id {
    type: number
    sql: ${TABLE}.id ;;
  }
}
```

#### 2.2 Table and Column Reference Validation (MANDATORY)

Cross-reference ALL SQL table and column names against the source schema file (DDL, schema.yml, or other provided schema documentation).

**Validation Process**:

1. Extract all `sql_table_name` references from generated LookML
2. Extract all `${TABLE}.column` references from each view
3. Compare against the DDL or schema file
4. Verify case-sensitive column names (BigQuery is case-sensitive)

**For every view, verify**:

- [ ] **Table name exists**: The `sql_table_name` or `FROM` clause references a table that exists in the DDL/schema
- [ ] **Database/schema path is correct**: Full path like `project.dataset.table` matches the actual structure
- [ ] **Every column exists**: Each `${TABLE}.column_name` reference matches an actual column in the source table
- [ ] **Column names are case-accurate**: Verify exact casing matches the source
- [ ] **Data types are compatible**: Column types in DDL match the LookML dimension types used

**Example Validation**:

Given this DDL:
```sql
CREATE TABLE `ra-development.analytics_seed.employee_pto` (
  First_name STRING,
  Last_name STRING,
  email STRING,
  Start_date DATE,
  End_date DATE,
  Days FLOAT64,
  Type STRING
);
```

Validate the LookML references:

| LookML Reference | DDL Column | Status |
|-----------------|------------|--------|
| `${TABLE}.First_name` | `First_name STRING` | ✅ Match |
| `${TABLE}.Last_name` | `Last_name STRING` | ✅ Match |
| `${TABLE}.email` | `email STRING` | ✅ Match |
| `${TABLE}.Start_date` | `Start_date DATE` | ✅ Match |
| `${TABLE}.first_name` | - | ❌ Case mismatch! Should be `First_name` |
| `${TABLE}.pto_type` | - | ❌ Column doesn't exist! Should be `Type` |

**Fixing Mismatches**:

If validation reveals mismatches:
1. Update the LookML to use exact column names from the DDL
2. Do not assume column names - always verify against source
3. Document any ambiguity if DDL is unclear or incomplete

#### 2.3 preferred_slug Validation

If any view, explore, or dashboard uses `preferred_slug`, validate compliance:

**Syntax Rules**:

| Rule | Requirement |
|------|-------------|
| Maximum length | 255 characters |
| Allowed characters | Letters (A-Z, a-z), numbers (0-9), dashes (`-`), underscores (`_`) |
| NOT allowed | Spaces, special characters, unicode, dots, slashes |

**Validation Regex**: `^[A-Za-z0-9_-]{1,255}$`

**Valid Examples**:
```lkml
preferred_slug: "orders-analysis"
preferred_slug: "customer_metrics_v2"
preferred_slug: "exec-summary-2024"
```

**Invalid Examples**:
```lkml
# ❌ INVALID - contains spaces
preferred_slug: "orders analysis"

# ❌ INVALID - contains dots
preferred_slug: "orders.analysis"

# ❌ INVALID - contains special characters
preferred_slug: "orders@analysis!"

# ❌ INVALID - exceeds 255 characters
preferred_slug: "this_is_a_very_long_slug_that_..."
```

#### 2.4 Relationship Validation

For all explores and joins:

| Check | Rule | Severity |
|-------|------|----------|
| Explicit relationship | Joins have `relationship:` defined | Critical |
| Join type appropriate | `left_outer`, `inner`, etc. match data model | Major |
| SQL ON conditions | Reference correct fields from both views | Critical |
| View exists | All joined views are defined in the project | Critical |

#### 2.5 Documentation Validation

| Check | Rule | Severity |
|-------|------|----------|
| View descriptions | Every view has a `description` | Major |
| Complex field descriptions | Calculated/derived dimensions are documented | Major |
| Business logic comments | SQL with complex logic has comments | Info |
| Group labels | Related fields use `group_label` | Info |
| Measure formats | Numeric measures have `value_format_name` | Info |

#### 2.6 Quality Checklist

**Dimensions**:
- [ ] Every dimension has `type:` specified
- [ ] Primary keys defined with `primary_key: yes`
- [ ] Foreign keys marked `hidden: yes`
- [ ] Labels are business-friendly
- [ ] Group labels organize related fields

**Measures**:
- [ ] Appropriate measure types (sum, count, average, etc.)
- [ ] Value formats applied (usd, decimal_2, percent_1)
- [ ] Drill fields defined for exploration

**Dates**:
- [ ] Using `dimension_group` with appropriate timeframes
- [ ] Correct `datatype:` (date vs timestamp)
- [ ] `convert_tz: no` for date-only fields

### Step 3: Generate Validation Report

**Output Format**:

```markdown
## Semantic Layer (LookML) Validation: [PROJECT_NAME]

**Status:** PASS | FAIL

### Table/Column Reference Check
- **Schema source**: `[DDL file or schema.yml path]`
- **Tables validated**: [count]
- **Columns validated**: [count]
- **Status**: ✅ All references valid | ❌ Mismatches found

| View | Table | Columns Checked | Status |
|------|-------|-----------------|--------|
| [view_name] | `[full_table_path]` | [count] | ✅ Valid / ❌ [issue] |

### preferred_slug Validation
- **Slugs found**: [count]
- **Status**: ✅ All valid | ❌ Issues found | N/A (none used)

| Location | Slug | Length | Characters | Status |
|----------|------|--------|------------|--------|
| [explore/view/dashboard name] | `[slug]` | [len] | ✅/❌ | ✅ Valid / ❌ [issue] |

### Syntax Check
| Check | Status | Notes |
|-------|--------|-------|
| Balanced braces | ✅/❌ | |
| SQL terminators | ✅/❌ | |
| Dimension types | ✅/❌ | |
| SQL references | ✅/❌ | |
| Primary keys | ✅/❌ | |
| Labels | ✅/⚠️ | |

### Relationship Check
| Explore | Joins | Relationship Defined | SQL ON Valid | Status |
|---------|-------|---------------------|-------------|--------|

### Documentation Check
| View | Description | Fields Documented | Complex Logic Commented | Status |
|------|-------------|-------------------|------------------------|--------|

### Issues Found
- [list of issues, if any]

### Recommendations
- [actionable recommendations]

### Next Steps
1. **Fix issues** (if FAIL): Address listed problems, then re-validate
2. **Review with stakeholders**: `/wire:semantic_layer-review <project>`
3. **Sync in Looker IDE** - Pull changes and validate
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.semantic_layer section:
   ```yaml
   semantic_layer:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: [today]
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `semantic_layer`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Validation Failures

If checks fail:
- Set validate status to `fail`
- List all issues with severity (Critical / Major / Info)
- For table/column mismatches: show the exact mismatch and correct value
- For preferred_slug issues: show the invalid slug and the validation rule violated
- User must fix issues and re-validate

### No Schema Source Available

```
Warning: No DDL or schema.yml files found for cross-referencing.

Table/column reference validation cannot be performed without a schema source.
Proceeding with syntax and structure validation only.

To enable full validation, provide one of:
1. DDL file in artifacts/
2. dbt schema.yml files
3. Schema specification file
```

### Missing Source Tables

If `sql_table_name` references a table not in the schema:
```
❌ Table not found in schema: `project.dataset.unknown_table`

   View: [view_name]
   Line: sql_table_name: `project.dataset.unknown_table` ;;

   Available tables:
   - project.dataset.table_a
   - project.dataset.table_b
   - ...
```

## Output

This command:
- Validates LookML syntax and structure
- Cross-references all table/column names against source schema (MANDATORY)
- Checks preferred_slug compliance
- Validates explore relationships
- Checks documentation completeness
- Updates `status.md` with validation results
- Provides actionable feedback if issues found

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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
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
