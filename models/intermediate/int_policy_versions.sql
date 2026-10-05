{{ config(materialized='table') }}

{#-
    One row per policy per point in time at which any tracked attribute changed:
    the bind itself plus every endorsement / cancellation. Attributes that a change
    does not touch are carried forward from the previous version using a portable
    "running non-null group" technique (no IGNORE NULLS dialect differences).
-#}

with events as (
    select
        policy_id,
        effective_date as version_start_date,
        0 as event_order,
        'BIND' as event_type,
        bound_annual_premium as annual_premium,
        bound_coverage_limit as coverage_limit,
        bound_deductible as deductible
    from {{ ref('stg_policies') }}

    union all

    select
        policy_id,
        change_effective_date as version_start_date,
        1 as event_order,
        change_type as event_type,
        new_annual_premium as annual_premium,
        new_coverage_limit as coverage_limit,
        new_deductible as deductible
    from {{ ref('stg_policy_changes') }}
),

grouped as (
    select
        *,
        sum(case when annual_premium is not null then 1 else 0 end) over (
            partition by policy_id order by version_start_date, event_order
            rows between unbounded preceding and current row
        ) as premium_grp,
        sum(case when coverage_limit is not null then 1 else 0 end) over (
            partition by policy_id order by version_start_date, event_order
            rows between unbounded preceding and current row
        ) as limit_grp,
        sum(case when deductible is not null then 1 else 0 end) over (
            partition by policy_id order by version_start_date, event_order
            rows between unbounded preceding and current row
        ) as deductible_grp,
        max(case when event_type = 'CANCELLATION' then 1 else 0 end) over (
            partition by policy_id order by version_start_date, event_order
            rows between unbounded preceding and current row
        ) as is_cancelled_flag
    from events
),

filled as (
    select
        policy_id,
        version_start_date,
        event_order,
        event_type,
        max(annual_premium) over (partition by policy_id, premium_grp) as annual_premium,
        max(coverage_limit) over (partition by policy_id, limit_grp) as coverage_limit,
        max(deductible) over (partition by policy_id, deductible_grp) as deductible,
        is_cancelled_flag = 1 as is_cancelled
    from grouped
)

select
    {{ surrogate_key(['f.policy_id', 'f.version_start_date', 'f.event_order']) }} as policy_event_sk,
    f.policy_id,
    p.policy_number,
    p.customer_id,
    p.product_line_code,
    p.sales_channel,
    p.effective_date,
    p.expiration_date,
    f.version_start_date,
    f.event_type,
    f.event_order,
    f.annual_premium,
    f.coverage_limit,
    f.deductible,
    f.is_cancelled,
    case when f.event_type = 'CANCELLATION' then f.version_start_date end as cancellation_date
from filled as f
inner join {{ ref('stg_policies') }} as p
    on f.policy_id = p.policy_id
