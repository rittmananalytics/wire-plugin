view: orders {
  sql_table_name: `halcyon-prod.analytics.orders` ;;

  dimension: customer_id {
    type: number
    label: "Customer Id"
    sql: ${TABLE}.customer_id ;;
  }

  dimension: id {
    primary_key: yes
    type: number
    label: "Id"
    sql: ${TABLE}.id ;;
  }

  dimension: is_returned {
    type: yesno
    label: "Is Returned"
    sql: ${TABLE}.is_returned ;;
  }

  dimension: order_code {
    type: string
    label: "Order Code"
    sql: ${TABLE}.`order code` ;;
  }

  dimension: product_id {
    type: number
    label: "Product Id"
    sql: ${TABLE}.product_id ;;
  }

  dimension: status {
    type: string
    label: "Status"
    sql: ${TABLE}.status ;;
  }

  dimension: total {
    type: number
    label: "Total"
    sql: ${TABLE}.total ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    datatype: timestamp
    label: "Created At"
    sql: ${TABLE}.created_at ;;
  }

  measure: count {
    type: count
    label: "Count"
  }

  measure: count_where_4d86d3 {
    type: count
    label: "Count where is returned is Yes"
    filters: [is_returned: "Yes"]
  }

  measure: return_rate {
    type: number
    label: "Return rate"
    sql: (${count_where_4d86d3}) / NULLIF(${count}, 0) ;;
  }
}
