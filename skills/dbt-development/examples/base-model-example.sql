-- Example base model: models/staging/stg_back_office/base_back_office__orders.sql
-- The back-office system moves orders older than two years from orders to archived_orders. The two
-- tables have the same columns. The union sits here so that stg_back_office__orders states the
-- concept. Only stg_back_office__orders reads this model; integration and warehouse models never do.

{{
    config(
        description = """
            Grain: One row per order, current or archived.
            Current and archived back-office orders, unioned, with the source table recorded.
        """
    )
}}

with s_orders as (

    select * from {{ source('back_office', 'orders') }}

),

s_archived_orders as (

    select * from {{ source('back_office', 'archived_orders') }}

),

unioned as (

    select

        id,
        user_id,
        status,
        total_cents,
        placed_at,
        'orders' as source_table_name

    from s_orders

    union all

    select

        id,
        user_id,
        status,
        total_cents,
        placed_at,
        'archived_orders' as source_table_name

    from s_archived_orders

),

final as (

    select * from unioned

)

select * from final
