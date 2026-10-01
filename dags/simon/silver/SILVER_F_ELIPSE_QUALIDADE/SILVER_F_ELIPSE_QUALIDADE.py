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

gold_dataset = Dataset("elipse://gold/f_qualidade_simon")

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 2, 21, 6, 5))

extraction_sql = "extract_qualidade.sql"


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
                            PARTITION BY "E3TimeStamp", Codigo, "Maquina_ID"
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
    pg_con_str = get_duckdb_conn("pg")
    tmp_table = "silver.temp_qualidade"

    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_con_str}' AS pg (TYPE POSTGRES);")

        check_table_query = f"SELECT to_regclass('{tmp_table}') IS NOT NULL"
        tmp_table_exists = con.sql(
            f"SELECT * FROM postgres_query('pg', $${check_table_query}$$)"
        ).fetchone()

        if tmp_table_exists is not None and tmp_table_exists[0]:
            log.info(f"[SKIP] '{tmp_table}' já existe")
            return

        size_mb = con.sql(
            "SELECT SUM(total_uncompressed_size) / (1024*1024.0) "
            f"FROM parquet_metadata([{paths_glob}])"
        ).fetchone() or (0,)

        log.info(f"[START] Carregando parquets ({size_mb[0]:.2f}MB)")

        con.execute(
            "CREATE TEMP VIEW v_source AS "
            f"SELECT * FROM read_parquet([{paths_glob}], union_by_name=true)"
        )

        con.execute(f"CREATE OR REPLACE TABLE pg.{tmp_table} AS SELECT * FROM v_source LIMIT 0")

        total_rows = con.execute(f"INSERT INTO pg.{tmp_table} SELECT * FROM v_source").fetchone()

        log.info(f"[DONE] Total linhas inseridas: {total_rows}")

    sentinel.touch()


@task
def clear_cache():
    log.info("[CLEANUP] Limpando arquivos e sentinelas.")
    for parquet in _get_parquet_map().values():
        parquet.unlink(missing_ok=True)
    _get_sentinel("concat_and_load_stage").unlink(missing_ok=True)


@dag(
    dag_id="SILVER_F_QUALIDADE_SIMON",
    default_args=default_args,
    schedule="20 9,18 * * *",
    catchup=False,
    max_active_runs=1,
    concurrency=4,
    tags=["elipse", "qualidade", "silver"],
)
def dag_factory():
    sob_data = extract_data.override(task_id="extract_data_sob")("sob")
    for_data = extract_data.override(task_id="extract_data_for")("for")
    cra_data = extract_data.override(task_id="extract_data_cra")("cra")

    concat = concat_and_load_stage()

    vacuum = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql="VACUUM elipse.silver.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

    analyze = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql="ANALYZE elipse.silver.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )

    merge = SQLExecuteQueryOperator(
        task_id="merge_table_and_drop_temp",
        conn_id="postgres_eng_server",
        sql=read_sql_file("merge_query.sql", __file__),
        autocommit=True,
        outlets=[gold_dataset],
    )

    clear = clear_cache()

    _ = [sob_data, for_data, cra_data] >> concat >> vacuum >> analyze >> merge >> clear


dag_factory()
