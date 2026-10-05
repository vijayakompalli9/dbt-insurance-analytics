-- Every claim in the fact must resolve to a known policy, the policy version in force
-- on the loss date, and a known customer.
select
    f.claim_id,
    f.policy_id,
    f.policy_version_sk
from {{ ref('fct_claims') }} as f
left join {{ ref('dim_policy') }} as p
    on f.policy_version_sk = p.policy_version_sk
left join {{ ref('dim_customer') }} as c
    on f.customer_sk = c.customer_sk
where p.policy_version_sk is null
    or c.customer_sk is null
    or p.policy_id <> f.policy_id
