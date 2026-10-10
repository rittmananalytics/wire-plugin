- dashboard: sales_by_region_sales
  title: Sales by Region (Sales)
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Tableau worksheet Sales by Region (Sales) (twb_to_lookml 0.1.0, experimental)
  elements:
  - name: sales_by_region
    title: Sales by Region
    model: halcyon
    explore: orders
    type: looker_bar
    fields:
    - orders.region
    - orders.total_sales
    limit: 500
    row: 0
    col: 0
    width: 24
    height: 19
