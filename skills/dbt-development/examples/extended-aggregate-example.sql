-- Example extended aggregate: models/warehouse/wh_core/wh_core__user_daily_activity_xa.sql
-- An extended aggregate (_xa) is a denormalised table built from fact and dimension models. This one
-- aggregates the activity fact to a summary grain for faster reporting. Aggregated columns lead with
-- the function, so the name shows the value is no longer one activity's.

{{
    config(
        description = """
            Grain: One row per user per activity date.
            Daily activity totals per user, with the user's country and status from the user dimension.
        """
    )
}}

with s_activities as (

    select * from {{ ref('wh_core__activity_fact') }}

),

s_users as (

    select * from {{ ref('wh_core__user_dim') }}

),

-- Aggregates before joining, so the join to the user dimension runs on one row per user per day.
daily_activity as (

    select

        user_fk,
        activity_started_dt,
        count(activity_pk) as count_activity_pk,
        sum(activity_duration_seconds) as sum_activity_duration_seconds,
        max(activity_started_ts) as max_activity_started_ts

    from s_activities

    group by user_fk, activity_started_dt

),

join_user_attributes as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['daily_activity.user_fk', 'daily_activity.activity_started_dt']) }}
            as user_daily_activity_pk,
        {# foreign keys #}
        daily_activity.user_fk,
        {# attributes #}
        s_users.user_country_code as user_daily_activity_user_country_code,
        {# metrics #}
        daily_activity.count_activity_pk as user_daily_activity_count,
        daily_activity.sum_activity_duration_seconds as user_daily_activity_sum_activity_duration_seconds,
        {# booleans #}
        s_users.user_is_active as user_daily_activity_user_is_active,
        {# temporal #}
        daily_activity.activity_started_dt as user_daily_activity_dt,
        daily_activity.max_activity_started_ts as user_daily_activity_max_activity_started_ts

    from daily_activity

    left join s_users
        on daily_activity.user_fk = s_users.user_pk

),

final as (

    select * from join_user_attributes

)

select * from final
