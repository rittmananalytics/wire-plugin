- dashboard: exec_summary
  title: Exec Summary
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Tableau dashboard Exec Summary (twb_to_lookml 0.1.0, experimental)
  elements:
  - name: text_2
    type: text
    title_text: Executive summary
    row: 0
    col: 0
    width: 24
    height: 1
  - name: total
    title: Total
    model: halcyon
    explore: orders
    type: single_value
    fields:
    - orders.total_sales
    limit: 500
    row: 1
    col: 0
    width: 6
    height: 3
  - name: by_region
    title: By Region
    model: halcyon
    explore: orders
    type: looker_column
    fields:
    - orders.total_sales
    - orders.region
    limit: 500
    row: 1
    col: 6
    width: 18
    height: 3
  - name: trend
    title: Trend
    model: halcyon
    explore: orders
    type: looker_area
    fields:
    - orders.total_sales
    - orders.order_date_month
    limit: 500
    row: 4
    col: 0
    width: 24
    height: 9
