-- =============================================================================
-- MULTI-SOURCE INTEGRATION MODEL EXAMPLE
-- File: models/integration/int__company.sql
-- =============================================================================
-- 
-- This integration model demonstrates:
-- 1. Dynamic source union using merge_sources macro
-- 2. Entity deduplication by business key (company_name)
-- 3. Array collection of all source system IDs
-- 4. Optional manual merge resolution via seed file
-- 5. Source count tracking for data quality
-- =============================================================================

{% if var('crm_warehouse_company_sources') %}

{{
    config(
        materialized='table',
        unique_key='company_name'
    )
}}

-- =============================================================================
-- Step 1: Union all enabled sources using merge_sources macro
-- The macro dynamically unions only sources listed in the enablement array
-- =============================================================================
with companies_unioned as (
    {{ merge_sources(
        sources=var('crm_warehouse_company_sources'),
        model_suffix='__company'
    ) }}
),

-- =============================================================================
-- Step 2: Collect all source IDs into arrays grouped by company name
-- This preserves all source system IDs for downstream fact table joins
-- =============================================================================
all_company_ids as (
    select
        company_name,
        array_agg(distinct company_id ignore nulls) as all_company_ids
    from companies_unioned
    where company_name is not null
      and trim(company_name) != ''
    group by 1
),

-- =============================================================================
-- Step 3: Deduplicate attributes by taking best/max values
-- Different strategies can be used: MAX, MIN, FIRST non-null, priority-based
-- =============================================================================
companies_grouped as (
    select
        company_name,
        
        -- Take first non-null website (could also use MAX or priority logic)
        max(company_website) as company_website,
        
        -- Take first non-null industry
        max(company_industry) as company_industry,
        
        -- Take first non-null phone
        max(company_phone) as company_phone,
        
        -- For address, take first complete address
        max(company_address) as company_address,
        max(company_city) as company_city,
        max(company_state) as company_state,
        max(company_country) as company_country,
        max(company_zip) as company_zip,
        
        -- Social links
        max(company_linkedin_url) as company_linkedin_url,
        max(company_twitter_handle) as company_twitter_handle,
        
        -- Take longest description (usually most complete)
        max(company_description) as company_description,
        
        -- Timestamps: earliest created, latest modified
        min(company_created_ts) as company_created_ts,
        max(company_last_modified_ts) as company_last_modified_ts,
        
        -- Track how many sources this company appears in
        count(distinct source_system) as source_count,
        
        -- List of source systems for debugging
        array_agg(distinct source_system ignore nulls) as source_systems

    from companies_unioned
    where company_name is not null
      and trim(company_name) != ''
    group by 1
),

-- =============================================================================
-- Step 4: Join arrays back to grouped data
-- =============================================================================
companies_pre_merged as (
    select
        g.*,
        a.all_company_ids
    from companies_grouped g
    join all_company_ids a
        on g.company_name = a.company_name
),

-- =============================================================================
-- Step 5: Apply manual merge resolution (optional)
-- Uses seed file to handle cases where same company has different names
-- =============================================================================
{% if var('enable_companies_merge_file', false) %}

merge_list as (
    select * from {{ ref('companies_merge_list') }}
),

-- Find companies that should be merged based on the merge list
-- The merge list maps old_company_id -> company_id (the target to merge into)
merged_company_ids as (
    select
        target.company_name,
        -- Combine all IDs from both source and target companies
        array_concat_agg(
            case 
                when source.company_name is not null then source.all_company_ids
                else target.all_company_ids
            end
        ) as all_company_ids
    from companies_pre_merged target
    left join merge_list m 
        on m.company_id in unnest(target.all_company_ids)
    left join companies_pre_merged source 
        on m.old_company_id in unnest(source.all_company_ids)
    group by 1
),

-- Identify companies that were merged INTO another (should be excluded)
excluded_companies as (
    select distinct source.company_name
    from merge_list m
    join companies_pre_merged source 
        on m.old_company_id in unnest(source.all_company_ids)
),

final as (
    select
        c.company_name,
        c.company_website,
        c.company_industry,
        c.company_phone,
        c.company_address,
        c.company_city,
        c.company_state,
        c.company_country,
        c.company_zip,
        c.company_linkedin_url,
        c.company_twitter_handle,
        c.company_description,
        c.company_created_ts,
        c.company_last_modified_ts,
        c.source_count,
        c.source_systems,
        -- Use merged IDs if available, otherwise original
        coalesce(m.all_company_ids, c.all_company_ids) as all_company_ids
    from companies_pre_merged c
    left join merged_company_ids m 
        on c.company_name = m.company_name
    where c.company_name not in (select company_name from excluded_companies)
)

{% else %}

-- No merge file configured, use pre-merged data directly
final as (
    select * from companies_pre_merged
)

{% endif %}

select * from final

{% else %}

-- No sources configured, model disabled
{{ config(enabled=false) }}

{% endif %}
