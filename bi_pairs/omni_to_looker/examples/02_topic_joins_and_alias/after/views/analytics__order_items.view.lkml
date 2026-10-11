view: analytics__order_items {
  sql_table_name: `halcyon-prod.analytics.order_items` ;;

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: order_id {
    sql: ${TABLE}.order_id ;;
  }

  measure: count {
    type: count
  }
}
