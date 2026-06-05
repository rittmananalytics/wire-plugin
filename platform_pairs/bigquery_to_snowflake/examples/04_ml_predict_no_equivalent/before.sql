-- BigQuery: fct_churn_predictions.sql
-- Uses BigQuery ML to score subscription churn risk.
-- This pattern has NO direct Snowflake equivalent.

with subs as (
    select * from {{ ref('dim_customer') }}
    where is_active_subscriber
),

predictions as (
    select
        customer_pk,
        predicted_churn_label,
        predicted_churn_probs[offset(0)].prob as churn_probability_30d
    from
        ml.predict(model `acme_analytics.subscription_churn_model_v3`,
            (
                select
                    customer_pk,
                    tenure_days,
                    avg_order_value,
                    days_since_last_order,
                    total_lifetime_orders,
                    accepts_marketing
                from subs
            )
        )
)

select * from predictions
