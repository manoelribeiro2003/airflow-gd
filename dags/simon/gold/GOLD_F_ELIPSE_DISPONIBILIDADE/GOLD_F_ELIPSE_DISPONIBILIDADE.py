from datetime import datetime, timedelta

import duckdb as ddb
from airflow.datasets import Dataset
from airflow.decorators import dag, task
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import get_duckdb_conn
from global_modules.partitions import monthly_partition_bounds
from global_modules.utils import read_sql_file

log = LoggingMixin().log

gold_dataset = Dataset("elipse://gold/f_disponibilidade_simon")

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))


@task
def ensure_partition():
    start, end = monthly_partition_bounds(datetime.now() + timedelta(days=30))

    partition_name = f"oee_fparadas_p_{start:%Y_%m}"

    create_partition = (
        f"CREATE TABLE IF NOT EXISTS gold.{partition_name} "
        f"PARTITION OF gold.oee_fparadas "
        f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')"
    )

    pg_con_str = get_duckdb_conn("pg")

    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_con_str}' AS pg (TYPE POSTGRES);")

        log.info(f"[INFO] Criando partição: \n {create_partition}")
        con.execute(f"CALL postgres_execute('pg', $${create_partition}$$)")
        log.info(f"[DONE] Partição gold.{partition_name}.")


@dag(
    dag_id="GOLD_F_DISPONIBILIDADE_SIMON",
    default_args=default_args,
    schedule=[gold_dataset],
    catchup=False,
    max_active_runs=1,
    tags=["elipse", "self_service", "disponibilidade", "gold"],
)
def dag_factory():
    partition = ensure_partition()

    transform = SQLExecuteQueryOperator(
        task_id="transform_silver_into_gold",
        conn_id="postgres_eng_server",
        sql=read_sql_file("transform_query.sql", __file__),
    )

    vacuum_analyze = SQLExecuteQueryOperator(
        task_id="vacuum_analyze_task",
        sql="VACUUM ANALYZE elipse.gold.oee_fparadas;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

    _ = partition >> transform >> vacuum_analyze


dag_factory()
