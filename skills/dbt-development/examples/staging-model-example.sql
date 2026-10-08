-- Example staging model: models/staging/stg_back_office/stg_back_office__users.sql
-- Source: back-office user_accounts table, declared in _sources.yml as back_office.users.
-- Renames, casts and cleans user accounts for the integration and warehouse layers.
-- Natural keys keep their case. Attribute strings are lowercased.

{{
    config(
        description = """
            Grain: One row per user account.
            User accounts from the back-office system, renamed and cast. Accounts loaded twice by the
            loader are deduplicated to the latest load.
        """
    )
}}

with s_users as (

    select * from {{ source('back_office', 'users') }}

),

-- The loader can write the same account twice in one sync. Keeps the most recently loaded row per account id.
deduplicated_users as (

    select * from s_users

    qualify row_number() over (partition by id order by _loaded_at desc) = 1

),

rename_and_cast as (

    select

        {# natural keys #}
        cast(id as {{ dbt.type_string() }}) as user_natural_key,
        cast(account_id as {{ dbt.type_string() }}) as user_account_natural_key,
        {# attributes #}
        lower(cast(name as {{ dbt.type_string() }})) as user_name,
        lower(trim(cast(email as {{ dbt.type_string() }}))) as user_email,
        lower(cast(country_code as {{ dbt.type_string() }})) as user_country_code,
        {# metrics #}
        cast(account_balance_cents as {{ dbt.type_numeric() }}) / 100 as user_account_balance_amount,
        cast(session_length_secs as {{ dbt.type_int() }}) as user_average_session_duration_seconds,
        cast(profile_completion as {{ dbt.type_numeric() }}) as user_profile_completion_ratio,
        {# booleans #}
        cast(active as {{ dbt.type_boolean() }}) as user_is_active,
        coalesce(cast(is_deleted as {{ dbt.type_boolean() }}), false) as user_was_deleted,
        {# temporal #}
        cast(created_date as {{ ra_type_date() }}) as user_created_dt,
        cast(updated_at as {{ dbt.type_timestamp() }}) as user_updated_ts

    from deduplicated_users

),

final as (

    select * from rename_and_cast

)

select * from final
