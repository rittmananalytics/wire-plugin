- dashboard: sales_by_segment_customers
  title: Sales by Segment (Customers)
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Tableau worksheet Sales by Segment (Customers) (twb_to_lookml 0.1.0, experimental)
  elements:
  - name: sales_by_segment
    title: Sales by Segment
    model: halcyon
    explore: orders_and_customers
    type: looker_bar
    fields:
    - customers.segment
    - orders.total_sales
    limit: 500
    row: 0
    col: 0
    width: 24
    height: 19
