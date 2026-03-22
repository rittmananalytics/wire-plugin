-- =============================================================================
-- MULTI-SOURCE STAGING MODEL EXAMPLE
-- File: models/sources/stg_hubspot_crm/stg_hubspot_crm__company.sql
-- =============================================================================
-- 
-- This staging model demonstrates the multi-source framework pattern:
-- 1. Conditional compilation based on source enablement
-- 2. Multi-ETL support (Stitch, Fivetran, Airbyte)
-- 3. ID prefixing to prevent collisions
-- 4. Standardized column naming for integration
-- =============================================================================

{% if var("crm_warehouse_company_sources") %}
{% if 'hubspot_crm' in var("crm_warehouse_company_sources") %}

-- Support multiple ETL pipelines
{% if var("stg_hubspot_crm_etl") == 'stitch' %}

with source as (
    select * from {{ source('stitch_hubspot_crm', 'companies') }}
    -- Optional: filter for latest record per company if Stitch provides history
    qualify row_number() over (partition by companyid order by _sdc_batched_at desc) = 1
)

{% elif var("stg_hubspot_crm_etl") == 'fivetran' %}

with source as (
    select * from {{ source('fivetran_hubspot_crm', 'company') }}
    where not _fivetran_deleted
)

{% elif var("stg_hubspot_crm_etl") == 'airbyte' %}

with source as (
    select * from {{ source('airbyte_hubspot_crm', 'companies') }}
)

{% endif %}

renamed as (
    select
        -- =================================================================
        -- PRIMARY KEY: Prefixed with source identifier
        -- This prevents ID collisions when merging with other sources
        -- =================================================================
        concat(
            '{{ var("stg_hubspot_crm_id-prefix") }}',
            cast(companyid as {{ dbt.type_string() }})
        ) as company_id,
        
        -- =================================================================
        -- BUSINESS KEY: Standardized for matching across sources
        -- Apply consistent cleaning: trim, normalize spacing, remove suffixes
        -- =================================================================
        trim(
            regexp_replace(
                regexp_replace(
                    coalesce(properties_name, ''),
                    r'(?i)\s*(Limited|Ltd\.?|Inc\.?|LLC|Corp\.?|PLC|GmbH|SA|SAS|BV|NV)$',
                    ''
                ),
                r'\s+',
                ' '
            )
        ) as company_name,
        
        -- =================================================================
        -- STANDARDIZED ATTRIBUTES
        -- Use consistent column names across all sources
        -- =================================================================
        lower(trim(properties_website)) as company_website,
        properties_industry as company_industry,
        properties_phone as company_phone,
        properties_address as company_address,
        properties_city as company_city,
        properties_state as company_state,
        properties_country as company_country,
        properties_zip as company_zip,
        
        -- LinkedIn and social
        properties_linkedin_company_page as company_linkedin_url,
        properties_twitterhandle as company_twitter_handle,
        
        -- Description
        properties_description as company_description,
        
        -- =================================================================
        -- TIMESTAMPS: Always use _ts suffix, store in UTC
        -- =================================================================
        cast(properties_createdate as {{ dbt.type_timestamp() }}) as company_created_ts,
        cast(properties_hs_lastmodifieddate as {{ dbt.type_timestamp() }}) as company_last_modified_ts,
        
        -- =================================================================
        -- SOURCE METADATA: Track origin for debugging
        -- =================================================================
        'hubspot_crm' as source_system,
        current_timestamp() as _loaded_ts
        
    from source
    where properties_name is not null
      and trim(properties_name) != ''
)

select * from renamed

{% endif %}
{% else %} 

-- Model disabled when source not in enablement array
{{ config(enabled=false) }} 

{% endif %}
