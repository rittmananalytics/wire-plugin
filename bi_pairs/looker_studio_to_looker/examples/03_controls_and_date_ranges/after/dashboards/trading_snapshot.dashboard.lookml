- dashboard: trading_snapshot
  title: Trading Snapshot
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Looker Studio report Trading Snapshot (ls_to_lookml 0.1.0, experimental)
  filters:
  - name: Date range
    title: Date range
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    model: halcyon_ls
    explore: orders
    field: orders.order_date_date
  - name: Region
    title: Region
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    model: halcyon_ls
    explore: orders
    field: orders.region
  elements:
  - name: text_cd_title
    type: text
    body_text: Trading at a glance
    row: 0
    col: 0
    width: 12
    height: 1
  - name: kpi_metric_cd_kpi
    model: halcyon_ls
    explore: orders
    type: single_value
    fields:
    - orders.total_revenue
    limit: 500
    row: 1
    col: 0
    width: 4
    height: 2
    listen:
      Date range: orders.order_date_date
      Region: orders.region
  - name: simple_barchart_cd_bar
    model: halcyon_ls
    explore: orders
    type: looker_column
    fields:
    - orders.order_date_date
    - orders.region
    - orders.total_revenue
    sorts:
    - orders.total_revenue desc
    pivots:
    - orders.region
    limit: 10
    row: 1
    col: 4
    width: 10
    height: 6
    filters:
      orders.order_date_date: 13 months
    listen:
      Region: orders.region
  - name: simple_linechart_cd_line
    model: halcyon_ls
    explore: weekly_sessions_sql
    type: looker_line
    fields:
    - weekly_sessions_sql.week_start
    - weekly_sessions_sql.total_sessions
    sorts:
    - weekly_sessions_sql.week_start asc
    limit: 500
    row: 1
    col: 14
    width: 10
    height: 6
    listen:
      Date range: weekly_sessions_sql.week_start_as_date_date
  - name: simple_piechart_cd_pie
    model: halcyon_ls
    explore: orders
    type: looker_pie
    fields:
    - orders.region
    - orders.count
    sorts:
    - orders.count desc
    limit: 500
    row: 7
    col: 0
    width: 8
    height: 6
    listen:
      Region: orders.region
