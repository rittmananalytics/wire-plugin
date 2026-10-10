view: orders {
  sql_table_name: `retail.orders` ;;

  dimension: order_id {
    type: number
    label: "order_id"
    sql: ${TABLE}.order_id ;;
  }

  dimension: profit {
    type: number
    label: "profit"
    hidden: yes
    sql: ${TABLE}.profit ;;
  }

  dimension: region {
    type: string
    label: "region"
    sql: ${TABLE}.region ;;
  }

  dimension: region_upper {
    type: string
    label: "Region Upper"
    sql: CONCAT(UPPER(${orders.region}), ' region') ;;
  }

  dimension: sales {
    type: number
    label: "sales"
    hidden: yes
    sql: ${TABLE}.sales ;;
  }

  dimension: size_band {
    type: string
    label: "Size Band"
    sql: CASE WHEN ${orders.sales} > 1000 THEN 'Big' ELSE 'Small' END ;;
  }

  measure: profit_ratio {
    type: number
    label: "Profit Ratio"
    sql: (${orders.total_profit}) / NULLIF(${orders.total_sales}, 0) ;;
  }

  measure: total_profit {
    type: sum
    label: "profit"
    sql: ${profit} ;;
  }

  measure: total_sales {
    type: sum
    label: "sales"
    sql: ${sales} ;;
  }
}
