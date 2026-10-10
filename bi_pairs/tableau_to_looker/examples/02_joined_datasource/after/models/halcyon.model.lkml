connection: "warehouse"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders_and_customers {
  label: "Orders and Customers"
  view_name: orders
  join: customers {
    type: inner
    relationship: many_to_one
    sql_on: ${orders.customer_id} = ${customers.customer_id} ;;
  }
}
