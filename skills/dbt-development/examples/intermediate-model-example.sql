-- Example intermediate model: models/integration/int_crm/intermediate/int_crm__contacts__unioned.sql
-- Combines the same concept (contacts) from two sources into one input for int_crm__contacts.
-- Materialized as a view by the intermediate folder config.

{{
    config(
        description = """
            Grain: One row per contact per source system.
            Salesforce and HubSpot contacts in one shape, with the source system recorded.
        """
    )
}}

with s_salesforce_contacts as (

    select * from {{ ref('stg_salesforce__contacts') }}

),

s_hubspot_contacts as (

    select * from {{ ref('stg_hubspot__contacts') }}

),

unioned as (

    select

        {# natural keys #}
        contact_natural_key,
        {# attributes #}
        contact_email,
        contact_first_name,
        contact_last_name,
        contact_job_title,
        contact_country_name,
        'salesforce' as contact_source_system,
        {# temporal #}
        contact_created_ts,
        contact_updated_ts,
        contact_last_activity_dt

    from s_salesforce_contacts

    union all

    select

        {# natural keys #}
        contact_natural_key,
        {# attributes #}
        contact_email,
        contact_first_name,
        contact_last_name,
        contact_job_title,
        contact_country_name,
        'hubspot' as contact_source_system,
        {# temporal #}
        contact_created_ts,
        contact_updated_ts,
        contact_last_activity_dt

    from s_hubspot_contacts

),

final as (

    select * from unioned

)

select * from final
