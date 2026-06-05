-- BigQuery: dim_customer_address.sql

with customers as (
    select * from {{ ref('stg_shopify__customers') }}
),

with_address as (
    select
        customer_pk,
        email,
        struct(
            street_1,
            street_2,
            city,
            postcode,
            country_code
        ) as address,
        created_ts
    from customers
),

filtered as (
    select
        customer_pk,
        email,
        address.country_code,
        address.postcode
    from with_address
    where address.country_code in ('GB', 'IE')
)

select * from filtered
