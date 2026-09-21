view: customers {
  sql_table_name: analytics.dim_customers ;;
  label: "Customers"

  dimension: customer_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.customer_id ;;
  }

  dimension: full_name {
    type: string
    sql: ${TABLE}.full_name ;;
    description: "First and last name"
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country_code ;;
    hidden: yes
  }

  measure: count {
    type: count
  }

  measure: total_lifetime_value {
    type: sum
    sql: ${TABLE}.lifetime_value ;;
    value_format_name: usd
  }
}
