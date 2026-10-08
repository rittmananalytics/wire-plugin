-- =============================================================================
-- MULTI-SOURCE STAGING MODEL EXAMPLE
-- File: models/staging/stg_hubspot_crm/stg_hubspot_crm__companies.sql
-- =============================================================================
--
-- Shows the multi-source pattern in a staging model:
-- 1. Compiles only when hubspot_crm is in the company sources array
-- 2. Supports more than one loader in one model (Stitch or Fivetran here; add an elif per loader)
-- 3. Prefixes the natural key with the source, so IDs cannot collide across sources
-- 4. Uses the column names every company staging model shares, so the intermediate model can union them
--
-- Projects built on the older pattern (models/sources/, stg_hubspot_crm__company.sql) keep those names.
-- =============================================================================

{% if 'hubspot_crm' in var('crm_warehouse_company_sources', []) %}

{{
    config(
        description = """
            Grain: One row per HubSpot company.
            HubSpot companies with source-prefixed natural keys and standard column names, ready to union
            with the company staging models of other sources.
        """
    )
}}

{% if var('stg_hubspot_crm_etl') == 'stitch' %}

with s_companies as (

    select * from {{ source('stitch_hubspot_crm', 'companies') }}

),

-- Stitch appends a new row on every change. Keeps the latest row per company.
current_companies as (

    select * from s_companies

    qualify row_number() over (partition by companyid order by _sdc_batched_at desc) = 1

),

{% elif var('stg_hubspot_crm_etl') == 'fivetran' %}

with s_companies as (

    select * from {{ source('fivetran_hubspot_crm', 'companies') }}

),

-- Removes companies Fivetran has marked deleted in HubSpot.
current_companies as (

    select * from s_companies

    where not coalesce(_fivetran_deleted, false)

),

{% endif %}

rename_and_cast as (

    select

        {# natural keys #}
        -- The source prefix is added; the HubSpot id itself keeps its case.
        concat(
            '{{ var("stg_hubspot_crm_id-prefix") }}',
            cast(companyid as {{ dbt.type_string() }})
        ) as company_natural_key,
        {# attributes #}
        -- Legal suffixes are removed so the same company matches across sources.
        lower(trim(
            regexp_replace(
                regexp_replace(
                    coalesce(properties_name, ''),
                    r'(?i)\s*(limited|ltd\.?|inc\.?|llc|corp\.?|plc|gmbh|sa|sas|bv|nv)$',
                    ''
                ),
                r'\s+',
                ' '
            )
        )) as company_name,
        lower(trim(properties_website)) as company_website,
        lower(properties_industry) as company_industry,
        properties_phone as company_phone,
        lower(properties_city) as company_city,
        lower(properties_country) as company_country_name,
        properties_linkedin_company_page as company_linkedin_url,
        'hubspot_crm' as company_source_system,
        {# temporal #}
        cast(properties_createdate as {{ dbt.type_timestamp() }}) as company_created_ts,
        cast(properties_hs_lastmodifieddate as {{ dbt.type_timestamp() }}) as company_last_modified_ts

    from current_companies

),

final as (

    select * from rename_and_cast

)

select * from final

{% else %}

-- Model disabled when hubspot_crm is not in the company sources array.
{{ config(enabled = false) }}

{% endif %}
