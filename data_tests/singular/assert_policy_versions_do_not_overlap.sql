-- SCD2 integrity: per policy, each version must start exactly where the previous
-- one ended (no gaps, no overlaps), and exactly one version is current.
with ordered as (
    select
        policy_id,
        version_number,
        effective_from,
        effective_to,
        is_current,
        lag(effective_to) over (partition by policy_id order by version_number) as prev_to
    from {{ ref('dim_policy') }}
)

select
    policy_id,
    version_number,
    'gap_or_overlap' as issue
from ordered
where prev_to is not null and prev_to <> effective_from

union all

select
    policy_id,
    null as version_number,
    'current_version_count' as issue
from {{ ref('dim_policy') }}
group by policy_id
having sum(case when is_current then 1 else 0 end) <> 1
