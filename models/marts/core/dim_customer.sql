{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

with policy_stats as (
    select
        customer_id,
        count(*) as policy_count,
        min(effective_date) as first_policy_effective_date,
        count(distinct product_line_code) as product_line_count
    from {{ ref('stg_policies') }}
    group by customer_id
),

customers as (
    select
        c.*,
        {{ dbt.datediff('c.date_of_birth', as_of, 'day') }} / 365.25 as age_years_exact,
        {{ dbt.datediff('c.customer_since_date', as_of, 'day') }} / 365.25 as tenure_years_exact
    from {{ ref('stg_customers') }} as c
)

select
    {{ surrogate_key(['c.customer_id']) }} as customer_sk,
    c.customer_id,
    c.customer_type,
    case
        when c.customer_type = 'BUSINESS' then c.last_name
        else c.first_name || ' ' || c.last_name
    end as customer_name,
    c.email,
    c.state_code,
    c.date_of_birth,
    cast(floor(c.age_years_exact) as integer) as age_years,
    case
        when c.customer_type = 'BUSINESS' then 'N/A (business)'
        when c.age_years_exact < 30 then '18-29'
        when c.age_years_exact < 45 then '30-44'
        when c.age_years_exact < 60 then '45-59'
        else '60+'
    end as age_band,
    c.customer_since_date,
    cast(floor(c.tenure_years_exact) as integer) as tenure_years,
    coalesce(s.policy_count, 0) as policy_count,
    coalesce(s.product_line_count, 0) as product_line_count,
    s.first_policy_effective_date
from customers as c
left join policy_stats as s
    on c.customer_id = s.customer_id
