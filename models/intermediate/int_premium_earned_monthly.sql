{#-
    Written and earned premium per installment per calendar month.

    * Written: the full installment is written in the month its coverage starts.
    * Earned: pro-rata by day over the installment's coverage period, stopping at
      the earlier of cancellation and the as-of date. A coverage month (e.g.
      15 Jan -> 15 Feb) touches at most two calendar months, so each installment
      contributes at most two earned rows.
-#}

{% set as_of_excl = dbt.dateadd('day', 1, "cast('" ~ var('as_of_date') ~ "' as date)") %}

with cancellations as (
    select
        policy_id,
        min(cancellation_date) as cancellation_date
    from {{ ref('int_policy_versions') }}
    group by policy_id
),

installments as (
    select
        pr.premium_id,
        pr.policy_id,
        po.product_line_code,
        pr.coverage_start_date,
        pr.coverage_end_date,
        pr.written_premium,
        {{ dbt.datediff('pr.coverage_start_date', 'pr.coverage_end_date', 'day') }} as coverage_days,
        -- Exclusive end of the earning window.
        least(
            pr.coverage_end_date,
            coalesce(cx.cancellation_date, cast('9999-12-31' as date)),
            {{ as_of_excl }}
        ) as earn_end_date,
        cast({{ dbt.date_trunc('month', 'pr.coverage_start_date') }} as date) as start_month,
        cast({{ dbt.date_trunc('month', dbt.dateadd('day', -1, 'pr.coverage_end_date')) }} as date)
            as end_month
    from {{ ref('stg_premiums') }} as pr
    inner join {{ ref('stg_policies') }} as po
        on pr.policy_id = po.policy_id
    left join cancellations as cx
        on pr.policy_id = cx.policy_id
),

bounded as (
    select
        *,
        -- Exclusive end of the earning window inside the start month.
        least(cast({{ dbt.dateadd('month', 1, 'start_month') }} as date), earn_end_date) as first_month_end
    from installments
),

earning as (
    -- Round the installment's total earned once; segment 2 takes the remainder so the
    -- two monthly pieces always sum exactly to the rounded total (never above written).
    select
        *,
        cast(
            written_premium
            * greatest({{ dbt.datediff('coverage_start_date', 'earn_end_date', 'day') }}, 0)
            / coverage_days as decimal(18, 2)
        ) as earned_total,
        cast(
            written_premium
            * greatest({{ dbt.datediff('coverage_start_date', 'first_month_end', 'day') }}, 0)
            / coverage_days as decimal(18, 2)
        ) as earned_first_month
    from bounded
)

-- Segment 1: the month the coverage starts (premium is written here).
select
    premium_id,
    policy_id,
    product_line_code,
    start_month as calendar_month,
    written_premium,
    earned_first_month as earned_premium
from earning

union all

-- Segment 2: the following month, when the coverage month straddles a month boundary.
select
    premium_id,
    policy_id,
    product_line_code,
    end_month as calendar_month,
    cast(0 as decimal(18, 2)) as written_premium,
    earned_total - earned_first_month as earned_premium
from earning
where end_month > start_month
