from datetime import datetime

import pandas as pd
from airflow.decorators import dag, task
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.utils import read_sql_file
from sqlalchemy import text

log = LoggingMixin().log

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2024, 6, 30, 7, 0))


@task
def populate_f_segmentacao_simon(logical_date: datetime | None = None):
    engine = MsSqlHook(mssql_conn_id="db_engenharia").get_sqlalchemy_engine()

    df = pd.read_sql_query(read_sql_file("DBO.SIM_EQUIPAMENTOS.SQL", __file__), engine)

    merge_query = read_sql_file("insert_DBO.FSEGMENTACAO_SIMON.sql", __file__)

    params_list = df.to_dict(orient="records")

    now = datetime.now()

    for row in params_list:
        row["data"] = logical_date.strftime("%Y-%m-%d")  # pyright: ignore
        row["updated_at"] = now

    log.info(f"[START] Executando merge para {len(params_list)} equipamentos")

    with engine.begin() as conn:
        conn.execute(text(merge_query), params_list)  # pyright: ignore[reportCallIssue]

    log.info("[DONE] Merge concluído")


@dag(
    dag_id="F_SIMON_SEGMENTACAO",
    default_args=default_args,
    schedule="0 7 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["elipse", "segmentacao", "silver"],
)
def dag_factory():
    populate_f_segmentacao_simon()


dag_factory()
