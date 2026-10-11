view: products {
  sql_table_name: `halcyon-prod.analytics.products` ;;

  dimension: category {
    sql: ${TABLE}.category ;;
  }

  dimension: category_group {
    sql: ${category} ;;
    case: {
      when: {
        sql: ${category} IN ('Tents', 'Sleeping bags') ;;
        label: "Camping"
      }
      when: {
        sql: ${category} = 'Jackets' ;;
        label: "Clothing"
      }
      else: "Other"
    }
  }

  dimension: id {
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: price {
    sql: ${TABLE}.price ;;
  }

  dimension: price_band {
    type: tier
    tiers: [0, 25, 100]
    style: integer
    sql: ${price} ;;
  }
}
