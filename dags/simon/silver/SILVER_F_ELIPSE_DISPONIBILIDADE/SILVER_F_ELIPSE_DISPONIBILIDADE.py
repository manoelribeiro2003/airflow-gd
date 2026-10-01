import os
from datetime import datetime, timedelta
from pathlib import Path

import connectorx as cx
import duckdb as ddb
from airflow.datasets import Dataset
from airflow.decorators import dag, task
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import Estabelecimento, get_cx_conn, get_duckdb_conn, get_estab_code
from global_modules.utils import get_parquet_file, get_sentinel_file, read_sql_file

log = LoggingMixin().log

DATABASE_ID = os.environ.get("DATABASE_PROD")
DW_CONN = "postgres_eng_server"

STAGE_TABLE = "stage.stage_paradas"
SILVER_TABLE = "silver.oee_fparadas"
extraction_sql = "extract_paradas.sql"

gold_dataset = Dataset("elipse://gold/f_disponibilidade_simon")

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))


def _get_parquet_map() -> dict[Estabelecimento, Path]:
    return {
        "sob": get_parquet_file("sob", __file__),
        "for": get_parquet_file("for", __file__),
        "cra": get_parquet_file("cra", __file__),
    }


def _get_sentinel(name: str) -> Path:
    return get_sentinel_file(name, __file__)


@task(retries=3, retry_delay=timedelta(minutes=2))
def extract_data(estab: Estabelecimento):
    parquet_file = _get_parquet_map()[estab]

    if parquet_file.exists():
        log.info(f"[SKIP] {estab} já processado")
        return

    log.info(f"[START] Extraindo {estab}")

    sql = read_sql_file(extraction_sql, __file__)
    estab_code = get_estab_code(estab)
    sql_with_params = sql.format(estab=estab_code)

    df = cx.read_sql(get_cx_conn(estab), sql_with_params, return_type="arrow")

    log.info(f"[DONE QUERY] recuperados {df.shape[0]} linhas, {(df.nbytes / (1024**2)):.2f}MB")

    temp_file = parquet_file.with_suffix(".tmp")

    with ddb.connect() as con:
        con.register("df", df)
        con.execute(
            f"""
            COPY (
                SELECT * EXCLUDE (rn) FROM (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY "Id"
                            ORDER BY "E3TimeStamp" DESC
                        ) AS rn
                    FROM df
                )
                WHERE rn = 1
            ) TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )

    del df

    temp_file.rename(parquet_file)

    log.info(f"[DONE] {estab} -> parquet gravado (dedup aplicado)")


@task(retries=2, retry_delay=timedelta(minutes=1))
def concat_and_load_stage():
    sentinel = _get_sentinel("concat_and_load_stage")

    if sentinel.exists():
        log.info("[SKIP] concat_and_load_stage já concluído")
        return

    parquet_map = _get_parquet_map()
    parquet_paths = list(parquet_map.values())
    paths_glob = ", ".join(f"'{p}'" for p in parquet_paths)

    pg_conn_str = get_duckdb_conn("pg")

    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE POSTGRES);")

        already_loaded = con.sql(f"SELECT COUNT(1) FROM pg.{STAGE_TABLE}").fetchone()

        if already_loaded and already_loaded[0] > 0:
            log.info(f"[SKIP] '{STAGE_TABLE}' já carregada")
            return

        size_mb = con.sql(
            f"""
            SELECT SUM(total_uncompressed_size) / (1024*1024.0)
            FROM parquet_metadata([{paths_glob}])
            """
        ).fetchone() or (0,)

        log.info(f"[DUCKDB] Iniciando bulk insert ({size_mb[0]:.2f}MB).")

        # Se precisar de máxima performance, mude para COPY ... FROM *.parquet
        total_rows = con.execute(
            f"""
                INSERT INTO pg.{STAGE_TABLE}
                SELECT * FROM read_parquet([{paths_glob}], union_by_name=true)
                """
        ).fetchone() or (0,)

        log.info(f"[DONE] Total linhas inseridas: {total_rows[0]}")

    sentinel.touch()


@task
def clear_cache():
    log.info("[CLEANUP] Limpando arquivos e sentinelas.")
    for parquet in _get_parquet_map().values():
        parquet.unlink(missing_ok=True)
    _get_sentinel("concat_and_load_stage").unlink(missing_ok=True)


@dag(
    dag_id="SILVER_F_DISPONIBILIDADE_SIMON",
    default_args=default_args,
    schedule="30 9,18 * * *",
    catchup=False,
    max_active_runs=1,
    concurrency=4,
    tags=["elipse", "silver", "disponibilidade"],
)
def dag_factory():

    sob_data = extract_data.override(task_id="extract_data_sob")("sob")
    for_data = extract_data.override(task_id="extract_data_for")("for")
    cra_data = extract_data.override(task_id="extract_data_cra")("cra")

    concat = concat_and_load_stage()

    vacuum_task = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql=f"VACUUM {DATABASE_ID}.{SILVER_TABLE};",
        conn_id=DW_CONN,
        autocommit=True,
    )

    analyze_task = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql=f"ANALYZE {DATABASE_ID}.{SILVER_TABLE};",
        conn_id=DW_CONN,
        autocommit=True,
    )

    merge_data = SQLExecuteQueryOperator(
        task_id="merge_stage_silver",
        conn_id=DW_CONN,
        sql=read_sql_file("merge_query.sql", __file__),
        params={
            "source": STAGE_TABLE,
            "target": SILVER_TABLE,
            "database_id": DATABASE_ID,
        },
        autocommit=True,
        outlets=[gold_dataset],
    )

    truncate_stage = SQLExecuteQueryOperator(
        task_id="truncate_stage",
        conn_id=DW_CONN,
        sql=read_sql_file("truncate_stage_paradas.sql", __file__),
        params={"source": STAGE_TABLE, "database_id": DATABASE_ID},
    )

    clear = clear_cache()

    _ = (
        [sob_data, for_data, cra_data]
        >> concat
        >> vacuum_task
        >> analyze_task
        >> merge_data
        >> truncate_stage
        >> clear
    )


dag_factory()
