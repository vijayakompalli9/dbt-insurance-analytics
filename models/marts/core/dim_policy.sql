{#-
    SCD Type 2 policy dimension built from the `snap_policy` snapshot.
    One row per policy version. `effective_from` / `effective_to` give a gap-free,
    non-overlapping validity range per policy (the first version is back-dated to
    the policy effective date), so facts can join on "version valid at event date".
-#}

with snap as (
    select
        *,
        row_number() over (partition by policy_id order by dbt_valid_from) as version_number
    from {{ ref('snap_policy') }}
)

select
    {{ surrogate_key(['s.policy_id', 's.dbt_valid_from']) }} as policy_version_sk,
    s.policy_id,
    s.policy_number,
    s.version_number,
    {{ surrogate_key(['s.customer_id']) }} as customer_sk,
    s.customer_id,
    s.product_line_code,
    pl.product_line_name,
    pl.line_of_business,
    s.sales_channel,
    s.effective_date,
    s.expiration_date,
    s.cancellation_date,
    s.policy_status,
    s.annual_premium,
    s.coverage_limit,
    s.deductible,
    cast(s.dbt_valid_from as timestamp) as valid_from,
    cast(s.dbt_valid_to as timestamp) as valid_to,
    case
        when s.version_number = 1 then s.effective_date
        else cast(s.dbt_valid_from as date)
    end as effective_from,
    coalesce(cast(s.dbt_valid_to as date), cast('9999-12-31' as date)) as effective_to,
    s.dbt_valid_to is null as is_current
from snap as s
left join {{ ref('stg_product_lines') }} as pl
    on s.product_line_code = pl.product_line_code
