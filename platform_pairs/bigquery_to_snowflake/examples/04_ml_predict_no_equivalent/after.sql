-- Snowflake: fct_churn_predictions.sql
-- ML.PREDICT has no direct Snowflake equivalent. Three viable migration paths are
-- documented below. The team's choice is recorded in migration_strategy.md; the
-- after.sql shown here implements the most common one (external function calling
-- a Cloud Function that wraps the original model artifact).

with subs as (
    select * from {{ ref('dim_customer') }}
    where is_active_subscriber
),

-- External function 'predict_churn' is a Snowflake external function (created
-- in target_setup) that POSTs the row payload to a Cloud Function endpoint
-- hosting the original BigQuery ML model artifact (exported as a TensorFlow
-- SavedModel). The cloud function returns the same prediction shape.
predictions as (
    select
        customer_pk,
        prediction_response:label::varchar                  as predicted_churn_label,
        prediction_response:probs[0]:prob::number(5, 4)     as churn_probability_30d
    from (
        select
            customer_pk,
            predict_churn(object_construct(
                'tenure_days',           tenure_days,
                'avg_order_value',       avg_order_value,
                'days_since_last_order', days_since_last_order,
                'total_lifetime_orders', total_lifetime_orders,
                'accepts_marketing',     accepts_marketing
            )) as prediction_response
        from subs
    )
)

select * from predictions
