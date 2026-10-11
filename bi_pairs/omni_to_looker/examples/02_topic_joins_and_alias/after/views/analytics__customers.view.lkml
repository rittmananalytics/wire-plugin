view: analytics__customers {
  sql_table_name: `halcyon-prod.analytics.customers` ;;

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: name {
    sql: ${TABLE}.name ;;
  }
}
