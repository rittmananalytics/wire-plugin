-- Example Warehouse Dimension Model
-- Purpose: Contact dimension for BI consumption
-- Materialization: Table (all warehouse models are tables)

{{
  config(
    materialized = 'table',
    sort = 'contact_pk',
    dist = 'contact_pk'
  )
}}

with

s_contact as (
    select * from {{ ref('int__contact') }}
),

s_account as (
    select * from {{ ref('int__account') }}
),

-- Aggregate contact activity metrics
contact_activity_summary as (
    select
        contact_fk,
        count(*) as total_activities,
        count(case when activity_type = 'email' then 1 end)
            as email_count,
        count(case when activity_type = 'call' then 1 end)
            as call_count,
        count(case when activity_type = 'meeting' then 1 end)
            as meeting_count,
        max(activity_ts) as last_activity_ts

    from {{ ref('int__activity') }}
    group by contact_fk
),

-- Aggregate contact transaction metrics
contact_transaction_summary as (
    select
        contact_fk,
        count(*) as total_transactions,
        sum(amount) as lifetime_value,
        max(transaction_ts) as last_transaction_ts,
        min(transaction_ts) as first_transaction_ts

    from {{ ref('int__transaction') }}
    group by contact_fk
),

final as (
    select
        -- Keys
        s_contact.contact_pk,
        s_account.account_pk as account_fk,

        -- Timestamps
        s_contact.created_ts,
        s_contact.updated_ts,
        s_contact.last_activity_date,
        contact_activity_summary.last_activity_ts,
        contact_transaction_summary.first_transaction_ts,
        contact_transaction_summary.last_transaction_ts,

        -- Contact attributes
        s_contact.email as contact_email,
        s_contact.first_name as contact_first_name,
        s_contact.last_name as contact_last_name,
        concat(
            s_contact.first_name,
            ' ',
            s_contact.last_name
        ) as contact_full_name,
        s_contact.phone as contact_phone,
        s_contact.job_title as contact_job_title,
        s_contact.lead_source as contact_lead_source,

        -- Location attributes
        s_contact.city as contact_city,
        s_contact.state as contact_state,
        s_contact.country as contact_country,

        -- Account attributes (denormalized for convenience)
        s_account.account_name,
        s_account.account_industry,
        s_account.account_type,

        -- Engagement attributes
        s_contact.engagement_level as contact_engagement_level,
        s_contact.days_since_last_activity,

        -- Activity metrics
        coalesce(contact_activity_summary.total_activities, 0)
            as total_activities,
        coalesce(contact_activity_summary.email_count, 0)
            as total_emails,
        coalesce(contact_activity_summary.call_count, 0)
            as total_calls,
        coalesce(contact_activity_summary.meeting_count, 0)
            as total_meetings,

        -- Transaction metrics
        coalesce(contact_transaction_summary.total_transactions, 0)
            as total_transactions,
        coalesce(contact_transaction_summary.lifetime_value, 0)
            as lifetime_value,

        -- Calculated attributes
        case
            when contact_transaction_summary.total_transactions > 0
                then contact_transaction_summary.lifetime_value /
                    contact_transaction_summary.total_transactions
            else 0
        end as average_transaction_value,

        date_diff(
            current_date(),
            contact_transaction_summary.last_transaction_ts,
            day
        ) as days_since_last_transaction,

        -- Flags
        s_contact.has_email as is_emailable,
        s_contact.has_phone as is_callable,
        case
            when contact_transaction_summary.total_transactions > 0
                then true
            else false
        end as is_customer,
        case
            when contact_transaction_summary.last_transaction_ts >=
                date_sub(current_date(), interval 90 day)
                then true
            else false
        end as is_active_customer,

        -- Source metadata
        s_contact.source_system as contact_source_system,
        s_contact.source_natural_key as contact_source_natural_key

    from s_contact
    left join s_account
        on s_contact.contact_pk = s_account.contact_pk
    left join contact_activity_summary
        on s_contact.contact_pk =
            contact_activity_summary.contact_fk
    left join contact_transaction_summary
        on s_contact.contact_pk =
            contact_transaction_summary.contact_fk
)

select * from final
