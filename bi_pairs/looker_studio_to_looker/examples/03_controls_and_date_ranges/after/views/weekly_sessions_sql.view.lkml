view: weekly_sessions_sql {
  derived_table: {
    sql: SELECT FORMAT_DATE('%Y-%m-%d', week_start) AS week_start, channel, sessions FROM analytics.web_weekly ;;
  }

  dimension: channel {
    type: string
    label: "channel"
    sql: ${TABLE}.channel ;;
  }

  dimension: sessions {
    type: number
    label: "sessions"
    sql: ${TABLE}.sessions ;;
  }

  dimension: week_start {
    type: string
    label: "week_start"
    sql: ${TABLE}.week_start ;;
  }

  dimension_group: week_start_as_date {
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    datatype: date
    convert_tz: no
    label: "week_start (as date)"
    sql: DATE(SAFE_CAST(${TABLE}.week_start AS TIMESTAMP)) ;;
  }

  measure: total_sessions {
    type: sum
    label: "sessions (sum)"
    sql: ${sessions} ;;
  }
}
