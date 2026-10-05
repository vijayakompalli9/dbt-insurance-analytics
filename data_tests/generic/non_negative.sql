{#- Fails for rows where the column is negative (nulls are ignored; pair with not_null). -#}
{% test non_negative(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < 0
{% endtest %}
