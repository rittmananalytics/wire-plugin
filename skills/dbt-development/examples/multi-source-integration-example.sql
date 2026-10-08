-- =============================================================================
-- MULTI-SOURCE INTEGRATION MODEL EXAMPLE
-- File: models/integration/int_crm/int_crm__companies.sql
-- =============================================================================
--
-- Reads the intermediate union (int_crm__companies__unioned, built with the merge_sources macro) and:
-- 1. Resolves companies across sources by cleaned company name
-- 2. Collects every source natural key into an array, for fact joins downstream
-- 3. Optionally applies a manual merge list held in a seed
-- 4. Counts the sources each company appears in, for data quality
--
-- BigQuery syntax (unnest, select * replace). Adapt for other warehouses.
--
-- Projects built on the older pattern (int__company.sql, companies_merge_list seed) keep those names.
-- =============================================================================

{% if var('crm_warehouse_company_sources', []) %}

{{
    config(
        description = """
            Grain: One row per company, matched across all enabled CRM sources by cleaned name.
            Companies from every enabled source with their source natural keys collected into an array.
        """
    )
}}

with s_companies as (

    select * from {{ ref('int_crm__companies__unioned') }}

),

{% if var('enable_companies_merge_file', false) %}

s_company_merge_list as (

    select * from {{ ref('seed__company_merge_list') }}

),

{% endif %}

-- A company without a name cannot be matched, so it is not part of the resolved company entity.
named_companies as (

    select * from s_companies

    where company_name != ''

),

-- One row per company name. Attribute rule: the greatest non-null value across sources. The created
-- timestamp takes the earliest, the modified timestamp the latest.
grouped_companies as (

    select

        company_name,
        array_agg(distinct company_natural_key ignore nulls) as array_agg_company_natural_key,
        max(company_website) as max_company_website,
        max(company_industry) as max_company_industry,
        max(company_phone) as max_company_phone,
        max(company_city) as max_company_city,
        max(company_country_name) as max_company_country_name,
        count(distinct company_source_system) as count_company_source_system,
        min(company_created_ts) as min_company_created_ts,
        max(company_last_modified_ts) as max_company_last_modified_ts

    from named_companies

    group by company_name

),

{% if var('enable_companies_merge_file', false) %}

-- The merge list maps a company natural key (merged_company_natural_key) to the natural key of the
-- company it belongs to (company_natural_key). Finds the company name on each side of every mapping.
merge_pairs as (

    select

        merge_target_companies.company_name as target_company_name,
        merge_source_companies.company_name as merged_company_name,
        merge_source_companies.array_agg_company_natural_key as merged_array_agg_company_natural_key

    from s_company_merge_list

    inner join grouped_companies as merge_target_companies
        on s_company_merge_list.company_natural_key in unnest(merge_target_companies.array_agg_company_natural_key)

    inner join grouped_companies as merge_source_companies
        on s_company_merge_list.merged_company_natural_key
            in unnest(merge_source_companies.array_agg_company_natural_key)

),

-- Adds the merged companies' natural keys to the company they were merged into, and removes the
-- merged companies as separate rows.
companies_after_merge as (

    select

        grouped_companies.* replace (
            array_concat(
                grouped_companies.array_agg_company_natural_key,
                coalesce(merge_pairs.merged_array_agg_company_natural_key, [])
            ) as array_agg_company_natural_key
        )

    from grouped_companies

    left join merge_pairs
        on grouped_companies.company_name = merge_pairs.target_company_name

    where grouped_companies.company_name not in (select merged_company_name from merge_pairs)

),

{% else %}

companies_after_merge as (

    select * from grouped_companies

),

{% endif %}

rename_for_output as (

    select

        {# natural keys #}
        array_agg_company_natural_key as company_natural_keys,
        {# attributes #}
        company_name,
        max_company_website as company_website,
        max_company_industry as company_industry,
        max_company_phone as company_phone,
        max_company_city as company_city,
        max_company_country_name as company_country_name,
        {# metrics #}
        count_company_source_system as company_source_system_count,
        {# temporal #}
        min_company_created_ts as company_created_ts,
        max_company_last_modified_ts as company_last_modified_ts

    from companies_after_merge

),

final as (

    select * from rename_for_output

)

select * from final

{% else %}

-- No company sources configured, model disabled.
{{ config(enabled = false) }}

{% endif %}
