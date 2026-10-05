with cleaned as (
    select
        trim(change_id) as change_id,
        trim(policy_id) as policy_id,
        {{ parse_date('change_effective_date') }} as change_effective_date,
        upper(trim(change_type)) as change_type,
        {{ cents_to_dollars('new_annual_premium_cents') }} as new_annual_premium,
        {{ cents_to_dollars('new_coverage_limit_cents') }} as new_coverage_limit,
        {{ cents_to_dollars('new_deductible_cents') }} as new_deductible,
        _loaded_at
    from {{ raw_source('policy_changes') }}
),

deduped as (
    -- Exact duplicate transactions are re-sent occasionally.
    {{ dedupe('cleaned', 'change_id', '_loaded_at desc') }}
)

select
    change_id,
    policy_id,
    change_effective_date,
    change_type,
    new_annual_premium,
    new_coverage_limit,
    new_deductible,
    _loaded_at
from deduped
