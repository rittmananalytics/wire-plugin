connection: "halcyon_bigquery"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders {
  view_name: analytics__orders
  label: "Orders"
}
