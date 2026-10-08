-- =============================================================================
-- MULTI-SOURCE WAREHOUSE DIMENSION EXAMPLE
-- File: models/warehouse/wh_crm/wh_crm__company_dim.sql
-- =============================================================================
--
-- Shows:
-- 1. The surrogate key generated from the business key (company name), not from a source id, so the key
--    stays stable when sources are added or removed
-- 2. The array of source natural keys kept, so facts can join on any source's id
-- 3. Conditional compilation on the company sources array
--
-- Projects built on the older pattern (models/warehouse/core/company_dim.sql) keep those names.
-- =============================================================================

{% if var('crm_warehouse_company_sources', []) %}

{{
    config(
        description = """
            Grain: One row per company, matched across all enabled CRM sources.
            The company dimension, with every source natural key for the company held in an array.
        """,
        partition_by = {
            "field": "company_created_ts",
            "data_type": "timestamp",
            "granularity": "month"
        }
    )
}}

with s_companies as (

    select * from {{ ref('int_crm__companies') }}

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['company_name']) }} as company_pk,
        {# natural keys #}
        -- Facts join with: <fact natural key> in unnest(company_natural_keys)
        company_natural_keys,
        {# attributes #}
        company_name,
        company_website,
        company_industry,
        company_phone,
        company_city,
        company_country_name,
        {# metrics #}
        company_source_system_count,
        {# booleans #}
        company_source_system_count > 1 as company_is_multi_source,
        company_website is not null as company_has_website,
        {# temporal #}
        company_created_ts,
        company_last_modified_ts

    from s_companies

),

final as (

    select * from add_primary_key

)

select * from final

{% else %}

-- No company sources configured, model disabled.
{{ config(enabled = false) }}

{% endif %}
