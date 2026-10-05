{#- Calendar dimension spanning the portfolio window plus a year either side. -#}

with spine as (
    {{ dbt.date_spine(
        datepart="day",
        start_date="cast('2023-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
),

days as (
    select cast(date_day as date) as date_day from spine
)

select
    cast(
        extract(year from date_day) * 10000
        + extract(month from date_day) * 100
        + extract(day from date_day) as integer
    ) as date_key,
    date_day,
    cast(extract(year from date_day) as integer) as calendar_year,
    cast(extract(quarter from date_day) as integer) as calendar_quarter,
    cast(extract(month from date_day) as integer) as calendar_month,
    case cast(extract(month from date_day) as integer)
        when 1 then 'January' when 2 then 'February' when 3 then 'March'
        when 4 then 'April' when 5 then 'May' when 6 then 'June'
        when 7 then 'July' when 8 then 'August' when 9 then 'September'
        when 10 then 'October' when 11 then 'November' else 'December'
    end as month_name,
    cast({{ dbt.date_trunc('month', 'date_day') }} as date) as month_start_date,
    cast({{ dbt.last_day('date_day', 'month') }} as date) as month_end_date,
    cast({{ dbt.date_trunc('quarter', 'date_day') }} as date) as quarter_start_date,
    cast({{ iso_day_of_week('date_day') }} as integer) as iso_day_of_week,
    {{ iso_day_of_week('date_day') }} in (6, 7) as is_weekend,
    date_day = cast({{ dbt.last_day('date_day', 'month') }} as date) as is_month_end
from days
