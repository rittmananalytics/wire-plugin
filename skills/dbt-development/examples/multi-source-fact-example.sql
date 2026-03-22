-- =============================================================================
-- MULTI-SOURCE FACT TABLE EXAMPLE
-- File: models/warehouse/finance/invoice_fct.sql
-- =============================================================================
-- 
-- This fact table demonstrates:
-- 1. Joining to dimension using source ID arrays (IN UNNEST pattern)
-- 2. Conditional compilation based on source enablement
-- 3. Proper surrogate key generation
-- 4. Calculated metrics and sequencing
-- =============================================================================

{% if var("finance_warehouse_invoice_sources") %}

{{
    config(
        materialized='table',
        unique_key='invoice_pk',
        partition_by={
            "field": "invoice_created_ts",
            "data_type": "timestamp",
            "granularity": "month"
        }
    )
}}

with invoices as (
    select * from {{ ref('int__invoice') }}
),

-- Reference the dimension table for joins
companies_dim as (
    select * from {{ ref('company_dim') }}
),

-- Optional: Join to contacts if available
{% if var('crm_warehouse_contact_sources', []) %}
contacts_dim as (
    select * from {{ ref('contact_dim') }}
),
{% endif %}

final as (
    select
        -- =================================================================
        -- PRIMARY KEY
        -- =================================================================
        {{ dbt_utils.generate_surrogate_key(['i.invoice_number', 'i.source_system']) }} as invoice_pk,
        
        -- =================================================================
        -- FOREIGN KEYS: Join using the source ID arrays
        -- The IN UNNEST() pattern matches ANY source ID in the array
        -- =================================================================
        c.company_pk as company_fk,
        
        {% if var('crm_warehouse_contact_sources', []) %}
        ct.contact_pk as contact_fk,
        {% endif %}
        
        -- =================================================================
        -- NATURAL KEYS: Preserve source system IDs
        -- =================================================================
        i.invoice_id,
        i.invoice_number,
        i.company_id as company_natural_key,
        
        -- =================================================================
        -- INVOICE ATTRIBUTES
        -- =================================================================
        i.invoice_subject,
        i.invoice_status,
        i.invoice_type,
        i.invoice_currency,
        i.invoice_payment_term,
        
        -- =================================================================
        -- AMOUNTS
        -- =================================================================
        i.invoice_local_total_revenue_amount,
        i.invoice_local_total_tax_amount,
        i.invoice_local_total_due_amount,
        i.total_local_amount,
        i.total_gbp_amount,
        i.invoice_currency_rate,
        
        -- =================================================================
        -- TIMESTAMPS
        -- =================================================================
        i.invoice_created_ts,
        i.invoice_issue_ts,
        i.invoice_due_ts,
        i.invoice_sent_ts,
        i.invoice_paid_ts,
        i.expected_payment_ts,
        
        -- =================================================================
        -- CALCULATED FIELDS
        -- =================================================================
        -- Invoice sequence per company
        row_number() over (
            partition by c.company_pk 
            order by i.invoice_issue_ts
        ) as invoice_seq,
        
        -- Days calculations
        {{ dbt.datediff('i.invoice_issue_ts', 'i.invoice_paid_ts', 'day') }} as days_to_pay,
        {{ dbt.datediff('i.invoice_due_ts', 'i.invoice_paid_ts', 'day') }} as days_overdue,
        {{ dbt.datediff('i.invoice_issue_ts', 'i.invoice_due_ts', 'day') }} as payment_terms_days,
        
        -- Derived status
        case 
            when i.invoice_status = 'Paid' then 'Paid'
            when i.invoice_status = 'Open' and i.invoice_due_ts < current_timestamp() then 'Overdue'
            when i.invoice_status = 'Open' then 'Open'
            when i.invoice_status = 'Draft' then 'Draft'
            else i.invoice_status
        end as invoice_status_derived,
        
        -- =================================================================
        -- SOURCE METADATA
        -- =================================================================
        i.source_system,
        current_timestamp() as _loaded_ts

    from invoices i
    
    -- =================================================================
    -- JOIN TO COMPANY DIMENSION USING SOURCE ID ARRAY
    -- This is the key pattern: match ANY ID in the all_company_ids array
    -- =================================================================
    left join companies_dim c
        on i.company_id in unnest(c.all_company_ids)
    
    {% if var('crm_warehouse_contact_sources', []) %}
    -- Similar pattern for contact dimension if available
    left join contacts_dim ct
        on i.contact_id in unnest(ct.all_contact_ids)
    {% endif %}
)

select * from final

{% else %}

-- No invoice sources configured, model disabled
{{ config(enabled=false) }}

{% endif %}
