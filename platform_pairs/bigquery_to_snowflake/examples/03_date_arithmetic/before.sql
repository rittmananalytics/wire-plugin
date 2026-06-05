-- BigQuery: fct_subscription_metrics.sql
-- Heavy use of date/timestamp arithmetic — the most common per-line translation in any migration.

with subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

with_metrics as (
    select
        subscription_pk,
        customer_fk,
        started_ts,
        cancelled_ts,

        -- Subscription duration in days
        date_diff(date(cancelled_ts), date(started_ts), day) as duration_days,

        -- Renewal date: started + 30 days
        date_add(date(started_ts), interval 30 day) as next_renewal_date,

        -- Truncate started_ts to month for cohort analysis
        date_trunc(date(started_ts), month) as cohort_month,

        -- Was the subscription started in the last 90 days?
        timestamp_diff(current_timestamp(), started_ts, day) <= 90 as is_recent_signup,

        -- Format the cohort month for display
        format_date('%Y-%m', date(started_ts)) as cohort_label
    from subs
)

select * from with_metrics
