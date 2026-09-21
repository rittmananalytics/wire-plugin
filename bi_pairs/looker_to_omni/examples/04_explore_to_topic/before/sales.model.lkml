connection: "acme"
include: "*.view.lkml"

explore: orders {
  label: "Sales"
  fields: [ALL_FIELDS*, -customers.email]
  sql_always_where: ${orders.customer_id} IS NOT NULL ;;
  access_filter: {
    field: customers.region
    user_attribute: region
  }
  join: customers {
    sql_on: ${orders.customer_id} = ${customers.customer_id} ;;
    relationship: many_to_one
    type: left_outer
  }
  join: reps {
    from: customers
    sql_on: ${orders.rep_id} = ${reps.customer_id} ;;
    relationship: many_to_one
    type: left_outer
  }
  join: order_lines {
    sql_on: ${orders.order_id} = ${order_lines.order_id} ;;
    relationship: one_to_many
    type: left_outer
  }
  join: skus {
    sql_on: ${order_lines.sku_id} = ${skus.sku_id} ;;
    relationship: many_to_one
    type: left_outer
  }
}
