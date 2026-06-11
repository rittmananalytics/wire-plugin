-- BigQuery: fct_deals.sql
-- Joins deals to the company dimension on company_id. The dimension collapses
-- merged duplicate companies, so it stores every source company_id for a company
-- in an ARRAY (all_company_ids). BigQuery tests array membership directly in the
-- join condition with IN UNNEST.

with companies_dim as (
    select * from {{ ref('dim_companies') }}
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
    on d.company_id in unnest(c.all_company_ids)
