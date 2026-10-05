{{
    config(
        materialized='incremental',
        unique_key='payment_id',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

{#-
    Claim payment transactions, loaded incrementally on `_loaded_at`. A small
    lookback window (var payments_lookback_days) re-processes recent loads so
    late-arriving re-sends are merged on `payment_id` instead of duplicated.
-#}

with payments as (
    select *
    from {{ ref('stg_claim_payments') }}
    {% if is_incremental() %}
        -- noqa: disable=LT02
        where _loaded_at > (
            select {{ dbt.dateadd('day', -1 * var('payments_lookback_days'), 'max(_loaded_at)') }}
            from {{ this }}
        )
    {% endif %}
)  -- noqa: enable=LT02

select
    {{ surrogate_key(['p.payment_id']) }} as payment_sk,
    p.payment_id,
    p.claim_id,
    c.policy_id,
    c.product_line_code,
    p.payment_date,
    cast({{ dbt.date_trunc('month', 'p.payment_date') }} as date) as payment_month,
    p.payment_type,
    p.payment_amount,
    p.payment_type = 'RECOVERY' as is_recovery,
    p._loaded_at,
    {{ dbt.current_timestamp() }} as dbt_loaded_at
from payments as p
inner join {{ ref('int_claims_enriched') }} as c
    on p.claim_id = c.claim_id
