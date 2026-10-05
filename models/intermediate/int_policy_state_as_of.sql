{#-
    Policy state "as of" var('as_of_date'): the latest version on or before that
    date, with a derived lifecycle status. This is the relation the SCD2 snapshot
    (snapshots/snap_policy.yml) watches. Replaying the snapshot over successive
    as-of dates (see `make history`) reconstructs a realistic version history.
-#}

{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

with ranked as (
    select
        *,
        row_number() over (
            partition by policy_id order by version_start_date desc, event_order desc
        ) as rn
    from {{ ref('int_policy_versions') }}
    where version_start_date <= {{ as_of }}
),

current_version as (
    select * from ranked
    where rn = 1
),

cancellations as (
    select
        policy_id,
        min(cancellation_date) as cancellation_date
    from {{ ref('int_policy_versions') }}
    where cancellation_date <= {{ as_of }}
    group by policy_id
)

select
    v.policy_id,
    v.policy_number,
    v.customer_id,
    v.product_line_code,
    v.sales_channel,
    v.effective_date,
    v.expiration_date,
    c.cancellation_date,
    v.annual_premium,
    v.coverage_limit,
    v.deductible,
    case
        when v.is_cancelled then 'CANCELLED'
        when v.expiration_date <= {{ as_of }} then 'EXPIRED'
        else 'ACTIVE'
    end as policy_status,
    -- Business timestamp of the latest change; drives dbt_valid_from in the snapshot.
    cast(
        case
            when not v.is_cancelled and v.expiration_date <= {{ as_of }} then v.expiration_date
            else v.version_start_date
        end as timestamp
    ) as state_updated_at,
    {{ as_of }} as as_of_date
from current_version as v
left join cancellations as c
    on v.policy_id = c.policy_id
