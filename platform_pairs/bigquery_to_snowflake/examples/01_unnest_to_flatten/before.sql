-- BigQuery: int_order_items.sql
-- Explodes the order_lines repeated record on a Shopify order into one row per line item.

with orders as (
    select * from {{ ref('stg_shopify__orders') }}
),

exploded as (
    select
        o.order_pk,
        o.customer_fk,
        o.order_ts,
        line.product_id          as product_fk,
        line.variant_id          as variant_fk,
        line.quantity,
        line.unit_price,
        line.line_total
    from orders o,
    unnest(o.order_lines) as line
)

select * from exploded
