connection: "halcyon_bq"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: daily_orders_sql {
  label: "Daily orders (SQL)"
}

explore: orders {
  label: "Orders"
}

explore: top_customers_sql {
  label: "Top customers (SQL)"
}
