-- Snowflake: fct_subscription_metrics.sql
-- DATEDIFF / DATEADD swap names AND argument order; INTERVAL literals replaced by unit-keyword positional args.

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
        -- BQ: date_diff(end, start, unit) — Snowflake: datediff(unit, start, end)
        datediff(day, date(started_ts), date(cancelled_ts)) as duration_days,

        -- Renewal date: started + 30 days
        -- BQ: date_add(d, interval n unit) — Snowflake: dateadd(unit, n, d)
        dateadd(day, 30, date(started_ts)) as next_renewal_date,

        -- Truncate started_ts to month for cohort analysis
        -- BQ: date_trunc(d, unit) — Snowflake: date_trunc('unit', d)  -- argument order reversed
        date_trunc('month', date(started_ts)) as cohort_month,

        -- Was the subscription started in the last 90 days?
        -- Same rewrite as duration_days
        datediff(day, started_ts, current_timestamp()) <= 90 as is_recent_signup,

        -- Format the cohort month for display
        -- BQ: format_date('%Y-%m', d) — Snowflake: to_char(d, 'YYYY-MM') — format string differs too
        to_char(date(started_ts), 'YYYY-MM') as cohort_label
    from subs
)

select * from with_metrics
