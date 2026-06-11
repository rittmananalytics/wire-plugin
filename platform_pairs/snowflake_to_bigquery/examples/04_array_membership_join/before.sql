-- Snowflake: fct_deals.sql
-- Joins deals to the company dimension on company_id. The dimension collapses
-- merged duplicate companies, so it stores every source company_id for a company
-- in an ARRAY (all_company_ids). The join must match a deal's single company_id
-- against any element of that array.

with companies_dim as (
    -- Snowflake cannot test array membership inline in a JOIN condition, so the
    -- array is first flattened to one row per company_id, then equi-joined.
    select
        c.company_pk,
        cf.value::string as company_id
    from {{ ref('dim_companies') }} c,
    table(flatten(c.all_company_ids)) cf
)

select
    {{ dbt_utils.generate_surrogate_key(['d.deal_id']) }} as deal_pk,
    c.company_pk as company_fk,
    d.deal_id,
    d.deal_amount,
    d.deal_stage,
    d.closed_ts
from {{ ref('int_deals') }} d
join companies_dim c
    on d.company_id = c.company_id
