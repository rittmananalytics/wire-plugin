-- BigQuery: int_contacts.sql (aggregation fragment)
-- Collapses many source rows per contact into one row, rolling the source values
-- up into arrays — a scalar array of emails, and an array of address records.

with contacts as (
    select * from {{ ref('stg_contacts') }}
)

select
    contact_name,

    -- Scalar array. IGNORE NULLS is required on BigQuery — an array cannot hold a
    -- NULL element, so the default RESPECT NULLS would error at runtime.
    array_agg(distinct lower(contact_email) ignore nulls) as all_contact_emails,

    -- Array of records, built as a native typed STRUCT array.
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
