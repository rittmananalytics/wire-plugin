connection: "halcyon_bq"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders {
  label: "Orders"
  join: products {
    type: left_outer
    relationship: many_to_one
    sql_on: ${orders.product_id} = ${products.id} ;;
  }
}
