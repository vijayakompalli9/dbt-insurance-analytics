with cleaned as (
    select
        trim(premium_id) as premium_id,
        trim(policy_id) as policy_id,
        cast(installment_number as integer) as installment_number,
        {{ parse_date('coverage_start_date') }} as coverage_start_date,
        {{ parse_date('coverage_end_date') }} as coverage_end_date,
        {{ cents_to_dollars('written_premium_cents') }} as written_premium,
        _loaded_at
    from {{ raw_source('premiums') }}
),

deduped as (
    -- Billing occasionally re-sends an installment a few days later: keep the latest.
    {{ dedupe('cleaned', 'premium_id', '_loaded_at desc') }}
)

select
    premium_id,
    policy_id,
    installment_number,
    coverage_start_date,
    coverage_end_date,
    written_premium,
    _loaded_at
from deduped
