-- =============================================================================
-- MERGE SOURCES MACRO
-- File: macros/macro__merge_sources.sql (new projects)
-- Existing projects keep their file name (for example macros/merge_sources.sql).
-- =============================================================================
--
-- Unions the staging model of every source in a sources array. Used by intermediate models such as
-- int_crm__companies__unioned. One macro per file; helper macros such as a Stitch or Fivetran filter
-- go in their own macro__<name>.sql files.
--
-- Usage:
--     {{ merge_sources(sources = var('crm_warehouse_company_sources'), model_suffix = '__companies') }}
--
-- With sources ['hubspot_crm', 'xero_accounting'] this unions stg_hubspot_crm__companies and
-- stg_xero_accounting__companies.
--
-- Entry in macros/_schema_macros.yml (the name matches the macro as defined below):
--
--     macros:
--       - name: merge_sources
--         description: >
--           Unions the staging model of each source in a sources array,
--           using dbt_utils.union_relations. Adds _dbt_source_relation
--           to record which model each row came from.
--         arguments:
--           - name: sources
--             type: list[string]
--             description: Source names, as used in stg_<source> model names.
--           - name: model_suffix
--             type: string
--             description: The model name after the source, such as __companies.
-- =============================================================================

{% macro merge_sources(sources, model_suffix) %}

    {% set relations = [] %}

    {% for source_name in sources %}
        {% do relations.append(ref('stg_' ~ source_name ~ model_suffix)) %}
    {% endfor %}

    {{ dbt_utils.union_relations(relations = relations, source_column_name = '_dbt_source_relation') }}

{% endmacro %}
