{% test unique_combination_of_columns(model, column_list) %}
select {{ column_list | join(', ') }}
from {{ model }}
group by {{ column_list | join(', ') }}
having count(*) > 1
{% endtest %}
