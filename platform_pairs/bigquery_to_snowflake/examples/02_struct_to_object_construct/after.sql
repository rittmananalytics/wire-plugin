-- Snowflake: dim_customer_address.sql
-- OBJECT_CONSTRUCT replaces STRUCT; colon-path replaces dot notation; casts are now explicit.

with customers as (
    select * from {{ ref('stg_shopify__customers') }}
),

with_address as (
    select
        customer_pk,
        email,
        object_construct(
            'street_1',     street_1,
            'street_2',     street_2,
            'city',         city,
            'postcode',     postcode,
            'country_code', country_code
        ) as address,
        created_ts
    from customers
),

filtered as (
    -- Downstream usage: colon-path with explicit cast
    select
        customer_pk,
        email,
        address:country_code::varchar  as country_code,
        address:postcode::varchar      as postcode
    from with_address
    where address:country_code::varchar in ('GB', 'IE')
)

select * from filtered
