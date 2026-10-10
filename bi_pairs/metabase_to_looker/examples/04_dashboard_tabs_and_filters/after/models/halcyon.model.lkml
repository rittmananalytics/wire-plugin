connection: "halcyon_bq"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders {
  label: "Orders"
  join: customers {
    type: left_outer
    relationship: many_to_one
    sql_on: ${orders.customer_id} = ${customers.id} ;;
  }
  join: products {
    type: left_outer
    relationship: many_to_one
    sql_on: ${orders.product_id} = ${products.id} ;;
  }
}
