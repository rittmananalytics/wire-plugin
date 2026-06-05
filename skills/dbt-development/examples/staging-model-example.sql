-- Example staging model: stg_core/stg_core__users.sql
-- Source: back-office user_accounts table
-- Purpose: Rename, type-cast, and standardise user account data ready for
--          downstream integration and warehouse layers

{{
  config(
    description = 'Cleaned and standardised user accounts from the back-office source'
    )
}}

with s_users as (

    select * from {{ source('back_office', 'user_accounts') }}

),

rename_and_cast as (

    select

        {# keys #}
        lower(cast(id as {{ dbt.type_string() }} )) as user_natural_key,

        {# attributes #}
        lower(cast(name as {{ dbt.type_string() }} )) as user_name,
        lower(trim(cast(email as {{ dbt.type_string() }} ))) as user_email,
        lower(cast(country_code as {{ dbt.type_string() }} )) as user_country_code,

        {# metrics #}
        cast(account_balance as {{ dbt.type_numeric() }} ) as user_account_balance_amount,

        {# booleans #}
        cast(status as {{ dbt.type_boolean() }} ) as user_status,
        cast(is_deleted as {{ dbt.type_boolean() }} ) as was_deleted,

        {# temporal data types #}
        cast(created_date as {{ type_date() }} ) as user_created_dt,
        cast(updated_at as {{ dbt.type_timestamp() }} ) as user_updated_ts,

    from s_users

),

final as (

    select * from rename_and_cast

)

select * from final
