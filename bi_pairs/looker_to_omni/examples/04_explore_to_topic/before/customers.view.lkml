view: customers {
  sql_table_name: analytics.dim_customers ;;
  dimension: customer_id { primary_key: yes sql: ${TABLE}.customer_id ;; }
  dimension: region { sql: ${TABLE}.region ;; }
  dimension: email { sql: ${TABLE}.email ;; }
}
