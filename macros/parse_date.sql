{#-
    Parse a text date that may arrive as YYYY-MM-DD, YYYY/MM/DD or MM/DD/YYYY.
    Returns null (never errors) for anything else, so bad values surface in tests
    rather than failing the load. Dispatched per adapter because every warehouse
    spells "try-parse with format" differently.
-#}
{% macro parse_date(column_name) -%}
    {{ return(adapter.dispatch('parse_date', 'insurance_analytics')(column_name)) }}
{%- endmacro %}

{% macro default__parse_date(column_name) -%}
    cast(nullif(trim({{ column_name }}), '') as date)
{%- endmacro %}

{% macro duckdb__parse_date(column_name) -%}
    cast(coalesce(
        try_strptime(nullif(trim({{ column_name }}), ''), '%Y-%m-%d'),
        try_strptime(nullif(trim({{ column_name }}), ''), '%Y/%m/%d'),
        try_strptime(nullif(trim({{ column_name }}), ''), '%m/%d/%Y')
    ) as date)
{%- endmacro %}

{% macro snowflake__parse_date(column_name) -%}
    coalesce(
        try_to_date(nullif(trim({{ column_name }}), ''), 'YYYY-MM-DD'),
        try_to_date(nullif(trim({{ column_name }}), ''), 'YYYY/MM/DD'),
        try_to_date(nullif(trim({{ column_name }}), ''), 'MM/DD/YYYY')
    )
{%- endmacro %}

{% macro databricks__parse_date(column_name) -%}
    coalesce(
        to_date(try_to_timestamp(nullif(trim({{ column_name }}), ''), 'yyyy-MM-dd')),
        to_date(try_to_timestamp(nullif(trim({{ column_name }}), ''), 'yyyy/MM/dd')),
        to_date(try_to_timestamp(nullif(trim({{ column_name }}), ''), 'MM/dd/yyyy'))
    )
{%- endmacro %}
