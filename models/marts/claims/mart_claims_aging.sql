{#-
    Open-claim inventory aged by days since report, as of var('as_of_date').
    Every product line x bucket combination is present (zero-filled) so BI
    tiles never silently disappear.
-#}

with buckets as (
    select
        1 as bucket_order,
        '0-30 days' as aging_bucket,
        0 as min_days,
        30 as max_days
    union all
    select
        2 as bucket_order,
        '31-90 days' as aging_bucket,
        31 as min_days,
        90 as max_days
    union all
    select
        3 as bucket_order,
        '91-180 days' as aging_bucket,
        91 as min_days,
        180 as max_days
    union all
    select
        4 as bucket_order,
        '181-365 days' as aging_bucket,
        181 as min_days,
        365 as max_days
    union all
    select
        5 as bucket_order,
        '365+ days' as aging_bucket,
        366 as min_days,
        100000 as max_days
),

open_claims as (
    select *
    from {{ ref('fct_claims') }}
    where is_open
),

spine as (
    select
        pl.product_line_code,
        pl.product_line_name,
        b.*
    from {{ ref('stg_product_lines') }} as pl
    cross join buckets as b
)

select
    {{ surrogate_key(['s.product_line_code', 's.aging_bucket']) }} as aging_sk,
    cast('{{ var("as_of_date") }}' as date) as as_of_date,
    s.product_line_code,
    s.product_line_name,
    s.bucket_order,
    s.aging_bucket,
    count(c.claim_id) as open_claim_count,
    coalesce(sum(c.case_reserve), 0) as case_reserve,
    coalesce(sum(c.net_paid), 0) as net_paid_to_date,
    coalesce(sum(c.incurred_loss), 0) as incurred_loss,
    cast(avg(c.days_open) as decimal(10, 1)) as avg_days_open,
    max(c.days_open) as max_days_open
from spine as s
left join open_claims as c
    on s.product_line_code = c.product_line_code
        and c.days_open between s.min_days and s.max_days
group by
    s.product_line_code, s.product_line_name, s.bucket_order, s.aging_bucket
