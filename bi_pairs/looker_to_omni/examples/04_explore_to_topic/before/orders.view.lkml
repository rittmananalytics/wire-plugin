view: orders {
  sql_table_name: analytics.fct_orders ;;
  dimension: order_id { primary_key: yes sql: ${TABLE}.order_id ;; }
  dimension: customer_id { sql: ${TABLE}.customer_id ;; }
  dimension: rep_id { sql: ${TABLE}.rep_id ;; }
  measure: count { type: count }
}
