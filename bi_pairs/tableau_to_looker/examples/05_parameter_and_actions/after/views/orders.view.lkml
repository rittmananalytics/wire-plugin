view: orders {
  sql_table_name: `retail.orders` ;;

  parameter: top_n {
    type: number
    label: "Top N"
    default_value: "10"
  }

  dimension: above_threshold {
    type: yesno
    label: "Above Threshold"
    sql: ${orders.sales} > {% parameter top_n %} ;;
  }

  dimension: order_id {
    type: number
    label: "order_id"
    sql: ${TABLE}.order_id ;;
  }

  dimension: region {
    type: string
    label: "region"
    sql: ${TABLE}.region ;;
  }

  dimension: sales {
    type: number
    label: "sales"
    hidden: yes
    sql: ${TABLE}.sales ;;
  }

  measure: total_sales {
    type: sum
    label: "sales"
    sql: ${sales} ;;
  }
}
