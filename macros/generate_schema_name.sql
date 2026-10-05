{#-
    Schema naming policy.
      * target `prod`: use the custom schema verbatim (raw, staging, marts ...), so
        production objects land in clean, stable schemas.
      * any other target (dev, ci): prefix with the target schema
        (analytics_staging, analytics_marts ...), so developers and CI never collide
        with production and the whole build is disposable.
    Models without a custom schema use the target schema in every environment.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
