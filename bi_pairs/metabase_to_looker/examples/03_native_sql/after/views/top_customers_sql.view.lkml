view: top_customers_sql {
  derived_table: {
    sql: SELECT c.name AS customer_name, SUM(o.total) AS revenue
      FROM `analytics.orders` o JOIN `analytics.customers` c ON o.customer_id = c.id
      WHERE o.total >= {% parameter min_total %} AND {% condition region %} `analytics.customers`.region {% endcondition %}
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 20 ;;
  }

  parameter: min_total {
    type: number
    label: "Min total"
    default_value: "10"
  }

  filter: region {
    type: string
    label: "Region"
  }

  dimension: customer_name {
    type: string
    label: "customer_name"
    sql: ${TABLE}.customer_name ;;
  }

  dimension: revenue {
    type: number
    label: "revenue"
    sql: ${TABLE}.revenue ;;
  }
}
