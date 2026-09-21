view: events {
  sql_table_name: analytics.fct_events ;;

  dimension: event_id {
    primary_key: yes
    sql: ${TABLE}.event_id ;;
  }

  dimension_group: occurred {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year, day_of_week, day_of_week_index, hour_of_day, week_of_year]
    sql: ${TABLE}.occurred_at ;;
    convert_tz: no
  }

  dimension_group: session {
    type: duration
    intervals: [minute, hour]
    sql_start: ${TABLE}.session_start_at ;;
    sql_end: ${TABLE}.session_end_at ;;
  }

  dimension: occurred_month_label {
    type: string
    sql: FORMAT_DATE('%b %Y', ${occurred_month}) ;;
  }

  measure: count {
    type: count
  }
}
