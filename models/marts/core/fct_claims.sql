{#- One row per valid claim, linked to the policy version in force on the loss date. -#}

select
    {{ surrogate_key(['c.claim_id']) }} as claim_sk,
    c.claim_id,
    c.claim_number,
    c.policy_id,
    dp.policy_version_sk,
    {{ surrogate_key(['c.customer_id']) }} as customer_sk,
    c.product_line_code,
    cast(
        extract(year from c.loss_date) * 10000
        + extract(month from c.loss_date) * 100
        + extract(day from c.loss_date) as integer
    ) as loss_date_key,
    c.loss_date,
    cast({{ dbt.date_trunc('month', 'c.loss_date') }} as date) as accident_month,
    c.reported_date,
    c.closed_date,
    c.claim_status,
    c.is_open,
    c.cause_of_loss,
    c.case_reserve,
    c.payment_count,
    c.paid_indemnity,
    c.paid_expense,
    c.recoveries,
    c.net_paid,
    c.incurred_loss,
    dp.coverage_limit as coverage_limit_at_loss,
    dp.deductible as deductible_at_loss,
    c.days_to_report,
    c.days_open,
    c.is_loss_within_term,
    c.is_reported_date_corrected,
    c.is_reserve_corrected
from {{ ref('int_claims_enriched') }} as c
left join {{ ref('dim_policy') }} as dp
    on c.policy_id = dp.policy_id
        and c.loss_date >= dp.effective_from
        and c.loss_date < dp.effective_to
