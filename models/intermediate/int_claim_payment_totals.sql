-- Paid-to-date totals per claim, split by payment type.
select
    claim_id,
    count(*) as payment_count,
    sum(case when payment_type = 'INDEMNITY' then payment_amount else 0 end) as paid_indemnity,
    sum(case when payment_type = 'EXPENSE' then payment_amount else 0 end) as paid_expense,
    sum(case when payment_type = 'RECOVERY' then payment_amount else 0 end) as recoveries,
    sum(payment_amount) as net_paid,
    min(payment_date) as first_payment_date,
    max(payment_date) as last_payment_date
from {{ ref('stg_claim_payments') }}
where payment_date <= cast('{{ var("as_of_date") }}' as date)
group by claim_id
