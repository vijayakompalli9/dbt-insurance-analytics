{#-
    Keep one row per `partition_by` key, preferring the first row by `order_by`
    (e.g. `_loaded_at desc`). Written as a portable subquery (no QUALIFY). The
    helper column `_dedupe_rn` is left in place; callers select explicit columns.
-#}
{% macro dedupe(relation, partition_by, order_by) -%}
    select *
    from (
        select
            *,
            row_number() over (partition by {{ partition_by }} order by {{ order_by }}) as _dedupe_rn
        from {{ relation }}
    ) as ranked
    where _dedupe_rn = 1
{%- endmacro %}
