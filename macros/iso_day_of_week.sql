{#- ISO day of week (1 = Monday ... 7 = Sunday), dispatched per adapter. -#}
{% macro iso_day_of_week(column_name) -%}
    {{ return(adapter.dispatch('iso_day_of_week', 'insurance_analytics')(column_name)) }}
{%- endmacro %}

{% macro default__iso_day_of_week(column_name) -%}
    extract(isodow from {{ column_name }})
{%- endmacro %}

{% macro snowflake__iso_day_of_week(column_name) -%}
    dayofweekiso({{ column_name }})
{%- endmacro %}

{% macro databricks__iso_day_of_week(column_name) -%}
    extract(dayofweek_iso from {{ column_name }})
{%- endmacro %}
