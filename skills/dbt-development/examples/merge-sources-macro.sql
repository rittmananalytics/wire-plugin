-- =============================================================================
-- MERGE SOURCES MACRO
-- File: macros/merge_sources.sql
-- =============================================================================
-- 
-- This macro dynamically unions staging models based on the sources array.
-- It's a key component of the multi-source framework, enabling configuration-
-- driven source management.
--
-- Usage:
--   {{ merge_sources(
--       sources=var('crm_warehouse_company_sources'),
--       model_suffix='__company'
--   ) }}
--
-- This will union:
--   - stg_hubspot_crm__company (if 'hubspot_crm' in sources)
--   - stg_xero_accounting__company (if 'xero_accounting' in sources)
--   - stg_harvest_projects__company (if 'harvest_projects' in sources)
--   - etc.
--
-- =============================================================================

{% macro merge_sources(sources, model_suffix) %}
(
    {% set relations_list = [] %}
    
    {# Build list of ref() calls for each enabled source #}
    {% for source in sources %}
        {% do relations_list.append(ref("stg_" ~ source ~ model_suffix)) %}
    {% endfor %}

    {# Use dbt_utils.union_relations to combine all sources #}
    {# This adds _dbt_source_relation column to track which source each row came from #}
    {{ dbt_utils.union_relations(
        relations=relations_list,
        include=[],  -- include all columns
        exclude=[],  -- exclude no columns
        source_column_name='_dbt_source_relation'
    ) }}
)
{% endmacro %}


-- =============================================================================
-- ALTERNATIVE: Manual Union Macro
-- Use this if you need more control over the union process
-- =============================================================================

{% macro merge_sources_manual(sources, model_suffix) %}
(
    {% for source in sources %}
        select
            '{{ source }}' as source_system,
            *
        from {{ ref("stg_" ~ source ~ model_suffix) }}
        
        {% if not loop.last %}
        union all
        {% endif %}
    {% endfor %}
)
{% endmacro %}


-- =============================================================================
-- FILTER STITCH RELATION MACRO
-- Helper macro to deduplicate Stitch-loaded data
-- =============================================================================

{% macro filter_stitch_relation(relation, unique_column) %}
(
    select *
    from {{ relation }}
    qualify row_number() over (
        partition by {{ unique_column }}
        order by _sdc_batched_at desc
    ) = 1
)
{% endmacro %}


-- =============================================================================
-- FILTER FIVETRAN RELATION MACRO
-- Helper macro to filter out soft-deleted Fivetran records
-- =============================================================================

{% macro filter_fivetran_relation(relation) %}
(
    select *
    from {{ relation }}
    where not coalesce(_fivetran_deleted, false)
)
{% endmacro %}
