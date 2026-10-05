{#- Fails for every row where `expression` is not true (optionally filtered by `where_clause`).
    `column_name` is accepted so the test can be attached at column level; it is unused. -#}
{% test expression_is_true(model, expression, column_name=none, where_clause=none) %}
select *
from {{ model }}
where not ({{ expression }})
{% if where_clause %}
  and ({{ where_clause }})
{% endif %}
{% endtest %}
