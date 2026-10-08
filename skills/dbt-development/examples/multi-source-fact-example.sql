-- =============================================================================
-- MULTI-SOURCE FACT EXAMPLE
-- File: models/warehouse/wh_finance/wh_finance__invoice_fact.sql
-- =============================================================================
--
-- Shows:
-- 1. Joining to the company dimension through its array of source natural keys (BigQuery unnest)
-- 2. Conditional compilation on the invoice sources array
-- 3. Primary key from the invoice's natural key and source system
-- 4. Measures with explicit units and a rank within each company
--
-- Projects built on the older pattern (models/warehouse/finance/invoice_fact.sql) keep those names.
-- =============================================================================

{% if var('finance_warehouse_invoice_sources', []) %}

{{
    config(
        description = """
            Grain: One row per invoice per source system.
            Invoices from every enabled finance source, with the company they were raised to.
        """,
        partition_by = {
            "field": "invoice_issued_ts",
            "data_type": "timestamp",
            "granularity": "month"
        }
    )
}}

with s_invoices as (

    select * from {{ ref('int_finance__invoices') }}

),

s_companies as (

    select * from {{ ref('wh_crm__company_dim') }}

),

-- Matches each invoice to the company whose array of source natural keys holds the invoice's company id.
join_companies as (

    select

        s_invoices.*,
        s_companies.company_pk

    from s_invoices

    left join s_companies
        on s_invoices.invoice_company_natural_key in unnest(s_companies.company_natural_keys)

),

add_keys_and_measures as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['invoice_natural_key', 'invoice_source_system']) }} as invoice_pk,
        {# foreign keys #}
        company_pk as company_fk,
        {# natural keys #}
        invoice_natural_key,
        invoice_company_natural_key,
        {# attributes #}
        invoice_number,
        invoice_status,
        invoice_currency_code,
        invoice_source_system,
        {# indexes and ranks #}
        row_number() over (partition by company_pk order by invoice_issued_ts) as invoice_company_sequence_rank,
        {# metrics #}
        invoice_revenue_amount,
        invoice_tax_amount,
        invoice_revenue_amount_usd,
        {{ dbt.datediff('invoice_issued_ts', 'invoice_paid_ts', 'day') }} as invoice_payment_duration_days,
        {{ dbt.datediff('invoice_due_ts', 'invoice_paid_ts', 'day') }} as invoice_overdue_duration_days,
        {# booleans #}
        invoice_status = 'open' and invoice_due_ts < {{ dbt.current_timestamp() }} as invoice_is_overdue,
        {# temporal #}
        invoice_issued_ts,
        invoice_due_ts,
        invoice_paid_ts

    from join_companies

),

final as (

    select * from add_keys_and_measures

)

select * from final

{% else %}

-- No invoice sources configured, model disabled.
{{ config(enabled = false) }}

{% endif %}
