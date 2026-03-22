# LookML Content Authoring Skill for Claude Code

## Overview

This skill enables Claude Code to create and modify LookML content (views, explores, models) directly in the local filesystem. Claude Code works with LookML projects stored in git repositories, typically in a `/looker` directory structure. The user provides specifications, schema information, and requirements; Claude Code generates properly formatted, validated LookML files.

## Architecture

Claude Code operates on the local filesystem AND can interact with Looker via MCP server:

| Operation | Approach |
|-----------|----------|
| Read existing LookML files | `cat`, `view` filesystem commands |
| Write new LookML files | `write`, `create` filesystem commands |
| Modify existing files | `edit`, `str_replace` commands |
| Understand schema | User-provided specs OR Looker MCP discovery |
| Validate syntax | LookML linting rules during generation |
| Deploy to Looker | MCP `create_project_file`, `update_project_file` |
| Test queries | MCP `query` tool |
| Check errors | MCP `pulse` tool |
| Version control | Standard git operations |

**Looker MCP Server Tools Available:**

| Tool | Purpose |
|------|---------|
| `dev_mode` | Enable development mode (required before file operations) |
| `get_models` | List available LookML models |
| `get_explores` | List explores in a model |
| `get_dimensions` | Get dimensions for an explore (with correct field names) |
| `get_measures` | Get measures for an explore |
| `create_project_file` | Create new file in Looker project |
| `update_project_file` | Update existing file |
| `delete_project_file` | Delete file from project |
| `query` | Execute LookML query and return results |
| `pulse` | Run health checks (e.g., `check_dashboard_errors`) |

Schema information can be obtained from:
1. User-provided spec files, YAML configs, or documentation
2. Looker MCP discovery tools (`get_dimensions`, `get_measures`)

## Project Structure

LookML projects typically follow this structure within the repository:

```
/looker/
├── manifest.lkml                    # Project manifest
├── models/
│   ├── analytics.model.lkml         # Model definitions
│   └── marketing.model.lkml
├── views/
│   ├── core/                        # Core/shared views
│   │   ├── dim_customer.view.lkml
│   │   └── dim_product.view.lkml
│   ├── staging/                     # Staging layer views
│   │   └── stg_orders.view.lkml
│   └── marts/                       # Business logic views
│       └── fct_orders.view.lkml
├── explores/                        # Explore definitions (optional)
│   └── orders.explore.lkml
├── dashboards/                      # LookML dashboards
│   └── executive_summary.dashboard.lkml
└── docs/                            # Documentation and specs
    ├── schema.yml                   # Schema definitions
    └── field_specs.md               # Field specifications
```

## When to Use This Skill

Activate this skill when the user requests:

- Creating new LookML views from schema specifications
- Modifying existing views or explores
- Adding dimensions, measures, or joins
- Refactoring LookML for better organization
- Converting dbt schema YAML to LookML views
- Building explores with proper join relationships
- Creating LookML dashboards
- Any task involving LookML file creation or modification

## Critical Rules

### 1. Always Reference Real Data Sources

Every view must connect to a real table or derived query. Never use placeholder or mock data.

❌ **FORBIDDEN PATTERN:**
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

✅ **REQUIRED PATTERN:**
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

## Development Workflow

### Phase 1: Understand the Task

For every LookML request, extract:

1. **Business goal**: What metric or analysis is needed?
2. **Data source details**: Database, schema, table name, column specifications
3. **Target artifacts**: View? Explore? Model updates?
4. **Relationships**: How does this connect to other views?
5. **Project location**: Path to LookML files (typically `/looker/`)

### Phase 2: Examine Existing Project

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

### Phase 3: Parse Schema Information

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

### Phase 4: Design the LookML

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

### Phase 5: Create the View File

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

### Phase 6: Update Model File

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

### Phase 7: Validate and Document

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

### Phase 8: Provide Handover Summary

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

## Phase 9: Validation - MANDATORY

**This phase is REQUIRED before marking any LookML work as complete.**

### 9.1 Validate Table and Column References

After generating LookML, you MUST cross-reference all SQL table and column names against the source schema file (e.g., `target_warehouse_ddl.sql`, `schema.yml`, or other provided schema documentation).

#### Validation Process

```bash
# 1. Extract all sql_table_name references from generated LookML
grep -h "sql_table_name:" /looker/views/**/*.view.lkml

# 2. Extract all ${TABLE}.column references
grep -oE '\$\{TABLE\}\.[a-zA-Z_][a-zA-Z0-9_]*' /looker/views/new_view.view.lkml | sort -u

# 3. Compare against the DDL or schema file
cat target_warehouse_ddl.sql
```

#### Checklist for Each View

For every view created or modified, verify:

- [ ] **Table name exists**: The `sql_table_name` or `FROM` clause references a table that exists in the DDL/schema
- [ ] **Database/schema path is correct**: Full path like `project.dataset.table` matches the actual structure
- [ ] **Every column exists**: Each `${TABLE}.column_name` reference matches an actual column in the source table
- [ ] **Column names are case-accurate**: BigQuery is case-sensitive for column names - verify exact casing
- [ ] **Data types are compatible**: Column types in DDL match the LookML dimension types used

#### Example Validation

Given this DDL:
```sql
-- target_warehouse_ddl.sql
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

#### Fixing Mismatches

If validation reveals mismatches:

1. **Update the LookML** to use exact column names from the DDL
2. **Do not assume** column names - always verify against source
3. **Document any ambiguity** if DDL is unclear or incomplete

### 9.2 Validate preferred_slug Parameters

If any view, explore, or dashboard uses `preferred_slug`, it MUST comply with these rules:

#### preferred_slug Syntax Rules

| Rule | Requirement |
|------|-------------|
| **Maximum length** | 255 characters |
| **Allowed characters** | Letters (A-Z, a-z), numbers (0-9), dashes (`-`), underscores (`_`) |
| **NOT allowed** | Spaces, special characters, unicode, dots, slashes |

#### Valid Examples

```lkml
# ✅ VALID preferred_slug values
explore: orders {
  preferred_slug: "orders-analysis"
}

view: customer_metrics {
  preferred_slug: "customer_metrics_v2"
}

dashboard: executive_summary {
  preferred_slug: "exec-summary-2024"
}

explore: revenue {
  preferred_slug: "revenue_by_region_q4_2024"
}
```

#### Invalid Examples

```lkml
# ❌ INVALID - contains spaces
preferred_slug: "orders analysis"

# ❌ INVALID - contains dots
preferred_slug: "orders.analysis"

# ❌ INVALID - contains special characters
preferred_slug: "orders@analysis!"

# ❌ INVALID - exceeds 255 characters
preferred_slug: "this_is_a_very_long_slug_that_goes_on_and_on_and_exceeds_the_maximum_allowed_length_of_two_hundred_and_fifty_five_characters_which_is_the_limit_set_by_looker_for_preferred_slug_parameters_so_this_will_fail_validation_when_you_try_to_deploy_it"
```

#### Validation Regex

Use this pattern to validate preferred_slug values:
```regex
^[A-Za-z0-9_-]{1,255}$
```

#### Automated Check

```bash
# Extract all preferred_slug values and validate
grep -h "preferred_slug:" /looker/**/*.lkml | while read line; do
  slug=$(echo "$line" | sed 's/.*preferred_slug: *"\([^"]*\)".*/\1/')
  
  # Check length
  if [ ${#slug} -gt 255 ]; then
    echo "ERROR: preferred_slug exceeds 255 chars: $slug"
  fi
  
  # Check characters
  if ! echo "$slug" | grep -qE '^[A-Za-z0-9_-]+$'; then
    echo "ERROR: preferred_slug contains invalid characters: $slug"
  fi
done
```

### 9.3 Final Validation Summary

Before completing any LookML task, provide a validation summary:

```markdown
## Validation Summary

### Table/Column Reference Check
- **Schema source**: `target_warehouse_ddl.sql`
- **Tables validated**: 3
- **Columns validated**: 24
- **Status**: ✅ All references valid

| View | Table | Columns Checked | Status |
|------|-------|-----------------|--------|
| employee_pto | `ra-development.analytics_seed.employee_pto` | 7 | ✅ Valid |
| employee_summary | derived_table | 4 | ✅ Valid |

### preferred_slug Validation
- **Slugs found**: 2
- **Status**: ✅ All valid

| Location | Slug | Length | Characters | Status |
|----------|------|--------|------------|--------|
| explore: employee_pto | `employee-pto-analysis` | 21 | ✅ | ✅ Valid |
| dashboard: hr_overview | `hr-overview-2024` | 16 | ✅ | ✅ Valid |

### Issues Found
- None

### Recommendations
- All LookML is ready for commit and Looker validation
```

---

## Phase 10: Looker Deployment & Validation - MANDATORY FOR PRODUCTION

This phase applies to ALL LookML content types (views, explores, models, dashboards).

### 10.1 Enable Development Mode

Before any file operations, enable dev mode:

```
mcp__looker-mcp__dev_mode(devMode: true)
```

### 10.2 Deploy Files to Looker

**CRITICAL:** Looker API requires `.lkml` extension, not `.lookml`

For **new files**:
```
mcp__looker-mcp__create_project_file(
  project_id: "analytics",
  file_path: "views/my_view.view.lkml",  # .lkml NOT .lookml!
  file_content: "<file contents>"
)
```

For **updates**:
```
mcp__looker-mcp__update_project_file(
  project_id: "analytics",
  file_path: "views/my_view.view.lkml",
  file_content: "<updated contents>"
)
```

### 10.3 Validate Content

**For Views/Explores:**
Test with a simple query:
```
mcp__looker-mcp__query(
  model: "model_name",
  explore: "explore_name",
  fields: ["view.dimension", "view.measure"],
  limit: 1
)
```

**For Dashboards:**
Test EVERY element's query individually:
```
mcp__looker-mcp__query(
  model: "model_name",
  explore: "explore_name",
  fields: [...element fields...],
  filters: {...element filters...},
  limit: 10
)
```

Then check for dashboard errors:
```
mcp__looker-mcp__pulse(action: "check_dashboard_errors")
```

### 10.4 Fix and Iterate

If errors occur:
1. Identify the failing query/element
2. Check field names against `get_dimensions`/`get_measures` output
3. Update the file via `update_project_file`
4. Re-test the query
5. Repeat until all queries pass

### 10.5 Deployment Validation Checklist

- [ ] Development mode enabled
- [ ] File uploaded with `.lkml` extension
- [ ] All queries execute without error
- [ ] Dashboard pulse check passes (for dashboards)
- [ ] Data returned (or data sparsity documented)

---

## Batch Deployment from Specification Files

When deploying multiple LookML files from specification documents:

### Workflow

1. **Read specification files:**
   - `/docs/design/dashboard-specification.md`
   - `/docs/design/dashboard-data-dictionary.md`
   - Or similar project-specific specs

2. **Identify all content to deploy:**
   - List all dashboards/views/explores defined in specs
   - Check which already exist in Looker
   - Determine creation order (views → explores → dashboards)

3. **Process each item:**
   ```
   For each LookML file:
     1. Generate/read local file
     2. Deploy to Looker
     3. Test queries
     4. Fix errors (iterate)
     5. Mark complete
     6. Move to next
   ```

4. **Report summary:**
   ```markdown
   ## Deployment Summary

   | File | Status | Queries Tested | Issues |
   |------|--------|----------------|--------|
   | financial.dashboard.lkml | ✅ Deployed | 12/12 passed | None |
   | health.dashboard.lkml | ✅ Deployed | 15/15 passed | None |
   | productivity.dashboard.lkml | ⚠️ Deployed | 14/16 passed | 2 sparse data |
   ```

### Single vs Batch Commands

**Single deployment:**
```
/deploy-lookml /lookml/dashboards/financial.dashboard.lookml analytics
```

**Batch deployment (all from specs):**
```
/deploy-lookml --all --spec /docs/design/dashboard-specification.md analytics
```

---

## Troubleshooting Guide

### Common Issues

| Error Pattern | Likely Cause | Solution |
|--------------|--------------|----------|
| "Unknown field" | Column name mismatch | Verify exact column name from schema |
| "Circular reference" | Field references itself | Check dimension SQL references |
| "Missing }" | Unbalanced braces | Count and match all `{` and `}` |
| "Invalid SQL" | Missing `;;` | Add `;;` after SQL blocks |
| "Duplicate field" | Same name in view | Rename or remove duplicate |

### MCP Deployment Errors

| Error Pattern | Symptom | Fix |
|---------------|---------|-----|
| **File extension** | "File extension is not allowed" | Use `.lkml` not `.lookml` for MCP API calls |
| **Explore alias** | "Unknown field" when field exists | Use explore name not view name (see below) |
| **Case sensitivity** | Field not found | Match exact case from `get_dimensions`/`get_measures` output |
| **Filter syntax** | Query fails on filter | Use Looker expressions: "7 days", "this month", "NOT NULL" |
| **Empty data** | Query returns null/0 | Not an error - widen date filter or accept sparse data |
| **Dev mode** | "Cannot modify files" | Call `dev_mode(devMode: true)` first |
| **Missing field** | "Must query at least one dimension or measure" | Verify field names exist in explore |

### Explore Alias Pattern (Critical)

When an explore uses `from:` to alias a view:

```lkml
explore: monthly_spending {
  from: agg_monthly_spending  # View name
  label: "Monthly Spending"
}
```

**Field references MUST use the explore name:**
- ✅ `monthly_spending.total_spending`
- ❌ `agg_monthly_spending.total_spending`

**Discovery:** Use `get_dimensions(model, explore)` to see the correct field names with proper prefixes.

### Validation Commands

After creating files, user should run in Looker IDE:
1. **Content Validator**: Checks LookML syntax
2. **Explore queries**: Test with sample queries
3. **SQL Runner**: Verify generated SQL

## Summary

This skill enables Claude Code to:

1. **Parse schema specifications** from YAML, JSON, DDL files, or natural language
2. **Generate valid LookML** following best practices and project conventions
3. **Create complete views** with dimensions, measures, and drill fields
4. **Build explores** with proper joins and relationships
5. **Maintain consistency** with existing project patterns
6. **Validate all references** against source DDL/schema files before completion
7. **Ensure preferred_slug compliance** with Looker's syntax requirements
8. **Provide clear handover** with documentation, validation summary, and next steps
9. **Deploy to Looker** via MCP server with automatic validation
10. **Test all queries** for views, explores, and dashboard elements
11. **Batch deploy** multiple files from specification documents

### Critical Workflow Reminder

**NEVER mark LookML work as complete without:**

1. ✅ Cross-checking ALL `sql_table_name` references against the DDL/schema
2. ✅ Verifying EVERY `${TABLE}.column` reference exists with correct casing
3. ✅ Validating any `preferred_slug` values meet syntax rules (alphanumeric, dashes, underscores only; max 255 chars)
4. ✅ Providing a validation summary table in the handover
5. ✅ Deploying to Looker and testing all queries (Phase 10)
6. ✅ Running dashboard pulse check for dashboard content

Always examine existing project files first, follow established conventions, validate against source schema, deploy to Looker, test queries, and provide comprehensive summaries of changes made.
