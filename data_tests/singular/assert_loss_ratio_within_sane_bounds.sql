-- Rolling 12-month incurred loss ratio must be in [0, 3] once the line has credible
-- earned premium. Anything outside that band means a broken join, a sign error or
-- a unit mismatch (cents vs dollars), not a bad year.
select
    product_line_code,
    calendar_month,
    rolling_12m_earned_premium,
    rolling_12m_incurred_loss,
    rolling_12m_loss_ratio
from {{ ref('mart_loss_ratio_monthly') }}
where rolling_12m_earned_premium >= {{ var('min_credible_earned_premium') }}
    and (rolling_12m_loss_ratio < 0 or rolling_12m_loss_ratio > 3)
