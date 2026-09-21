view: accounts {
  sql_table_name: analytics.dim_accounts ;;

  dimension: account_id {
    primary_key: yes
    sql: ${TABLE}.account_id ;;
  }

  dimension: arr {
    type: number
    sql: ${TABLE}.annual_recurring_revenue ;;
  }

  dimension: arr_tier {
    type: tier
    tiers: [0, 10000, 50000, 250000]
    style: integer
    sql: ${arr} ;;
  }

  dimension: plan {
    sql: ${TABLE}.plan ;;
  }

  dimension: plan_family {
    case: {
      when: {
        sql: ${plan} = 'enterprise' ;;
        label: "Enterprise"
      }
      when: {
        sql: ${plan} IN ('team', 'business') ;;
        label: "Mid-market"
      }
      else: "Self-serve"
    }
  }

  dimension: health {
    case: {
      when: {
        sql: ${arr} > 100000 AND ${plan} = 'enterprise' ;;
        label: "Strategic"
      }
      else: "Standard"
    }
  }
}
