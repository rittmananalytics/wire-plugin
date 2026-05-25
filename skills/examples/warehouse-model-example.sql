-- Example warehouse dimension: warehouse/wh_core/wh_core__user_dim.sql
-- Purpose: User dimension for BI consumption
-- Materialisation: table (all warehouse models are tables)

{{
  config(
    description = 'User dimension with profile, engagement and lifetime-value attributes',
    materialized = 'table',
    unique_key = 'user_pk'
    )
}}

with s_users as (

    select * from {{ ref('int_core__users') }}

),

s_accounts as (

    select * from {{ ref('int_core__accounts') }}

),

s_activities as (

    select * from {{ ref('int_core__activities') }}

),

s_transactions as (

    select * from {{ ref('int_core__transactions') }}

),

activity_summary as (

    select
        user_fk,
        count(*) as user_activity_count,
        max(activity_ts) as user_last_activity_ts

    from s_activities
    group by user_fk

),

transaction_summary as (

    select
        user_fk,
        count(*) as user_transaction_count,
        sum(transaction_amount) as user_lifetime_value_amount,
        max(transaction_ts) as user_last_transaction_ts,
        min(transaction_ts) as user_first_transaction_ts

    from s_transactions
    group by user_fk

),

denormalised as (

    select

        {# keys #}
        s_users.user_pk,
        {{ dbt_utils.generate_surrogate_key(['s_users.account_natural_key']) }} as account_fk,
        s_users.user_natural_key,

        {# attributes #}
        s_users.user_name,
        s_users.user_email,
        s_users.user_country_code,
        s_accounts.account_name,
        s_accounts.account_industry,
        s_accounts.account_type,

        {# metrics #}
        coalesce(activity_summary.user_activity_count, 0) as user_activity_count,
        coalesce(transaction_summary.user_transaction_count, 0) as user_transaction_count,
        coalesce(transaction_summary.user_lifetime_value_amount, 0) as user_lifetime_value_amount,
        s_users.user_account_balance_amount,

        {# booleans #}
        coalesce(transaction_summary.user_transaction_count > 0, false) as is_customer,
        coalesce(
            transaction_summary.user_last_transaction_ts
                >= {{ dbt.dateadd('day', -90, dbt.current_timestamp()) }},
            false
        ) as is_active_customer,
        s_users.was_deleted,

        {# temporal data types #}
        s_users.user_created_dt,
        s_users.user_updated_ts,
        activity_summary.user_last_activity_ts,
        transaction_summary.user_first_transaction_ts,
        transaction_summary.user_last_transaction_ts,

    from s_users
    left join s_accounts
        on s_users.account_natural_key = s_accounts.account_natural_key
    left join activity_summary
        on s_users.user_pk = activity_summary.user_fk
    left join transaction_summary
        on s_users.user_pk = transaction_summary.user_fk

),

final as (

    select * from denormalised

)

select * from final
