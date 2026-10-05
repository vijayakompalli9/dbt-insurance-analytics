-- Total written premium in the fact equals total (deduplicated) installments in staging
-- for policies that exist: nothing dropped or double-counted by the monthly split.
with fact as (
    select coalesce(sum(written_premium), 0) as total from {{ ref('fct_premium_earned') }}
),

source_side as (
    select coalesce(sum(pr.written_premium), 0) as total
    from {{ ref('stg_premiums') }} as pr
    inner join {{ ref('stg_policies') }} as po on pr.policy_id = po.policy_id
)

select
    fact.total as fact_total,
    source_side.total as source_total
from fact cross join source_side
where abs(fact.total - source_side.total) > 0.01
