{% for dag in params.execute_timedelta['dag_dependencies'] %}
  SELECT
    GREATEST(COUNT(state), 0),
    '{{ dag }}' AS dag_id,
    (CASE WHEN GREATEST(COUNT(end_date)) = 0 THEN NULL ELSE COUNT(end_date) END) AS end_date
  FROM dag_run
  WHERE
    1 = 1
    AND start_date BETWEEN CURRENT_TIMESTAMP - INTERVAL '{{ params.execute_timedelta['execution_delta'][loop.index - 1] }} MINUTES' AND CURRENT_TIMESTAMP
    AND dag_id= '{{ dag }}'
    AND state='success'
    -- AND run_type= 'scheduled'
  {% if not loop.last  %}
  UNION ALL
  {% endif %}
{% endfor %}
