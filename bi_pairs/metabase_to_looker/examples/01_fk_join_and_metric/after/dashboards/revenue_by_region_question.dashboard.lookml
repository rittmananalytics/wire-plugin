- dashboard: revenue_by_region_question
  title: Revenue by region
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Metabase question Revenue by region (mb_to_lookml 0.1.0, experimental)
  elements:
  - name: revenue_by_region
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
    row: 0
    col: 0
    width: 24
    height: 12
