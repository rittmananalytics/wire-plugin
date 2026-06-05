-- BigQuery: fct_subscription_metrics.sql

with subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

with_metrics as (
    select
        subscription_pk,
        customer_fk,
        started_ts,
        cancelled_ts,
        date_diff(date(cancelled_ts), date(started_ts), day)  as duration_days,
        date_add(date(started_ts), interval 30 day)           as next_renewal_date,
        date_trunc(date(started_ts), month)                   as cohort_month,
        timestamp_diff(current_timestamp(), started_ts, day) <= 90 as is_recent_signup,
        format_date('%Y-%m', date(started_ts))                as cohort_label
    from subs
)

select * from with_metrics
