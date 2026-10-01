from datetime import datetime, timedelta

from airflow.datasets import Dataset
from airflow.decorators import dag
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from global_modules.dag_defaults import default_dag_args
from global_modules.utils import read_sql_file

DS_CADASTROS_SETORES = Dataset("elipse://silver/cadastros_setores")
DS_CADASTROS_MAQUINAS = Dataset("elipse://silver/cadastros_maquinas")
DS_CADASTROS_FABRICAS = Dataset("elipse://silver/cadastros_fabricas")

default_args = default_dag_args(owner="yan.arcanjo", start_date=datetime(2022, 8, 18, 7, 0))


@dag(
    dag_id="GOLD_ELIPSE_DMAQUINAS",
    description="Carga de dados GOLD_D_MAQUINAS_SIMON",
    default_args=default_args,
    schedule=[DS_CADASTROS_SETORES, DS_CADASTROS_MAQUINAS, DS_CADASTROS_FABRICAS],
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=60),
    tags=["elipse", "self_service", "gold"],
)
def dag_factory():
    merge = SQLExecuteQueryOperator(
        task_id="merge_stage_silver",
        conn_id="postgres_eng_server",
        sql=read_sql_file("merge_gold_dElipse_Maquinas.sql", __file__),
        autocommit=True,
    )

    vacuum_analyze = SQLExecuteQueryOperator(
        task_id="vacuum_analyze_task",
        sql="VACUUM ANALYZE elipse.gold.cadastros_maquinas;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

    _ = merge >> vacuum_analyze


dag_factory()
