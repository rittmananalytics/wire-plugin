-- =============================================================================
-- MULTI-SOURCE WAREHOUSE DIMENSION EXAMPLE
-- File: models/warehouse/core/company_dim.sql
-- =============================================================================
-- 
-- This warehouse dimension model demonstrates:
-- 1. Surrogate key generation from business key (not source IDs)
-- 2. Preservation of source ID arrays for fact table joins
-- 3. Conditional compilation based on source enablement
-- 4. Proper field ordering and naming conventions
-- =============================================================================

{% if var("crm_warehouse_company_sources") %}

{{
    config(
        materialized='table',
        unique_key='company_pk',
        -- Performance optimization for BigQuery
        partition_by={
            "field": "company_created_ts",
            "data_type": "timestamp",
            "granularity": "month"
        }
    )
}}

with companies as (
    select * from {{ ref('int__company') }}
),

final as (
    select
        -- =================================================================
        -- PRIMARY KEY: Surrogate key from business key
        -- Generated from company_name, NOT from source system IDs
        -- This ensures stable keys even when sources change
        -- =================================================================
        {{ dbt_utils.generate_surrogate_key(['company_name']) }} as company_pk,
        
        -- =================================================================
        -- BUSINESS KEY
        -- =================================================================
        company_name,
        
        -- =================================================================
        -- ATTRIBUTES
        -- =================================================================
        company_website,
        company_industry,
        company_phone,
        
        -- Address components
        company_address,
        company_city,
        company_state,
        company_country,
        company_zip,
        
        -- Derived: Full address for display
        concat_ws(', ',
            nullif(company_address, ''),
            nullif(company_city, ''),
            nullif(company_state, ''),
            nullif(company_zip, ''),
            nullif(company_country, '')
        ) as company_full_address,
        
        -- Social
        company_linkedin_url,
        company_twitter_handle,
        
        -- Description
        company_description,
        
        -- =================================================================
        -- TIMESTAMPS
        -- =================================================================
        company_created_ts,
        company_last_modified_ts,
        
        -- =================================================================
        -- DATA QUALITY / METADATA
        -- =================================================================
        source_count,
        source_systems,
        
        -- Boolean flags for filtering
        source_count > 1 as is_multi_source,
        company_website is not null as has_website,
        company_linkedin_url is not null as has_linkedin,
        
        -- =================================================================
        -- SOURCE ID ARRAY: Critical for fact table joins
        -- This array contains ALL source system IDs for this company
        -- Fact tables JOIN using: company_id IN UNNEST(all_company_ids)
        -- =================================================================
        all_company_ids,
        
        -- =================================================================
        -- AUDIT COLUMNS
        -- =================================================================
        current_timestamp() as _loaded_ts

    from companies
)

select * from final

{% else %}

-- No sources configured, model disabled
{{ config(enabled=false) }}

{% endif %}
