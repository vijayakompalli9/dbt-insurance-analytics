with cleaned as (
    select
        trim(customer_id) as customer_id,
        nullif(trim(first_name), '') as first_name,
        trim(last_name) as last_name,
        lower(trim(email)) as email,
        upper(trim(state_code)) as state_code,
        {{ parse_date('date_of_birth') }} as date_of_birth,
        {{ parse_date('customer_since') }} as customer_since_date,
        upper(trim(customer_type)) as customer_type,
        _loaded_at
    from {{ raw_source('customers') }}
),

deduped as (
    -- The feed re-sends customers when contact details change: keep the latest.
    {{ dedupe('cleaned', 'customer_id', '_loaded_at desc') }}
)

select
    customer_id,
    first_name,
    last_name,
    email,
    state_code,
    date_of_birth,
    customer_since_date,
    customer_type,
    _loaded_at
from deduped
