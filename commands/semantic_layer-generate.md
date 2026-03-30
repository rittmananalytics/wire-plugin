---
description: Generate semantic layer (LookML, etc.)
argument-hint: <project-folder>
---

# Generate semantic layer (LookML, etc.)

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.6\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"semantic_layer-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.6\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate semantic layer (LookML views, explores, models) from data model design
argument-hint: <project-folder>
---

# Semantic Layer (LookML) Generate Command

## Purpose

Generate LookML views, explores, and model configurations based on the project's data model design, dbt schema files, and requirements. Creates properly formatted, validated LookML files following best practices and project conventions.

## Usage

```bash
/wire:semantic_layer-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- Data model design should be complete (preferred)
- dbt models should be generated (preferred, for schema.yml references)
- Existing LookML project structure (if extending existing project)

## Critical Rules

### 1. Always Reference Real Data Sources

Every view must connect to a real table or derived query. Never use placeholder or mock data.

**FORBIDDEN PATTERN:**
```lkml
view: employee_pto {
  derived_table: {
    sql:
      SELECT 'Alice' as name, 5 as days
      UNION ALL
      SELECT 'Bob' as name, 3 as days
    ;;
  }
}
```

**REQUIRED PATTERN:**
```lkml
view: employee_pto {
  sql_table_name: `project_id.dataset.employee_pto` ;;
}
```

### 2. Match Exact Column Names

Column names in LookML must exactly match the source table columns (case-sensitive for most databases). Always verify column names from the provided schema.

### 3. Follow Project Conventions

Before creating new files, examine existing LookML in the project to understand:
- Naming conventions (snake_case, prefixes like `dim_`, `fct_`)
- File organization patterns
- Label and group_label usage
- Value format conventions

### 4. Validate LookML Syntax

Ensure all generated LookML:
- Has balanced braces `{}`
- Uses correct parameter names
- Includes required fields (e.g., `type` for dimensions)
- Has proper semicolons `;;` after SQL blocks

### 5. Document Your Work

Add comments explaining:
- Complex SQL logic
- Business context for calculated fields
- Source of truth for data
- Any assumptions made

## Input Sources

Claude Code relies on user-provided information for schema details:

### 1. Schema Specification Files

YAML or JSON files describing tables and columns:

```yaml
# schema.yml
tables:
  - name: employee_pto
    database: ra-development
    schema: analytics_seed
    columns:
      - name: First_name
        type: STRING
        description: Employee's first name
      - name: Last_name
        type: STRING
        description: Employee's last name
      - name: email
        type: STRING
        description: Employee email address
      - name: Start_date
        type: DATE
        description: PTO start date
      - name: End_date
        type: DATE
        description: PTO end date
      - name: Days
        type: FLOAT64
        description: Number of PTO days
      - name: Type
        type: STRING
        description: Type of PTO (vacation, sick, etc.)
```

### 2. dbt Schema Files

Convert dbt `schema.yml` to LookML:

```yaml
# dbt schema.yml
models:
  - name: stg_orders
    description: Staged orders data
    columns:
      - name: order_id
        description: Primary key
        tests:
          - unique
          - not_null
      - name: customer_id
        description: Foreign key to customers
      - name: order_date
        description: Date order was placed
      - name: total_amount
        description: Order total in USD
```

### 3. Direct User Instructions

User provides table details in natural language or structured format within the conversation.

### 4. Existing LookML Files

Examine existing views to understand patterns and relationships.

## Workflow

### Step 1: Read Inputs and Understand the Task

**Process**:
1. Read `requirements/requirements_specification.md`
2. Read `design/data_model_specification.md` (if exists)
3. Read dbt schema.yml files from `dbt/models/` (if dbt models generated)
4. For every LookML request, extract:
   - **Business goal**: What metric or analysis is needed?
   - **Data source details**: Database, schema, table name, column specifications
   - **Target artifacts**: View? Explore? Model updates?
   - **Relationships**: How does this connect to other views?
   - **Project location**: Path to LookML files (typically `/looker/`)

### Step 2: Examine Existing Project

```bash
# List project structure
find /looker -name "*.lkml" | head -20

# Read the model file to understand existing setup
cat /looker/models/analytics.model.lkml

# Study existing view patterns
head -100 /looker/views/core/dim_customer.view.lkml
```

Key things to identify:
- Connection name used in models
- Include patterns (`include: "/views/**/*.view"`)
- Existing explores and their joins
- Naming conventions and style

### Step 3: Parse Schema Information

Extract from user-provided specs:

```python
# From schema.yml or user instructions, identify:
table_name = "employee_pto"
full_table_path = "`ra-development.analytics_seed.employee_pto`"
columns = [
    {"name": "First_name", "type": "STRING"},
    {"name": "Last_name", "type": "STRING"},
    {"name": "email", "type": "STRING"},
    {"name": "Start_date", "type": "DATE"},
    {"name": "End_date", "type": "DATE"},
    {"name": "Days", "type": "FLOAT64"},
    {"name": "Type", "type": "STRING"},
]
```

#### Map Data Types to LookML Types

| Source Type | LookML Type | Notes |
|-------------|-------------|-------|
| STRING, VARCHAR | `type: string` | |
| INT64, INTEGER | `type: number` | |
| FLOAT64, NUMERIC | `type: number` | Add `value_format` |
| DATE | `type: time` with `datatype: date` | Use `dimension_group` |
| TIMESTAMP, DATETIME | `type: time` with `datatype: timestamp` | Use `dimension_group` |
| BOOLEAN | `type: yesno` | |
| ARRAY | `type: string` | Use `ARRAY_TO_STRING()` |
| STRUCT | Access with dot notation | `${TABLE}.struct.field` |

### Step 4: Design the LookML

#### Choose Source Pattern

**Use `sql_table_name`** for direct table access:

```lkml
view: employee_pto {
  sql_table_name: `ra-development.analytics_seed.employee_pto` ;;
}
```

**Use `derived_table`** for transformations:

```lkml
view: employee_pto_summary {
  derived_table: {
    sql:
      SELECT
        email,
        SUM(Days) AS total_days
      FROM `ra-development.analytics_seed.employee_pto`
      GROUP BY 1
    ;;
  }
}
```

### Step 5: Create the View File

Write complete, properly formatted LookML:

```lkml
view: employee_pto {
  sql_table_name: `ra-development.analytics_seed.employee_pto` ;;

  # =============================================================================
  # PRIMARY KEY
  # =============================================================================

  dimension: pto_id {
    primary_key: yes
    type: string
    sql: CONCAT(${TABLE}.email, '-', CAST(${TABLE}.Start_date AS STRING)) ;;
    hidden: yes
    description: "Composite key: email + start date"
  }

  # =============================================================================
  # DIMENSIONS - STRING
  # =============================================================================

  dimension: first_name {
    type: string
    label: "First Name"
    sql: ${TABLE}.First_name ;;
    group_label: "Employee Details"
  }

  dimension: last_name {
    type: string
    label: "Last Name"
    sql: ${TABLE}.Last_name ;;
    group_label: "Employee Details"
  }

  dimension: employee_name {
    type: string
    label: "Employee Name"
    sql: CONCAT(${TABLE}.First_name, ' ', ${TABLE}.Last_name) ;;
    group_label: "Employee Details"
  }

  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
    group_label: "Employee Details"
  }

  dimension: pto_type {
    type: string
    label: "PTO Type"
    sql: ${TABLE}.Type ;;
    description: "Category of time off: vacation, sick, personal, etc."
  }

  # =============================================================================
  # DIMENSIONS - DATE/TIME
  # =============================================================================

  dimension_group: pto_start {
    type: time
    label: "PTO Start"
    timeframes: [raw, date, week, month, quarter, year]
    convert_tz: no
    datatype: date
    sql: ${TABLE}.Start_date ;;
  }

  dimension_group: pto_end {
    type: time
    label: "PTO End"
    timeframes: [raw, date, week, month, quarter, year]
    convert_tz: no
    datatype: date
    sql: ${TABLE}.End_date ;;
  }

  # =============================================================================
  # DIMENSIONS - NUMERIC
  # =============================================================================

  dimension: pto_days {
    type: number
    label: "PTO Days"
    sql: ${TABLE}.Days ;;
    value_format_name: decimal_1
    description: "Number of days for this PTO request"
  }

  # =============================================================================
  # DIMENSIONS - DERIVED/CALCULATED
  # =============================================================================

  dimension: is_extended_leave {
    type: yesno
    label: "Extended Leave (5+ Days)"
    sql: ${pto_days} >= 5 ;;
    description: "Flag for PTO requests of 5 or more days"
  }

  dimension: pto_days_tier {
    type: tier
    label: "PTO Days Tier"
    tiers: [1, 3, 5, 10]
    style: integer
    sql: ${pto_days} ;;
  }

  # =============================================================================
  # MEASURES
  # =============================================================================

  measure: count {
    type: count
    label: "PTO Request Count"
    drill_fields: [detail*]
  }

  measure: total_pto_days {
    type: sum
    label: "Total PTO Days"
    sql: ${pto_days} ;;
    value_format_name: decimal_1
  }

  measure: average_pto_days {
    type: average
    label: "Average PTO Days"
    sql: ${pto_days} ;;
    value_format_name: decimal_2
  }

  measure: employee_count {
    type: count_distinct
    label: "Employee Count"
    sql: ${email} ;;
    description: "Distinct count of employees with PTO"
  }

  # =============================================================================
  # DRILL SETS
  # =============================================================================

  set: detail {
    fields: [
      employee_name,
      email,
      pto_start_date,
      pto_end_date,
      pto_days,
      pto_type
    ]
  }
}
```

### Step 6: Update Model File

Add the view to an explore in the model:

```lkml
# In models/analytics.model.lkml

connection: "ra_dw_prod"

include: "/views/**/*.view.lkml"

# Add new explore
explore: employee_pto {
  label: "Employee PTO"
  group_label: "HR Analytics"
  description: "Employee paid time off tracking and analysis"

  # Join to employee dimension if available
  join: employees_dim {
    type: left_outer
    relationship: many_to_one
    sql_on: ${employee_pto.email} = ${employees_dim.email} ;;
  }
}
```

### Step 7: Validate and Document

#### Syntax Validation Checklist

Before finalizing any LookML file, verify:

- [ ] All braces `{}` are balanced
- [ ] All SQL blocks end with `;;`
- [ ] All dimensions have `type:` specified
- [ ] All `sql:` references use `${TABLE}.column` or `${view.field}` syntax
- [ ] Primary keys are defined where appropriate
- [ ] Labels are business-friendly
- [ ] No trailing commas in lists
- [ ] Proper indentation (2 spaces standard)

#### Common Syntax Errors to Avoid

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

### Step 8: Provide Handover Summary

After creating LookML files, provide a summary:

```markdown
## LookML Changes Summary

### Files Created/Modified

1. **Created**: `/looker/views/hr/employee_pto.view.lkml`
   - Source table: `ra-development.analytics_seed.employee_pto`
   - Dimensions: 8 (including composite primary key)
   - Measures: 4
   - Drill set defined for detail exploration

2. **Modified**: `/looker/models/analytics.model.lkml`
   - Added `employee_pto` explore
   - Configured join to `employees_dim` view

### Next Steps for User

1. **Review the generated LookML** for accuracy against your schema
2. **Commit changes to git**:
   ```bash
   git add looker/
   git commit -m "feat: Add employee PTO view and explore"
   git push
   ```
3. **Sync in Looker IDE** - Pull changes and validate
4. **Run LookML Validator** - Check for any errors
5. **Test queries** - Run sample queries in the explore to verify data
```

## Common Patterns

### Pattern 1: Dimension Table (Slowly Changing)

```lkml
view: dim_customer {
  sql_table_name: `project.dataset.dim_customer` ;;

  dimension: customer_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.customer_id ;;
    hidden: yes
  }

  dimension: customer_name {
    type: string
    sql: ${TABLE}.customer_name ;;
  }

  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
  }

  dimension: customer_segment {
    type: string
    sql: ${TABLE}.segment ;;
  }

  dimension: is_active {
    type: yesno
    sql: ${TABLE}.is_active ;;
  }

  dimension_group: created {
    type: time
    timeframes: [date, month, year]
    datatype: date
    sql: ${TABLE}.created_date ;;
  }

  measure: count {
    type: count
  }

  measure: active_customer_count {
    type: count
    filters: [is_active: "yes"]
  }
}
```

### Pattern 2: Fact Table (Transactional)

```lkml
view: fct_orders {
  sql_table_name: `project.dataset.fct_orders` ;;

  dimension: order_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.order_id ;;
  }

  dimension: customer_id {
    type: number
    sql: ${TABLE}.customer_id ;;
    hidden: yes
  }

  dimension: product_id {
    type: number
    sql: ${TABLE}.product_id ;;
    hidden: yes
  }

  dimension_group: order {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    datatype: timestamp
    sql: ${TABLE}.order_timestamp ;;
  }

  dimension: order_amount {
    type: number
    sql: ${TABLE}.order_amount ;;
    value_format_name: usd
    hidden: yes
  }

  dimension: quantity {
    type: number
    sql: ${TABLE}.quantity ;;
    hidden: yes
  }

  # Measures
  measure: count {
    type: count
    drill_fields: [order_id, order_date, order_amount]
  }

  measure: total_revenue {
    type: sum
    sql: ${order_amount} ;;
    value_format_name: usd
  }

  measure: average_order_value {
    type: average
    sql: ${order_amount} ;;
    value_format_name: usd
  }

  measure: total_quantity {
    type: sum
    sql: ${quantity} ;;
  }

  measure: order_count {
    type: count_distinct
    sql: ${order_id} ;;
  }
}
```

### Pattern 3: Aggregated Derived Table (PDT)

```lkml
view: customer_order_summary {
  derived_table: {
    sql:
      SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS lifetime_orders,
        SUM(order_amount) AS lifetime_value,
        MIN(order_timestamp) AS first_order_date,
        MAX(order_timestamp) AS last_order_date,
        DATE_DIFF(CURRENT_DATE(), DATE(MAX(order_timestamp)), DAY) AS days_since_last_order
      FROM `project.dataset.fct_orders`
      GROUP BY 1
    ;;

    # PDT configuration
    datagroup_trigger: daily_refresh
    indexes: ["customer_id"]
  }

  dimension: customer_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.customer_id ;;
    hidden: yes
  }

  dimension: lifetime_orders {
    type: number
    sql: ${TABLE}.lifetime_orders ;;
  }

  dimension: lifetime_value {
    type: number
    sql: ${TABLE}.lifetime_value ;;
    value_format_name: usd
  }

  dimension: lifetime_value_tier {
    type: tier
    tiers: [0, 100, 500, 1000, 5000]
    style: integer
    sql: ${lifetime_value} ;;
  }

  dimension_group: first_order {
    type: time
    timeframes: [date, month, year]
    datatype: timestamp
    sql: ${TABLE}.first_order_date ;;
  }

  dimension_group: last_order {
    type: time
    timeframes: [date, month, year]
    datatype: timestamp
    sql: ${TABLE}.last_order_date ;;
  }

  dimension: days_since_last_order {
    type: number
    sql: ${TABLE}.days_since_last_order ;;
  }

  dimension: is_repeat_customer {
    type: yesno
    sql: ${lifetime_orders} > 1 ;;
  }

  measure: average_lifetime_value {
    type: average
    sql: ${lifetime_value} ;;
    value_format_name: usd
  }

  measure: average_lifetime_orders {
    type: average
    sql: ${lifetime_orders} ;;
    value_format_name: decimal_1
  }
}
```

### Pattern 4: Explore with Multiple Joins

```lkml
explore: orders {
  label: "Orders Analysis"
  description: "Analyze orders with customer, product, and geographic context"

  # Base view
  from: fct_orders

  # Customer dimension
  join: dim_customer {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fct_orders.customer_id} = ${dim_customer.customer_id} ;;
  }

  # Product dimension
  join: dim_product {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fct_orders.product_id} = ${dim_product.product_id} ;;
  }

  # Customer lifetime metrics
  join: customer_order_summary {
    type: left_outer
    relationship: one_to_one
    sql_on: ${fct_orders.customer_id} = ${customer_order_summary.customer_id} ;;
  }

  # Always filter to completed orders (optional)
  always_filter: {
    filters: [fct_orders.order_status: "completed"]
  }
}
```

### Pattern 5: Native Derived Table with Parameters

```lkml
view: dynamic_date_comparison {
  derived_table: {
    explore_source: orders {
      column: order_date { field: fct_orders.order_date }
      column: total_revenue { field: fct_orders.total_revenue }
      column: order_count { field: fct_orders.order_count }

      bind_filters: {
        from_field: dynamic_date_comparison.date_filter
        to_field: fct_orders.order_date
      }
    }
  }

  filter: date_filter {
    type: date
  }

  dimension: order_date {
    type: date
    sql: ${TABLE}.order_date ;;
  }

  measure: total_revenue {
    type: sum
    sql: ${TABLE}.total_revenue ;;
    value_format_name: usd
  }

  measure: order_count {
    type: sum
    sql: ${TABLE}.order_count ;;
  }
}
```

## BigQuery-Specific Patterns

### Handling Nested and Repeated Fields

```lkml
view: events {
  sql_table_name: `project.dataset.events` ;;

  # Unnest repeated field
  dimension: event_param_key {
    type: string
    sql: ep.key ;;
  }

  dimension: event_param_value {
    type: string
    sql: ep.value.string_value ;;
  }
}

# In the explore, use UNNEST
explore: events {
  join: event_params {
    type: left_outer
    relationship: one_to_many
    sql: LEFT JOIN UNNEST(${events.event_params}) AS ep ;;
  }
}
```

### Partitioned Table Optimization

```lkml
view: partitioned_events {
  sql_table_name: `project.dataset.events` ;;

  # Always include partition filter for performance
  dimension_group: event {
    type: time
    timeframes: [raw, date, week, month]
    datatype: timestamp
    sql: ${TABLE}._PARTITIONTIME ;;
  }
}

explore: partitioned_events {
  # Require partition filter
  always_filter: {
    filters: [partitioned_events.event_date: "last 30 days"]
  }
}
```

### Working with JSON Fields

```lkml
dimension: metadata_source {
  type: string
  sql: JSON_EXTRACT_SCALAR(${TABLE}.metadata, '$.source') ;;
}

dimension: metadata_version {
  type: number
  sql: CAST(JSON_EXTRACT_SCALAR(${TABLE}.metadata, '$.version') AS INT64) ;;
}
```

## LookML Dashboard Template

```lkml
- dashboard: executive_summary
  title: "Executive Summary"
  layout: newspaper
  preferred_viewer: dashboards-next
  description: "Key business metrics overview"

  filters:
    - name: date_range
      title: "Date Range"
      type: date_filter
      default_value: "last 30 days"
      allow_multiple_values: false

  elements:
    - title: "Total Revenue"
      name: total_revenue_tile
      model: analytics
      explore: orders
      type: single_value
      fields: [fct_orders.total_revenue]
      listen:
        date_range: fct_orders.order_date
      row: 0
      col: 0
      width: 6
      height: 4

    - title: "Revenue Over Time"
      name: revenue_trend
      model: analytics
      explore: orders
      type: looker_line
      fields: [fct_orders.order_date, fct_orders.total_revenue]
      sorts: [fct_orders.order_date]
      listen:
        date_range: fct_orders.order_date
      row: 4
      col: 0
      width: 12
      height: 8

    - title: "Revenue by Segment"
      name: revenue_by_segment
      model: analytics
      explore: orders
      type: looker_pie
      fields: [dim_customer.customer_segment, fct_orders.total_revenue]
      sorts: [fct_orders.total_revenue desc]
      listen:
        date_range: fct_orders.order_date
      row: 4
      col: 12
      width: 12
      height: 8
```

## Quality Checklist

Before finalizing any LookML work, verify:

### Syntax
- [ ] All braces `{}` are balanced
- [ ] All SQL blocks end with `;;`
- [ ] Proper indentation (2 spaces)
- [ ] No trailing commas

### Dimensions
- [ ] Every dimension has `type:` specified
- [ ] Primary keys defined with `primary_key: yes`
- [ ] Foreign keys marked `hidden: yes`
- [ ] Labels are business-friendly
- [ ] Group labels organize related fields

### Measures
- [ ] Appropriate measure types (sum, count, average, etc.)
- [ ] Value formats applied (usd, decimal_2, percent_1)
- [ ] Drill fields defined for exploration

### Dates
- [ ] Using `dimension_group` with appropriate timeframes
- [ ] Correct `datatype:` (date vs timestamp)
- [ ] `convert_tz: no` for date-only fields

### Documentation
- [ ] View has description
- [ ] Complex fields have descriptions
- [ ] Comments explain business logic

### Relationships
- [ ] Joins have explicit `relationship:` defined
- [ ] Join types are appropriate (left_outer, inner)
- [ ] SQL ON conditions reference correct fields

## LookML Project Structure Reference

```
/looker/
├── manifest.lkml
├── models/
│   ├── analytics.model.lkml
│   └── marketing.model.lkml
├── views/
│   ├── core/
│   ├── staging/
│   └── marts/
├── explores/
├── dashboards/
└── docs/
```

### Step 9: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.semantic_layer section:
   ```yaml
   semantic_layer:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: [today]
   ```
3. Write updated status.md

### Step 10: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `semantic_layer`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 11: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `semantic_layer`
- `artifact_name`: `Semantic Layer`
- `file_path`: `.wire/releases/[release_folder]/dev/semantic_layer.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 12: Confirm and Suggest Next Steps

**Output**:
```
## Semantic Layer (LookML) Generated Successfully

**Files Created/Modified:**
[list all generated LookML files]

### Validation Summary
- Tables validated: [count]
- Columns validated: [count]
- Status: [all valid / issues found]

### Next Steps

1. **Validate semantic layer**: `/wire:semantic_layer-validate <project>`
   This will cross-reference all table/column references against the source DDL
2. After validation, review: `/wire:semantic_layer-review <project>`
3. **Sync in Looker IDE** - Pull changes and validate
4. **Test queries** - Run sample queries in the explore to verify data
```

## Edge Cases

### Prerequisites Not Met

If data model or requirements not approved:
```
Error: Required prerequisites not complete.

Current status:
- Requirements: [status]
- Data Model: [status]

Complete these first:
- /wire:requirements-review <project>
- /wire:data_model-review <project>
```

### No Schema Information Available

```
Error: No schema information found.

I need one of the following to generate LookML:
1. dbt schema.yml files in dbt/models/
2. DDL/schema files in artifacts/
3. Direct table/column specifications

Please provide schema information and try again.
```

### Existing LookML Project Found

If LookML files already exist:
```
Found existing LookML project at: [path]
- [count] views
- [count] explores
- [count] models

How should I proceed?
1. Extend existing project (add new views alongside existing)
2. Replace all LookML files
3. Create in a separate directory
```

## Troubleshooting Guide

| Error Pattern | Likely Cause | Solution |
|--------------|--------------|----------|
| "Unknown field" | Column name mismatch | Verify exact column name from schema |
| "Circular reference" | Field references itself | Check dimension SQL references |
| "Missing }" | Unbalanced braces | Count and match all `{` and `}` |
| "Invalid SQL" | Missing `;;` | Add `;;` after SQL blocks |
| "Duplicate field" | Same name in view | Rename or remove duplicate |

## Output

This command creates:
- LookML view files in the project's `/looker/views/` directory
- LookML explore configurations
- Model file updates
- Validation summary with table/column reference checks
- Updates `status.md`

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
