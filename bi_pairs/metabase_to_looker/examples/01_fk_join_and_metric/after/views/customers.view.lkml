view: customers {
  sql_table_name: `halcyon-prod.analytics.customers` ;;

  dimension: id {
    primary_key: yes
    type: number
    label: "Id"
    sql: ${TABLE}.id ;;
  }

  dimension: name {
    type: string
    label: "Name"
    sql: ${TABLE}.name ;;
  }

  dimension: region {
    type: string
    label: "Region"
    sql: ${TABLE}.region ;;
  }

  dimension_group: signup_ts {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    datatype: timestamp
    label: "Signup Ts"
    sql: TIMESTAMP_SECONDS(${TABLE}.signup_ts) ;;
  }
}
