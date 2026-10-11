view: analytics__orders {
  sql_table_name: `halcyon-prod.analytics.orders` ;;

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: status {
    sql: ${TABLE}.status ;;
  }

  dimension: status_label {
    sql: INITCAP(${TABLE}.status) ;;
  }

  dimension: total {
    type: number
    value_format_name: gbp
    sql: ${TABLE}.total ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }

  measure: average_order_value {
    type: number
    value_format_name: gbp
    sql: ${revenue} / NULLIF(${count}, 0) ;;
  }

  measure: count {
    type: count
  }

  measure: revenue {
    type: sum
    value_format_name: gbp
    sql: ${total} ;;
    filters: [status: "-cancelled,-test"]
  }
}
