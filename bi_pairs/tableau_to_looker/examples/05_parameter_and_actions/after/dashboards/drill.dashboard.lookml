- dashboard: drill
  title: Drill
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Tableau dashboard Drill (twb_to_lookml 0.1.0, experimental)
  filters:
  - name: Region
    title: Region
    type: field_filter
    default_value: ''
    model: halcyon
    explore: orders
    field: orders.region
    listens_to_filters: []
  elements:
  - name: regions
    title: Regions
    model: halcyon
    explore: orders
    type: looker_bar
    fields:
    - orders.region
    - orders.total_sales
    limit: 500
    row: 1
    col: 0
    width: 12
    height: 11
    listen:
      Region: orders.region
  - name: orders
    title: Orders
    model: halcyon
    explore: orders
    type: looker_grid
    fields:
    - orders.order_id
    - orders.total_sales
    limit: 500
    row: 1
    col: 12
    width: 12
    height: 11
    listen:
      Region: orders.region
