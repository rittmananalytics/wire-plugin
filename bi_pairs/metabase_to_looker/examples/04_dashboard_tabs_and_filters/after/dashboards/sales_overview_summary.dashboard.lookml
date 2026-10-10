- dashboard: sales_overview_summary
  title: Sales overview - Summary
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Metabase dashboard Sales overview (mb_to_lookml 0.1.0, experimental)
  filters:
  - name: Region
    title: Region
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    model: halcyon
    explore: orders
    field: customers.region
  - name: Date
    title: Date
    type: field_filter
    default_value: 30 days ago for 30 days
    allow_multiple_values: true
    required: false
    model: halcyon
    explore: orders
    field: orders.created_at_date
  elements:
  - name: text_11
    type: text
    title_text: Sales overview
    row: 0
    col: 0
    width: 24
    height: 1
  - name: text_12
    type: text
    body_text: Revenue for (the region filter)
    row: 1
    col: 0
    width: 24
    height: 1
  - name: revenue_by_region_13
    title: Revenue by region
    model: halcyon
    explore: orders
    type: looker_column
    fields:
    - customers.region
    - orders.revenue
    filters:
      orders.created_at_date: 12 months
    sorts:
    - orders.revenue desc
    limit: 500
    row: 2
    col: 0
    width: 12
    height: 6
    listen:
      Region: customers.region
  - name: orders_by_month_14
    title: Orders per month
    model: halcyon
    explore: orders
    type: looker_line
    fields:
    - orders.created_at_month
    - orders.count
    filters:
      orders.created_at_date: 6 months ago for 6 months
    sorts:
    - orders.created_at_month asc
    limit: 500
    row: 2
    col: 12
    width: 12
    height: 6
    listen:
      Region: customers.region
      Date: orders.created_at_date
