with cleaned as (
    select
        trim(claim_id) as claim_id,
        trim(claim_number) as claim_number,
        trim(policy_id) as policy_id,
        -- loss_date arrives as YYYY-MM-DD, YYYY/MM/DD or MM/DD/YYYY.
        {{ parse_date('loss_date') }} as loss_date,
        {{ parse_date('reported_date') }} as raw_reported_date,
        {{ parse_date('closed_date') }} as closed_date,
        upper(trim(claim_status)) as claim_status,
        upper(trim(cause_of_loss)) as cause_of_loss,
        case_reserve_cents,
        _loaded_at
    from {{ raw_source('claims') }}
),

deduped as (
    -- The claim system re-sends the header on every status change: latest version wins.
    {{ dedupe('cleaned', 'claim_id', '_loaded_at desc') }}
)

select
    claim_id,
    claim_number,
    policy_id,
    loss_date,
    -- A claim cannot be reported before the loss occurred; correct keying errors.
    case
        when raw_reported_date < loss_date then loss_date else raw_reported_date
    end as reported_date,
    closed_date,
    claim_status,
    cause_of_loss,
    -- Negative case reserves are invalid; floor at zero and flag.
    {{ cents_to_dollars('case when case_reserve_cents < 0 then 0 else case_reserve_cents end') }}
        as case_reserve,
    raw_reported_date < loss_date as is_reported_date_corrected,
    case_reserve_cents < 0 as is_reserve_corrected,
    _loaded_at
from deduped
