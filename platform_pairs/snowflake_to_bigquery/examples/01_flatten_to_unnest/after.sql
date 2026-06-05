-- BigQuery: int_order_items.sql

with orders as (
    select * from {{ ref('stg_shopify__orders') }}
),

exploded as (
    select
        o.order_pk,
        o.customer_fk,
        o.order_ts,
        cast(line.product_id   as int64)         as product_fk,
        cast(line.variant_id   as int64)         as variant_fk,
        cast(line.quantity     as int64)         as quantity,
        cast(line.unit_price   as numeric)       as unit_price,
        cast(line.line_total   as numeric)       as line_total
    from orders o,
    unnest(o.order_lines) as line
)

select * from exploded
