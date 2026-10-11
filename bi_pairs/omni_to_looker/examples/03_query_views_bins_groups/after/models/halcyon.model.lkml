connection: "halcyon_bigquery"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: daily_revenue {
}

explore: products {
  label: "Products"
}
