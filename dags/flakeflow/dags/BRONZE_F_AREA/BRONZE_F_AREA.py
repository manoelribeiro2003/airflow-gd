from datetime import datetime, timedelta
from pathlib import Path

import connectorx as cx
import duckdb as ddb
from airflow.decorators import dag, task
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import get_cx_conn, get_duckdb_conn
from global_modules.pg_load import replace_pg_table
from global_modules.utils import get_parquet_file, get_sentinel_file, read_sql_file

log = LoggingMixin().log

default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 7, 0))

DDB_PG_FLAKEFLOW = get_duckdb_conn("pg_flakeflow")


def _get_parquet_file() -> Path:
    return get_parquet_file("main", __file__)


def _get_sentinel(name: str) -> Path:
    return get_sentinel_file(name, __file__)


@task(retries=3, retry_delay=timedelta(minutes=2))
def extract_data():
    parquet_file = _get_parquet_file()

    if parquet_file.exists():
        log.info("[SKIP] extração já processada")
        return

    log.info("[START] Extraindo dados de Area do flakeflow")

    df = cx.read_sql(
        get_cx_conn("flakeflow"),
        read_sql_file("extract_data.sql", __file__),
        return_type="arrow",
    )

    log.info(f"[DONE QUERY] {df.shape[0]} linhas, {(df.nbytes / (1024**2)):.2f}MB")

    if df.shape[0] == 0:
        log.info("[SKIP] Nenhum registro na fonte")
        return

    temp_file = parquet_file.with_suffix(".tmp")

    with ddb.connect() as con:
        con.register("df", df)
        con.execute(f"COPY (SELECT * FROM df) TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    del df

    temp_file.rename(parquet_file)
    log.info("[DONE] parquet gravado")


@task(retries=2, retry_delay=timedelta(minutes=1))
def load_table():
    sentinel = _get_sentinel("load_table")

    if sentinel.exists():
        log.info("[SKIP] load_table já concluído")
        return

    parquet_file = _get_parquet_file()

    if not parquet_file.exists():
        log.info("[SKIP] Nenhum dado para carregar")
        return

    with ddb.connect() as con:
        size_mb = con.execute(
            "SELECT SUM(total_uncompressed_size) / (1024*1024.0) "
            f"FROM parquet_metadata(['{parquet_file}'])"
        ).fetchone() or (0,)
        log.info(f"[START] Carregando parquet ({size_mb[0]:.2f}MB)")

    with ddb.connect() as con:
        con.execute(f"ATTACH '{DDB_PG_FLAKEFLOW}' AS pg (TYPE POSTGRES);")

        total_rows = replace_pg_table(
            con,
            "ferramental.area",
            f"SELECT *, CURRENT_TIMESTAMP AS loaded_at FROM read_parquet('{parquet_file}')",
        )

    sentinel.touch()
    log.info(f"[DONE] ferramental.area recarregada — {total_rows} registros")


@task
def clear_cache():
    log.info("[CLEANUP] Limpando parquets e sentinelas.")

    _get_parquet_file().unlink(missing_ok=True)
    _get_sentinel("load_table").unlink(missing_ok=True)


@dag(
    dag_id="BRONZE_F_AREA",
    default_args=default_args,
    schedule="0 7 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["flakeflow", "area", "bronze"],
)
def dag_factory():
    extract = extract_data()
    load = load_table()
    clear = clear_cache()

    _ = extract >> load >> clear


dag_factory()
