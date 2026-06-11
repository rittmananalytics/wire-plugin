-- Snowflake: int_contacts.sql (aggregation fragment)
-- Collapses many source rows per contact into one row, rolling the source values
-- up into arrays — a scalar array of emails, and an array of address records.

with contacts as (
    select * from {{ ref('stg_contacts') }}
)

select
    contact_name,

    -- Scalar array. Snowflake ARRAY_AGG omits NULLs by default, so no clause is
    -- needed to keep nulls out of the array.
    array_agg(distinct lower(contact_email)) as all_contact_emails,

    -- Array of records. Snowflake has no STRUCT literal in this position, so the
    -- record is hand-built as a JSON object string and parsed back with PARSE_JSON.
    array_agg(
        parse_json(
            concat(
                '{"address":"',  contact_address,
                '","city":"',    contact_city,
                '","country":"', contact_country, '"}'
            )
        )
    ) as all_contact_addresses

from contacts
group by 1
