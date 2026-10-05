-- Cumulative earned premium can never exceed cumulative written premium for a policy
-- (premium is written at the start of each coverage month and earned over it).
-- A one-cent tolerance absorbs per-segment rounding.
select
    policy_id,
    calendar_month,
    cumulative_written_premium,
    cumulative_earned_premium
from {{ ref('fct_premium_earned') }}
where cumulative_earned_premium > cumulative_written_premium + 0.01
