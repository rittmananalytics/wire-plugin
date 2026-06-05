-- Snowflake: fct_subscription_metrics.sql

with subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

with_metrics as (
    select
        subscription_pk,
        customer_fk,
        started_ts,
        cancelled_ts,
        datediff(day, date(started_ts), date(cancelled_ts)) as duration_days,
        dateadd(day, 30, date(started_ts))                  as next_renewal_date,
        date_trunc('month', date(started_ts))               as cohort_month,
        datediff(day, started_ts, current_timestamp()) <= 90 as is_recent_signup,
        to_char(date(started_ts), 'YYYY-MM')                as cohort_label
    from subs
)

select * from with_metrics
