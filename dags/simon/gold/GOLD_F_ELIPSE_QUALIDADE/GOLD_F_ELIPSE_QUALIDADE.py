from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from global_modules.dag_defaults import default_dag_args

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))

gold_dataset = Dataset("elipse://gold/f_qualidade_simon")

with DAG(
    "GOLD_F_QUALIDADE_SIMON",
    default_args=default_args,
    schedule=[gold_dataset],
    catchup=False,
    max_active_runs=1,
) as dag:
    transform_data = SQLExecuteQueryOperator(
        task_id="transform_silver_into_gold",
        conn_id="postgres_eng_server",
        sql="./sql_files/transform_qualidade.sql",
    )

    vacuum_analyze_task = SQLExecuteQueryOperator(
        task_id="vacuum_analyze_task",
        sql="VACUUM ANALYZE elipse.gold.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

_ = transform_data >> vacuum_analyze_task
