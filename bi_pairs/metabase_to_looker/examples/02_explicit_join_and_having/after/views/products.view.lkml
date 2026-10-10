view: products {
  sql_table_name: `halcyon-prod.analytics.products` ;;

  dimension: category {
    type: string
    label: "Category"
    sql: ${TABLE}.category ;;
  }

  dimension: id {
    primary_key: yes
    type: number
    label: "Id"
    sql: ${TABLE}.id ;;
  }

  dimension: title {
    type: string
    label: "Title"
    sql: ${TABLE}.title ;;
  }
}
