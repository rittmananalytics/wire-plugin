- dashboard: return_rate_by_category_question
  title: Return rate by category
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Metabase question Return rate by category (mb_to_lookml 0.1.0, experimental)
  elements:
  - name: return_rate_by_category
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
    width: 24
    height: 12
