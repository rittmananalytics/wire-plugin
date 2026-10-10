- dashboard: sql_reports
  title: SQL reports
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Metabase dashboard SQL reports (mb_to_lookml 0.1.0, experimental)
  filters:
  - name: Region
    title: Region
    type: field_filter
    default_value: North,South^, East
    allow_multiple_values: true
    required: false
    model: halcyon
    explore: top_customers_sql
    field: top_customers_sql.region
  elements:
  - name: top_customers_sql_21
    title: Top customers (SQL)
    model: halcyon
    explore: top_customers_sql
    type: looker_grid
    fields:
    - top_customers_sql.customer_name
    - top_customers_sql.revenue
    sorts:
    - top_customers_sql.revenue desc
    limit: 500
    row: 0
    col: 0
    width: 12
    height: 8
    listen:
      Region: top_customers_sql.region
  - name: daily_orders_sql_22
    title: Daily orders (SQL)
    model: halcyon
    explore: daily_orders_sql
    type: looker_line
    fields:
    - daily_orders_sql.orders_created_at_month
    - daily_orders_sql.orders_order_count
    - daily_orders_sql.orders_revenue
    sorts:
    - daily_orders_sql.orders_created_at_month asc
    limit: 500
    row: 0
    col: 12
    width: 12
    height: 8
