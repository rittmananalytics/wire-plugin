view: order_lines {
  sql_table_name: analytics.fct_order_lines ;;
  dimension: line_id { primary_key: yes sql: ${TABLE}.line_id ;; }
  dimension: order_id { sql: ${TABLE}.order_id ;; }
  dimension: sku_id { sql: ${TABLE}.sku_id ;; }
  measure: units { type: sum sql: ${TABLE}.units ;; }
}
