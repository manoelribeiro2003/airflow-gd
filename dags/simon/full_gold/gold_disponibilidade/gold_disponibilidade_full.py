import os
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from global_modules.dag_defaults import default_dag_args
from global_modules.utils import read_sql_file

DB = os.environ.get("DATABASE_PROD")
DW_CONN = "postgres_eng_server"

GOLD_TABLE = "gold.oee_fparadas"

# Adicionar o range da carga
data_inicio = "2024-10-01 05:24:00"
data_fim = "2025-01-01 06:00:00"


default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))

gold_dataset = Dataset("elipse://gold/f_disponibilidade_simon_full")

with DAG(
    "GOLD_F_DISPONIBILIDADE_SIMON_FULL",
    default_args=default_args,
    schedule=[gold_dataset],
    catchup=False,
    max_active_runs=1,
    concurrency=4,
    tags=["elipse", "gold", "disponibilidade"],
) as dag:
    transform_data = SQLExecuteQueryOperator(
        task_id="transform_silver_into_gold",
        conn_id=DW_CONN,
        sql=read_sql_file("transform_query_full.sql", __file__),
        params={"hora_inicio": data_inicio, "hora_fim": data_fim, "database": DB},
    )
    vacuum_task = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql=f"VACUUM {DB}.{GOLD_TABLE};",
        conn_id=DW_CONN,
        autocommit=True,  # Isso desabilita a transação para permitir o VACUUM
    )
    analyze_task = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql=f"ANALYZE {DB}.{GOLD_TABLE};",
        conn_id=DW_CONN,
        autocommit=True,
    )

_ = vacuum_task >> analyze_task >> transform_data
