{#- Convert integer cents to a fixed-precision dollar amount. -#}
{% macro cents_to_dollars(column_name, scale=2) -%}
    cast(({{ column_name }}) / 100.0 as decimal(18, {{ scale }}))
{%- endmacro %}

{#- Divide, returning null instead of erroring / infinity when the denominator is 0 or null. -#}
{% macro safe_divide(numerator, denominator) -%}
    case
        when ({{ denominator }}) is null or ({{ denominator }}) = 0 then null
        else cast({{ numerator }} as double) / cast({{ denominator }} as double)
    end
{%- endmacro %}
