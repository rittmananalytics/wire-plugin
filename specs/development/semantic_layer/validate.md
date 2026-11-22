---
wire_schema: "1.0"
command: validate
artifact: semantic_layer
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
preconditions:
  - artifact: semantic_layer
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate semantic layer (LookML) against standards, schema references, and best practices
argument-hint: <project-folder> [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the views, explores or measures for the slice only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. Run every check below against the slice's part. A check that needs the
   whole release (a cross-model consistency check) runs against the slice and
   the parts it depends on, and says so in the report.
3. On a ticket branch, write the result (`pass` or `fail`) to the ticket
   record's front matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`.

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

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
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
