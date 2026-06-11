-- Snowflake: int_contacts.sql (aggregation fragment)
-- Collapses many source rows per contact into one row, rolling the source values
-- up into arrays — a scalar array of emails, and an array of address records.

with contacts as (
    select * from {{ ref('stg_contacts') }}
)

select
    contact_name,

    -- Scalar array. Snowflake ARRAY_AGG omits NULLs by default, so IGNORE NULLS is
    -- dropped — it has no equivalent here and is not needed.
    array_agg(distinct lower(contact_email)) as all_contact_emails,

    -- Array of records. The BigQuery STRUCT becomes a Snowflake OBJECT via
    -- OBJECT_CONSTRUCT — explicit 'key', value pairs, not positional fields.
    array_agg(
        object_construct(
            'address', contact_address,
            'city',    contact_city,
            'country', contact_country
        )
    ) as all_contact_addresses

from contacts
group by 1
