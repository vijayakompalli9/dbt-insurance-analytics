{#-
    Monthly loss ratio by product line, from the first portfolio month to the
    as-of month. Two complementary views:

    * calendar-month paid loss ratio: net payments made in the month / earned premium;
    * accident-month incurred loss ratio: (net paid to date + case reserve) for
      losses occurring in the month / earned premium in the month.

    Rolling 12-month figures smooth the volatility of a small book and are what
    the singular bounds test checks.
-#}

{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

with months as (
    select distinct month_start_date as calendar_month
    from {{ ref('dim_date') }}
    where month_start_date >= cast('2024-01-01' as date)
        and month_start_date <= {{ as_of }}
),

spine as (
    select
        m.calendar_month,
        pl.product_line_code,
        pl.product_line_name,
        pl.line_of_business,
        pl.target_loss_ratio
    from months as m
    cross join {{ ref('stg_product_lines') }} as pl
),

premium as (
    select
        product_line_code,
        calendar_month,
        sum(written_premium) as written_premium,
        sum(earned_premium) as earned_premium
    from {{ ref('fct_premium_earned') }}
    group by product_line_code, calendar_month
),

paid as (
    select
        product_line_code,
        payment_month as calendar_month,
        sum(payment_amount) as paid_loss
    from {{ ref('fct_claim_payments') }}
    group by product_line_code, payment_month
),

accident as (
    select
        product_line_code,
        accident_month as calendar_month,
        count(*) as reported_claim_count,
        sum(incurred_loss) as accident_month_incurred_loss
    from {{ ref('fct_claims') }}
    group by product_line_code, accident_month
),

joined as (
    select
        s.calendar_month,
        s.product_line_code,
        s.product_line_name,
        s.line_of_business,
        s.target_loss_ratio,
        coalesce(pr.written_premium, 0) as written_premium,
        coalesce(pr.earned_premium, 0) as earned_premium,
        coalesce(pd.paid_loss, 0) as paid_loss,
        coalesce(a.accident_month_incurred_loss, 0) as incurred_loss,
        coalesce(a.reported_claim_count, 0) as claim_count
    from spine as s
    left join premium as pr
        on s.product_line_code = pr.product_line_code and s.calendar_month = pr.calendar_month
    left join paid as pd
        on s.product_line_code = pd.product_line_code and s.calendar_month = pd.calendar_month
    left join accident as a
        on s.product_line_code = a.product_line_code and s.calendar_month = a.calendar_month
),

rolling as (
    select
        *,
        sum(earned_premium) over (
            partition by product_line_code order by calendar_month
            rows between 11 preceding and current row
        ) as rolling_12m_earned_premium,
        sum(incurred_loss) over (
            partition by product_line_code order by calendar_month
            rows between 11 preceding and current row
        ) as rolling_12m_incurred_loss
    from joined
)

select
    {{ surrogate_key(['product_line_code', 'calendar_month']) }} as loss_ratio_month_sk,
    calendar_month,
    product_line_code,
    product_line_name,
    line_of_business,
    written_premium,
    earned_premium,
    paid_loss,
    incurred_loss,
    claim_count,
    cast({{ safe_divide('paid_loss', 'earned_premium') }} as decimal(10, 4)) as paid_loss_ratio,
    cast({{ safe_divide('incurred_loss', 'earned_premium') }} as decimal(10, 4))
        as incurred_loss_ratio,
    rolling_12m_earned_premium,
    rolling_12m_incurred_loss,
    cast(
        {{ safe_divide('rolling_12m_incurred_loss', 'rolling_12m_earned_premium') }}
        as decimal(10, 4)
    ) as rolling_12m_loss_ratio,
    target_loss_ratio,
    cast(
        {{ safe_divide('rolling_12m_incurred_loss', 'rolling_12m_earned_premium') }}
        - target_loss_ratio as decimal(10, 4)
    ) as rolling_12m_variance_to_target
from rolling
