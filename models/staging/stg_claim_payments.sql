with cleaned as (
    select
        trim(payment_id) as payment_id,
        trim(claim_id) as claim_id,
        {{ parse_date('payment_date') }} as payment_date,
        upper(trim(payment_type)) as payment_type,
        {{ cents_to_dollars('amount_cents') }} as payment_amount,
        _loaded_at
    from {{ raw_source('claim_payments') }}
),

deduped as (
    {{ dedupe('cleaned', 'payment_id', '_loaded_at desc') }}
)

select
    payment_id,
    claim_id,
    payment_date,
    payment_type,
    payment_amount,
    _loaded_at
from deduped
