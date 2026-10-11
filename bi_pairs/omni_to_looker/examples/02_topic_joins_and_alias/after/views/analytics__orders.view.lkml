view: analytics__orders {
  sql_table_name: `halcyon-prod.analytics.orders` ;;

  dimension: customer_id {
    sql: ${TABLE}.customer_id ;;
  }

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: referrer_id {
    sql: ${TABLE}.referrer_id ;;
  }
}
