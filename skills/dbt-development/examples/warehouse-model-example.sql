-- Example warehouse dimension: models/warehouse/wh_core/wh_core__user_dim.sql
-- Creates the primary key and the foreign key to the account dimension. Keys are created here and
-- nowhere else. Materialized as a table by the warehouse folder config.

{{
    config(
        description = """
            Grain: One row per user.
            The user dimension: profile attributes and status for every back-office user account.
        """
    )
}}

with s_users as (

    select * from {{ ref('int_core__users') }}

),

add_keys as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['user_natural_key']) }} as user_pk,
        {# foreign keys #}
        {{ dbt_utils.generate_surrogate_key(['user_account_natural_key']) }} as account_fk,
        {# natural keys #}
        user_natural_key,
        {# attributes #}
        user_name,
        user_email,
        user_country_code,
        {# metrics #}
        user_account_balance_amount,
        user_profile_completion_ratio,
        {# booleans #}
        user_is_active,
        user_was_deleted,
        {# temporal #}
        user_created_dt,
        user_updated_ts

    from s_users

),

final as (

    select * from add_keys

)

select * from final
