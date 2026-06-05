-- Example Integration Model
-- Purpose: Integrate contact data from Salesforce and HubSpot into unified contact entity
-- Enriches with calculated fields like contact score and engagement level

with

s_salesforce_contact as (
    select * from {{ ref('stg_salesforce__contact') }}
),

s_hubspot_contact as (
    select * from {{ ref('stg_hubspot__contact') }}
),

-- Union contacts from both sources into standardized shape
unioned_contacts as (
    select
        contact_pk,
        'salesforce' as source_system,
        salesforce_contact_natural_key as source_natural_key,
        email,
        first_name,
        last_name,
        phone,
        job_title,
        lead_source,
        city,
        state,
        country,
        created_ts,
        updated_ts,
        last_activity_date

    from s_salesforce_contact

    union all

    select
        contact_pk,
        'hubspot' as source_system,
        hubspot_contact_natural_key as source_natural_key,
        email,
        first_name,
        last_name,
        phone,
        job_title,
        lead_source,
        city,
        state,
        country,
        created_ts,
        updated_ts,
        last_activity_date

    from s_hubspot_contact
),

-- Deduplicate by email, keeping most recently updated record
deduplicated_contacts as (
    select
        contact_pk,
        source_system,
        source_natural_key,
        email,
        first_name,
        last_name,
        phone,
        job_title,
        lead_source,
        city,
        state,
        country,
        created_ts,
        updated_ts,
        last_activity_date,
        row_number() over (
            partition by lower(email)
            order by updated_ts desc
        ) as email_rank

    from unioned_contacts
    where email is not null
),

-- Calculate engagement metrics
contact_engagement as (
    select
        contact_pk,

        -- Calculate days since last activity
        date_diff(current_date(), last_activity_date, day)
            as days_since_last_activity,

        -- Classify engagement level
        case
            when date_diff(
                current_date(),
                last_activity_date,
                day
            ) <= 7
                then 'high'
            when date_diff(
                current_date(),
                last_activity_date,
                day
            ) <= 30
                then 'medium'
            when date_diff(
                current_date(),
                last_activity_date,
                day
            ) <= 90
                then 'low'
            else 'dormant'
        end as engagement_level

    from deduplicated_contacts
    where email_rank = 1
),

final as (
    select
        -- Keys
        deduplicated_contacts.contact_pk,
        deduplicated_contacts.source_system,
        deduplicated_contacts.source_natural_key,

        -- Timestamps
        deduplicated_contacts.created_ts,
        deduplicated_contacts.updated_ts,
        deduplicated_contacts.last_activity_date,

        -- Attributes
        deduplicated_contacts.email,
        deduplicated_contacts.first_name,
        deduplicated_contacts.last_name,
        deduplicated_contacts.phone,
        deduplicated_contacts.job_title,
        deduplicated_contacts.lead_source,
        deduplicated_contacts.city,
        deduplicated_contacts.state,
        deduplicated_contacts.country,

        -- Calculated metrics
        contact_engagement.days_since_last_activity,
        contact_engagement.engagement_level,

        -- Flags
        case
            when deduplicated_contacts.email is not null
                then true
            else false
        end as has_email,
        case
            when deduplicated_contacts.phone is not null
                then true
            else false
        end as has_phone

    from deduplicated_contacts
    inner join contact_engagement
        on deduplicated_contacts.contact_pk =
            contact_engagement.contact_pk
    where deduplicated_contacts.email_rank = 1
)

select * from final
