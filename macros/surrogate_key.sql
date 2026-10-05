{#-
    Deterministic surrogate key: md5 over the null-safe, delimiter-joined text of
    the given columns. Uses dbt's cross-database `hash`, `concat` and `type_string`
    so the same SQL compiles on DuckDB, Snowflake and Databricks.
-#}
{% macro surrogate_key(columns) -%}
    {%- set parts = [] -%}
    {%- for col in columns -%}
        {%- do parts.append("coalesce(cast(" ~ col ~ " as " ~ dbt.type_string() ~ "), '_null_')") -%}
        {%- if not loop.last %}{% do parts.append("'|'") %}{% endif -%}
    {%- endfor -%}
    {{ dbt.hash(dbt.concat(parts)) }}
{%- endmacro %}
