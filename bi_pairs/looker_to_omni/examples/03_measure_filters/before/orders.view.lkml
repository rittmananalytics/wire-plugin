view: orders {
  sql_table_name: analytics.fct_orders ;;

  dimension: order_id {
    primary_key: yes
    sql: ${TABLE}.order_id ;;
  }

  dimension: status {
    sql: ${TABLE}.status ;;
  }

  dimension: amount {
    type: number
    sql: ${TABLE}.amount ;;
  }

  dimension: is_gift {
    type: yesno
    sql: ${TABLE}.is_gift ;;
  }

  measure: completed_orders {
    type: count
    filters: [status: "complete"]
  }

  measure: large_orders {
    type: count
    filters: [amount: ">=100"]
  }

  measure: gift_orders {
    type: count
    filters: [is_gift: "Yes"]
  }

  measure: open_or_pending {
    type: count
    filters: [status: "open,pending"]
  }

  measure: not_cancelled_amount {
    type: sum
    sql: ${amount} ;;
    filters: [status: "-cancelled"]
  }

  measure: amount_with_status {
    type: sum
    sql: ${amount} ;;
    filters: [status: "-NULL"]
  }

  measure: uk_orders {
    type: count
    filters: [status: "%pend%"]
  }

  measure: recent_orders {
    type: count
    filters: [created_date: "30 days"]
  }

  measure: mixed_filter {
    type: count
    filters: [status: "open,-pending"]
  }

  measure: p90_amount {
    type: percentile
    percentile: 90
    sql: ${amount} ;;
  }

  measure: average_amount {
    type: average
    sql: ${amount} ;;
    value_format: "#,##0.00"
  }

  measure: aov {
    type: number
    sql: ${amount_with_status} / NULLIF(${completed_orders}, 0) ;;
  }
}
