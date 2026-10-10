- dashboard: looker_pack
  title: Looker Pack
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Looker Studio report Looker Pack (ls_to_lookml 0.1.0, experimental)
  filters:
  - name: Date range
    title: Date range
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    model: halcyon
    explore: orders
    field: orders.created_month
  elements:
  - name: kpi_metric_cd_lkpi
    model: halcyon
    explore: orders
    type: single_value
    fields:
    - orders.total_revenue
    limit: 500
    row: 1
    col: 0
    width: 6
    height: 2
    listen:
      Date range: orders.created_month
  - name: simple_barchart_cd_lbar
    model: halcyon
    explore: orders
    type: looker_column
    fields:
    - orders.region
    - orders.total_revenue
    sorts:
    - orders.total_revenue desc
    limit: 500
    row: 1
    col: 6
    width: 18
    height: 6
    listen:
      Date range: orders.created_month
