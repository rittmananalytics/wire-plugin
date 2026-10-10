view: orders {
  sql_table_name: `halcyon-prod.analytics.orders` ;;

  dimension: is_returned {
    type: yesno
    label: "is_returned"
    sql: ${TABLE}.is_returned ;;
  }

  dimension: margin {
    type: number
    label: "margin"
    sql: ${TABLE}.margin ;;
  }

  dimension: margin_rate {
    type: number
    label: "Margin rate"
    sql: SAFE_DIVIDE(${margin}, ${revenue}) ;;
  }

  dimension: order_code {
    type: string
    label: "order code"
    sql: ${TABLE}.`order code` ;;
  }

  dimension: orders {
    type: number
    label: "orders"
    sql: ${TABLE}.orders ;;
  }

  dimension: region {
    type: string
    label: "region"
    sql: ${TABLE}.region ;;
  }

  dimension: region_upper {
    type: string
    label: "Region (upper)"
    sql: UPPER(${region}) ;;
  }

  dimension: revenue {
    type: number
    label: "revenue"
    sql: ${TABLE}.revenue ;;
  }

  dimension_group: order_date {
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    datatype: date
    convert_tz: no
    label: "order_date"
    sql: ${TABLE}.order_date ;;
  }

  measure: chart_margin {
    type: number
    label: "Chart margin"
    sql: SAFE_DIVIDE(SUM(${margin}), SUM(${revenue})) ;;
  }

  measure: revenue_per_order {
    type: number
    label: "Revenue per order"
    sql: SAFE_DIVIDE(SUM(${revenue}), SUM(${orders})) ;;
  }

  measure: total_margin_rate {
    type: sum
    label: "Margin rate (sum)"
    sql: ${margin_rate} ;;
  }
}
