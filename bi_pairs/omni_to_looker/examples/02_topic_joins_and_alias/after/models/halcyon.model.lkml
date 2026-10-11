connection: "halcyon_bigquery"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: order_items {
  view_name: analytics__order_items
  label: "Order items"
  group_label: "Sales"
  sql_always_where: ${analytics__orders.customer_id} IS NOT NULL ;;
  join: analytics__orders {
    type: left_outer
    relationship: many_to_one
    sql_on: ${analytics__order_items.order_id} = ${analytics__orders.id} ;;
  }
  join: analytics__customers {
    type: left_outer
    relationship: many_to_one
    sql_on: ${analytics__orders.customer_id} = ${analytics__customers.id} ;;
  }
  join: referrers {
    from: analytics__customers
    type: left_outer
    relationship: many_to_one
    sql_on: ${analytics__orders.referrer_id} = ${referrers.id} ;;
  }
  join: analytics__returns {
    type: left_outer
    relationship: one_to_many
    sql_on: ${analytics__returns.order_item_id} = ${analytics__order_items.id} ;;
  }
}
