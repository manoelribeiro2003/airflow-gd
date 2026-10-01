from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
from airflow import DAG, Dataset
from airflow.decorators import task
from airflow.operators.empty import EmptyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import SHAREPOINT_EXTRACT_RETRY_ARGS, default_dag_args
from global_modules.database import exec_query_eng_db, get_duckdb_conn
from global_modules.sharepoint.envs import get_sharepoint_search_days
from global_modules.sharepoint.sharepoint import fetch_sharepoint_items_with_graph_api
from global_modules.sharepoint.sql_cast import build_select_with_cast
from global_modules.utils import read_sql_file
from melhorias.dags.BRONZE_MELHORIAS_GANHOS.fields import DATETIME_CONFIG, LIST_FIELDS

log = LoggingMixin().log

MEL_GANHOS_DATASET = Dataset("melhorias://bronze/melhoria_ganhos")

HERE = Path(__file__).parent

DATA_FILE = Path(HERE, "data.parquet")
STORE_FINISHED_FILE = Path(HERE, "store.finished")
MERGE_FINISHED_FILE = Path(HERE, "merge.finished")


@task(**SHAREPOINT_EXTRACT_RETRY_ARGS)
def extract_sharepoint():
    if DATA_FILE.exists():
        log.info("[SKIP] Parquet já existe, pulando extração")
        return

    # Janela vem de SHAREPOINT_SEARCH_DAYS (default 90); a mesma fonte alimenta o DELETE
    # do merge, garantindo que fetch e reap usem o mesmo numero de dias.
    days = get_sharepoint_search_days()

    log.info(f"[START] Buscando itens no SharePoint (janela de {days} dias)")

    df = fetch_sharepoint_items_with_graph_api(
        list_fields=LIST_FIELDS,
        site_url="https://grendenecombr.sharepoint.com/sites/dados_industriais/sis_melhorias",
        list_name="Melhorias",
        start_date=datetime.now(timezone.utc) - timedelta(days=days),
        datetime_config=DATETIME_CONFIG,
    )

    log.info(f"[INFO] {len(df)} registros extraídos do SharePoint")

    tmp = DATA_FILE.with_suffix(".tmp")
    df.to_parquet(tmp)
    tmp.rename(DATA_FILE)

    log.info(f"[DONE] Parquet gravado → {DATA_FILE.name}")


@task
def store_stg():
    if STORE_FINISHED_FILE.exists():
        log.info("[SKIP] store já concluído")
        return

    if not DATA_FILE.exists():
        log.warning("[WARN] Parquet não encontrado, pulando store")
        return

    log.info("[START] Carregando parquet")

    conn_str = get_duckdb_conn("dbengenharia")

    table_name = "dbo.stg_mel_ganhos"

    with duckdb.connect() as con:
        con.execute("INSTALL mssql FROM community;")
        con.execute("LOAD mssql;")
        con.execute(f"ATTACH '{conn_str}' AS db (TYPE mssql);")
        # Temos que fazer o cast para os tipos corretos, pois a inferência não é confiável.
        projection = build_select_with_cast(DATA_FILE, LIST_FIELDS)
        con.execute(f"COPY ({projection}) TO 'db.{table_name}' (FORMAT 'bcp', REPLACE true);")

    log.info(f"[DONE] Dados inseridos em {table_name}")
    STORE_FINISHED_FILE.touch()


@task(outlets=[MEL_GANHOS_DATASET])
def sync_bronze_layer():
    if MERGE_FINISHED_FILE.exists():
        log.info("[SKIP] merge_data já concluído")
        return

    log.info("[START] Executando SQL")

    days = get_sharepoint_search_days()
    exec_query_eng_db(read_sql_file("merge_ganhos.sql", __file__), {"search_days": days})

    MERGE_FINISHED_FILE.touch()
    log.info("[DONE] Merge concluído")


@task
def delete_cache():
    log.info("[CLEANUP] Removendo cache")

    DATA_FILE.unlink(missing_ok=True)
    STORE_FINISHED_FILE.unlink(missing_ok=True)
    MERGE_FINISHED_FILE.unlink(missing_ok=True)

    log.info("[DONE] Cache limpo")


default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 6, 5))

with DAG(
    dag_id="BRONZE_MELHORIA_GANHOS",
    default_args=default_args,
    schedule="0 */3 * * *",  # A cada 3 horas
    catchup=False,
    max_active_runs=1,
    tags=["melhorias", "bronze"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    _ = start >> extract_sharepoint() >> store_stg() >> sync_bronze_layer() >> delete_cache() >> end
