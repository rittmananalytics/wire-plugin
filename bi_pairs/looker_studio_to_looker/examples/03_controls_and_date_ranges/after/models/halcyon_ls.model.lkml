connection: "halcyon_bq"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

explore: orders {
  label: "Orders"
}

explore: weekly_sessions_sql {
  label: "Weekly sessions SQL"
}
