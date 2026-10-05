{#-
    Resolve a raw landing table.

    Locally the "raw zone" is populated by `dbt seed`, so staging must `ref()` the
    seed to get a DAG edge (otherwise a cold `dbt build` races the seed load).
    In a real warehouse the same tables are landed by an EL tool and are read via
    `source()`, which is also where freshness is declared.

    Controlled by var('raw_from_seeds'), defaulting to true only on DuckDB.
-#}
{% macro raw_source(table_name) -%}
    {%- if var('raw_from_seeds', target.type == 'duckdb') -%}
        {{ ref(table_name) }}
    {%- else -%}
        {{ source('northwind_raw', table_name) }}
    {%- endif -%}
{%- endmacro %}
