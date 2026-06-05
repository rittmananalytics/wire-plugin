-- Snowflake: int_order_items.sql
-- Same shape as the BigQuery original; LATERAL FLATTEN replaces UNNEST.

with orders as (
    select * from {{ ref('stg_shopify__orders') }}
),

exploded as (
    select
        o.order_pk,
        o.customer_fk,
        o.order_ts,
        line.value:product_id::number  as product_fk,
        line.value:variant_id::number  as variant_fk,
        line.value:quantity::number    as quantity,
        line.value:unit_price::number(18, 4)  as unit_price,
        line.value:line_total::number(18, 4)  as line_total
    from orders o,
    lateral flatten(input => o.order_lines) line
)

select * from exploded
