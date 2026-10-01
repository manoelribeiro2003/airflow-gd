from datetime import datetime

from airflow import DAG, Dataset
from airflow.decorators import task
from airflow.operators.empty import EmptyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import exec_query_eng_db
from global_modules.utils import read_sql_file

log = LoggingMixin().log

MEL_APROVACAO_DATASET = Dataset("melhorias://bronze/melhoria_aprovacao")
MEL_GANHOS_DATASET = Dataset("melhorias://bronze/melhoria_ganhos")
MEL_DATA_FAP_DATASET = Dataset("melhorias://silver/data_fap")


@task
def update_dt_fap() -> None:
    log.info("[START] Atualizando dt_fap nas melhorias aprovadas")
    exec_query_eng_db(read_sql_file("update_fap.sql", __file__))
    log.info("[DONE] dt_fap atualizado")


default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 6, 5))

with DAG(
    dag_id="BRONZE_MELHORIA_DATA_FAP",
    default_args=default_args,
    schedule=[MEL_APROVACAO_DATASET, MEL_GANHOS_DATASET],
    catchup=False,
    max_active_runs=1,
    tags=["melhorias", "bronze"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", outlets=[MEL_DATA_FAP_DATASET])

    _ = start >> update_dt_fap() >> end
