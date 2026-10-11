view: daily_revenue {
  derived_table: {
    sql: SELECT DATE(created_at) AS order_date, SUM(total) AS revenue
      FROM `halcyon-prod.analytics.orders`
      GROUP BY 1 ;;
  }
  label: "Daily revenue"

  dimension: revenue {
    hidden: yes
    sql: ${TABLE}.revenue ;;
  }

  dimension_group: order_date {
    type: time
    timeframes: [raw, date, week, month]
    sql: ${TABLE}.order_date ;;
  }

  measure: total_revenue {
    type: sum
    sql: ${TABLE}.revenue ;;
  }
}
