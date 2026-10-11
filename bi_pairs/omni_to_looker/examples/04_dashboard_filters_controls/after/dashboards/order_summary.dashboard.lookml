- dashboard: order_summary
  title: Order summary
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Omni document Order summary (omni_to_lookml 0.1.0, experimental)
  filters:
  - name: status
    title: Status
    type: field_filter
    default_value: complete,returned
    allow_multiple_values: true
    required: false
    ui_config:
      type: tag_list
      display: popover
    model: halcyon
    explore: orders
    field: analytics__orders.status
  elements:
  - name: orders_this_quarter_1
    title: Orders this quarter
    model: halcyon
    explore: orders
    type: single_value
    fields:
    - analytics__orders.count
    filters:
      analytics__orders.created_at_date: 1 quarter
    limit: 500
    row: 0
    col: 0
    width: 6
    height: 4
    listen:
      status: analytics__orders.status
  - name: revenue_by_status_and_month_2
    title: Revenue by status and month
    model: halcyon
    explore: orders
    type: looker_column
    fields:
    - analytics__orders.created_at_month
    - analytics__orders.status
    - analytics__orders.revenue
    - analytics__orders.count
    - per_order
    pivots:
    - analytics__orders.status
    filters:
      analytics__orders.status: -test
    sorts:
    - analytics__orders.created_at_month
    limit: 500
    dynamic_fields:
    - category: table_calculation
      expression: (${analytics__orders.revenue} / ${analytics__orders.count})
      label: Revenue per order
      table_calculation: per_order
      _kind_hint: measure
      _type_hint: number
      value_format_name: gbp
    stacking: normal
    row: 0
    col: 6
    width: 18
    height: 8
