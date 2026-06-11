-- BigQuery: int_contacts.sql (aggregation fragment)
-- Collapses many source rows per contact into one row, rolling the source values
-- up into arrays — a scalar array of emails, and an array of address records.

with contacts as (
    select * from {{ ref('stg_contacts') }}
)

select
    contact_name,

    -- Scalar array. BigQuery defaults to RESPECT NULLS and then errors, because an
    -- array cannot hold a NULL element. IGNORE NULLS is required to match
    -- Snowflake's default and to avoid a runtime failure.
    array_agg(distinct lower(contact_email) ignore nulls) as all_contact_emails,

    -- Array of records. BigQuery builds the array of STRUCTs natively — no JSON
    -- round-trip. Field names come from the aliases on each STRUCT element.
    array_agg(
        struct(
            contact_address as address,
            contact_city    as city,
            contact_country as country
        )
        ignore nulls
    ) as all_contact_addresses

from contacts
group by 1
