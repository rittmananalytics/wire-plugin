view: daily_orders_sql {
  derived_table: {
    sql: SELECT
        FORMAT_TIMESTAMP('%Y-%m', orders.created_at) AS orders_created_at_month,
        COUNT(DISTINCT orders.id) AS orders_order_count,
        SUM(orders.total) AS orders_revenue
      FROM `analytics.orders` AS orders
      WHERE orders.status != 'cancelled'
      GROUP BY 1
      ORDER BY 1 ;;
  }

  dimension: orders_created_at_month {
    type: string
    label: "orders_created_at_month"
    sql: ${TABLE}.orders_created_at_month ;;
  }

  dimension: orders_order_count {
    type: number
    label: "orders_order_count"
    sql: ${TABLE}.orders_order_count ;;
  }

  dimension: orders_revenue {
    type: number
    label: "orders_revenue"
    sql: ${TABLE}.orders_revenue ;;
  }
}
