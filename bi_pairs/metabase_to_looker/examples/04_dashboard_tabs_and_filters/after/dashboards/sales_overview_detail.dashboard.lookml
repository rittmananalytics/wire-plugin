- dashboard: sales_overview_detail
  title: Sales overview - Detail
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Metabase dashboard Sales overview (mb_to_lookml 0.1.0, experimental)
  elements:
  - name: return_rate_by_category_15
    title: Return rate by category
    model: halcyon
    explore: orders
    type: looker_bar
    fields:
    - products.category
    - orders.return_rate
    filters:
      orders.return_rate: '>=0.05'
      products.category: -Gift cards
    sorts:
    - products.category asc
    limit: 500
    row: 0
    col: 0
    width: 12
    height: 8
  - name: order_value_bands_16
    title: Order value bands
    model: halcyon
    explore: orders
    type: looker_column
    fields:
    - orders.total_bin_50
    - orders.count
    sorts:
    - orders.total_bin_50 asc
    limit: 500
    row: 0
    col: 12
    width: 12
    height: 8
