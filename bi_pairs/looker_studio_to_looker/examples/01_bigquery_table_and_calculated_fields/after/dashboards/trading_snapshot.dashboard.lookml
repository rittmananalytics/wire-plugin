- dashboard: trading_snapshot
  title: Trading Snapshot
  layout: newspaper
  preferred_viewer: dashboards-next
  description: Migrated from Looker Studio report Trading Snapshot (ls_to_lookml 0.1.0, experimental)
  elements:
  - name: simple_table_cd_table
    model: halcyon_ls
    explore: orders
    type: looker_grid
    fields:
    - orders.region
    - orders.region_upper
    - orders.total_margin_rate
    - orders.chart_margin
    limit: 500
    row: 0
    col: 0
    width: 24
    height: 8
