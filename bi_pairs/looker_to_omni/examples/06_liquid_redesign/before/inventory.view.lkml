view: inventory {
  sql_table_name: analytics.fct_inventory ;;

  dimension: sku_id {
    primary_key: yes
    sql: ${TABLE}.sku_id ;;
  }

  dimension: dynamic_label {
    type: string
    sql: {% if _user_attributes['language'] == 'de' %} ${TABLE}.name_de {% else %} ${TABLE}.name_en {% endif %} ;;
  }

  dimension: sku_link {
    sql: ${TABLE}.sku_id ;;
    html: <a href="https://wms.acme.com/sku/{{ value }}">{{ rendered_value }}</a> ;;
  }

  parameter: measure_picker {
    type: unquoted
    allowed_value: { value: "units" }
    allowed_value: { value: "value" }
  }

  filter: warehouse_filter {
    type: string
  }

  measure: units_on_hand {
    type: sum
    sql: ${TABLE}.units_on_hand ;;
  }

  measure: units_running_total {
    type: running_total
    sql: ${units_on_hand} ;;
  }
}

view: inventory_daily_pdt {
  derived_table: {
    sql: SELECT snapshot_date, SUM(units_on_hand) AS units FROM analytics.fct_inventory GROUP BY 1 ;;
    sql_trigger_value: SELECT CURRENT_DATE ;;
  }
  dimension: snapshot_date { type: date sql: ${TABLE}.snapshot_date ;; }
  measure: units { type: sum sql: ${TABLE}.units ;; }
}
