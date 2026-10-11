view: analytics__returns {
  sql_table_name: `halcyon-prod.analytics.returns` ;;

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: order_item_id {
    sql: ${TABLE}.order_item_id ;;
  }

  dimension: reason {
    sql: ${TABLE}.reason ;;
  }
}
