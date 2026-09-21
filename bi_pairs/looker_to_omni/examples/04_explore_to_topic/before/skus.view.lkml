view: skus {
  sql_table_name: analytics.dim_skus ;;
  dimension: sku_id { primary_key: yes sql: ${TABLE}.sku_id ;; }
  dimension: category { sql: ${TABLE}.category ;; }
}
