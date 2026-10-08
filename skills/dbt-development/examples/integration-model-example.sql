-- Example integration model: models/integration/int_crm/int_crm__contacts.sql
-- Reads the intermediate union of Salesforce and HubSpot contacts, keeps one row per email address,
-- and derives the engagement fields the warehouse exposes.

{{
    config(
        description = """
            Grain: One row per contact email address.
            Contacts from Salesforce and HubSpot, deduplicated by email, with engagement fields.
        """
    )
}}

with s_contacts as (

    select * from {{ ref('int_crm__contacts__unioned') }}

),

-- Contacts without an email address cannot be matched across sources or contacted, so they are not
-- part of the contact entity the warehouse exposes.
contacts_with_email as (

    select * from s_contacts

    where contact_email is not null

),

-- Ranks each email address's records, most recently updated first, so the latest record wins.
ranked_contacts as (

    select

        *,
        row_number() over (
            partition by contact_email
            order by contact_updated_ts desc
        ) as contact_email_rank

    from contacts_with_email

),

latest_contacts as (

    select * from ranked_contacts

    where contact_email_rank = 1

),

add_engagement as (

    select

        {# natural keys #}
        contact_natural_key,
        {# attributes #}
        contact_email,
        contact_first_name,
        contact_last_name,
        contact_job_title,
        contact_country_name,
        contact_source_system,
        case
            when {{ dbt.datediff('contact_last_activity_dt', dbt.current_timestamp(), 'day') }} <= 7 then 'high'
            when {{ dbt.datediff('contact_last_activity_dt', dbt.current_timestamp(), 'day') }} <= 30 then 'medium'
            when {{ dbt.datediff('contact_last_activity_dt', dbt.current_timestamp(), 'day') }} <= 90 then 'low'
            else 'dormant'
        end as contact_engagement_level,
        {# metrics #}
        {{ dbt.datediff('contact_last_activity_dt', dbt.current_timestamp(), 'day') }}
            as contact_time_since_last_activity_days,
        {# booleans #}
        contact_job_title is not null as contact_has_job_title,
        {# temporal #}
        contact_created_ts,
        contact_updated_ts,
        contact_last_activity_dt

    from latest_contacts

),

final as (

    select * from add_engagement

)

select * from final
