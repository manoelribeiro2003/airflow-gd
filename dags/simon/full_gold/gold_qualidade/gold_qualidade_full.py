from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from global_modules.dag_defaults import default_dag_args

# Adicionar o range da carga
data_inicio = "2025-01-01 05:25:00"
data_fim = "2025-02-01 05:25:00"


default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))

gold_dataset = Dataset("elipse://gold/f_qualidade_simon_full")

with DAG(
    "GOLD_F_QUALIDADE_SIMON_FULL",
    default_args=default_args,
    schedule=[gold_dataset],
    catchup=False,
    max_active_runs=1,
) as dag:
    transform_data = SQLExecuteQueryOperator(
        task_id="transform_silver_into_gold",
        conn_id="postgres_eng_server",
        sql="./sql_files/full_merge_gold_qualidade.sql",
        params={"data_inicio": data_inicio, "data_fim": data_fim},
    )
    vacuum_task = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql="VACUUM elipse.gold.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,  # Isso desabilita a transação para permitir o VACUUM
    )
    analyze_task = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql="ANALYZE elipse.gold.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

_ = vacuum_task >> analyze_task >> transform_data
