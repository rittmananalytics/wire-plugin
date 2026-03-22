-- Example Staging Model
-- Source: Salesforce contacts
-- Purpose: Basic cleaning and standardization of Salesforce contact data

with

s_salesforce_contact as (
    select * from {{ source('salesforce', 'contact') }}
),

final as (
    select
        -- Keys
        {{ dbt_utils.surrogate_key(['id', "'salesforce'"]) }}
            as contact_pk,
        id as salesforce_contact_natural_key,
        account_id as salesforce_account_natural_key,

        -- Dates and timestamps
        cast(created_date as timestamp) as created_ts,
        cast(last_modified_date as timestamp) as updated_ts,
        cast(last_activity_date as date) as last_activity_date,

        -- Attributes
        lower(trim(email)) as email,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        trim(phone) as phone,
        trim(title) as job_title,
        lower(trim(lead_source)) as lead_source,
        trim(mailing_city) as city,
        trim(mailing_state) as state,
        trim(mailing_country) as country,

        -- Metrics
        cast(number_of_employees as integer) as employee_count,

        -- Metadata
        case
            when is_deleted = 'true' then true
            when is_deleted = 'false' then false
            else null
        end as is_deleted,
        cast(system_modstamp as timestamp) as source_updated_ts

    from s_salesforce_contact
    where is_deleted = 'false'  -- Filter out deleted records
)

select * from final
