view: analytics__orders {
  sql_table_name: `halcyon-prod.analytics.orders` ;;

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: status {
    sql: ${TABLE}.status ;;
  }

  dimension: total {
    sql: ${TABLE}.total ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [raw, date, month, quarter]
    sql: ${TABLE}.created_at ;;
  }

  measure: count {
    type: count
  }

  measure: revenue {
    type: sum
    sql: ${total} ;;
  }
}
