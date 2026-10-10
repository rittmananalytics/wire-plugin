view: customers {
  sql_table_name: `retail.customers` ;;

  dimension: customer_id {
    type: string
    label: "customer_id"
    sql: ${TABLE}.customer_id ;;
  }

  dimension: segment {
    type: string
    label: "segment"
    sql: ${TABLE}.segment ;;
  }
}
