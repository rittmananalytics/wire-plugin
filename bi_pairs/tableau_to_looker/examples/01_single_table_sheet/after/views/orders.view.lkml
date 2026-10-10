view: orders {
  sql_table_name: `retail.orders` ;;

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
