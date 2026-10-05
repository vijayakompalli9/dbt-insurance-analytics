{#- Fails for rows outside [min_value, max_value]; either bound may be omitted. -#}
{% test accepted_range(model, column_name, min_value=none, max_value=none, where_clause=none) %}
select {{ column_name }}
from {{ model }}
where (
    1 = 0
    {% if min_value is not none %} or {{ column_name }} < {{ min_value }} {% endif %}
    {% if max_value is not none %} or {{ column_name }} > {{ max_value }} {% endif %}
)
{% if where_clause %} and ({{ where_clause }}) {% endif %}
{% endtest %}
