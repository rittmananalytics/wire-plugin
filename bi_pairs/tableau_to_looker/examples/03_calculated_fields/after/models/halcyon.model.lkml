connection: "warehouse"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders {
  label: "Orders"
}
