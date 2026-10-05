{#-
    Claims joined to their policy and paid-to-date totals. Claims whose policy_id
    does not exist (orphans from the upstream system) are excluded here; they are
    surfaced by the warn-severity relationships test on stg_claims.
-#}

{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

select
    c.claim_id,
    c.claim_number,
    c.policy_id,
    p.customer_id,
    p.product_line_code,
    c.loss_date,
    c.reported_date,
    c.closed_date,
    c.claim_status,
    c.cause_of_loss,
    c.claim_status = 'OPEN' as is_open,
    c.case_reserve,
    coalesce(t.payment_count, 0) as payment_count,
    coalesce(t.paid_indemnity, 0) as paid_indemnity,
    coalesce(t.paid_expense, 0) as paid_expense,
    coalesce(t.recoveries, 0) as recoveries,
    coalesce(t.net_paid, 0) as net_paid,
    coalesce(t.net_paid, 0) + c.case_reserve as incurred_loss,
    {{ dbt.datediff('c.loss_date', 'c.reported_date', 'day') }} as days_to_report,
    {{ dbt.datediff('c.reported_date', 'coalesce(c.closed_date, ' ~ as_of ~ ')', 'day') }} as days_open,
    c.loss_date >= p.effective_date and c.loss_date < p.expiration_date as is_loss_within_term,
    c.is_reported_date_corrected,
    c.is_reserve_corrected
from {{ ref('stg_claims') }} as c
inner join {{ ref('stg_policies') }} as p
    on c.policy_id = p.policy_id
left join {{ ref('int_claim_payment_totals') }} as t
    on c.claim_id = t.claim_id
where c.reported_date <= {{ as_of }}
