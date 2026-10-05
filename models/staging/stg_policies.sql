with cleaned as (
    select
        trim(policy_id) as policy_id,
        trim(policy_number) as policy_number,
        trim(customer_id) as customer_id,
        -- Some upstream rows arrive lowercase / padded (e.g. ' home').
        upper(trim(product_line_code)) as product_line_code,
        {{ parse_date('effective_date') }} as effective_date,
        {{ parse_date('expiration_date') }} as expiration_date,
        {{ cents_to_dollars('annual_premium_cents') }} as bound_annual_premium,
        {{ cents_to_dollars('coverage_limit_cents') }} as bound_coverage_limit,
        {{ cents_to_dollars('deductible_cents') }} as bound_deductible,
        upper(trim(policy_status)) as bound_status,
        upper(trim(sales_channel)) as sales_channel,
        _loaded_at
    from {{ raw_source('policies') }}
),

deduped as (
    {{ dedupe('cleaned', 'policy_id', '_loaded_at desc') }}
)

select
    policy_id,
    policy_number,
    customer_id,
    product_line_code,
    effective_date,
    expiration_date,
    bound_annual_premium,
    bound_coverage_limit,
    bound_deductible,
    bound_status,
    sales_channel,
    _loaded_at
from deduped
