{#- Written and earned premium at policy x calendar-month grain. -#}

with monthly as (
    select
        policy_id,
        product_line_code,
        calendar_month,
        sum(written_premium) as written_premium,
        sum(earned_premium) as earned_premium
    from {{ ref('int_premium_earned_monthly') }}
    group by policy_id, product_line_code, calendar_month
)

select
    {{ surrogate_key(['m.policy_id', 'm.calendar_month']) }} as premium_month_sk,
    m.policy_id,
    p.customer_id,
    {{ surrogate_key(['p.customer_id']) }} as customer_sk,
    m.product_line_code,
    m.calendar_month,
    m.written_premium,
    m.earned_premium,
    sum(m.written_premium) over (
        partition by m.policy_id order by m.calendar_month
        rows between unbounded preceding and current row
    ) as cumulative_written_premium,
    sum(m.earned_premium) over (
        partition by m.policy_id order by m.calendar_month
        rows between unbounded preceding and current row
    ) as cumulative_earned_premium
from monthly as m
inner join {{ ref('stg_policies') }} as p
    on m.policy_id = p.policy_id
