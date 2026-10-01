from datetime import date, datetime
from pathlib import Path

import duckdb
from airflow import DAG, Dataset
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import SHAREPOINT_EXTRACT_RETRY_ARGS, default_dag_args
from global_modules.database import exec_query_eng_db, get_duckdb_conn
from global_modules.sharepoint.sharepoint import download_sharepoint_file_with_graph_api
from global_modules.sharepoint.sql_cast import build_select_with_cast
from global_modules.utils import read_sql_file
from melhorias.dags.SILVER_MELHORIAS_VOLUME_REAL.fields import VOLUME_FIELDS

log = LoggingMixin().log

MEL_DATA_FAP_DATASET = Dataset("melhorias://silver/data_fap")
MEL_VOLUME_REAL_DATASET = Dataset("melhorias://silver/volume_real")

HERE = Path(__file__).parent

DATA_FILE = Path(HERE, "data.parquet")
STORE_FINISHED_FILE = Path(HERE, "store.finished")
MERGE_FINISHED_FILE = Path(HERE, "merge.finished")

# Site/biblioteca onde o Qlik salva o .parquet de volumes (IDEIA.md). O caminho do
# arquivo (relativo à raiz da document library) é configurável via Airflow Variable.
SHAREPOINT_SITE_URL = "https://grendenecombr.sharepoint.com/sites/Dados_Indicadores"
DEFAULT_DRIVE_PATH = "Arquivos Melhorias/volume_aderencia_melhorias.parquet"

STG_TABLE = "dbo.stg_mel_volume_real"


def _range_start() -> date:
    """Primeiro dia do mês, MEL_VOLUME_REAL_MONTHS meses atrás (default 3)."""
    months = int(Variable.get("MEL_VOLUME_REAL_MONTHS", 3))
    today = date.today()
    month_index = today.year * 12 + (today.month - 1) - months
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


@task(**SHAREPOINT_EXTRACT_RETRY_ARGS)
def extract_sharepoint():
    if DATA_FILE.exists():
        log.info("[SKIP] Parquet já existe, pulando extração")
        return

    drive_path = Variable.get("MEL_VOLUME_REAL_DRIVE_PATH", DEFAULT_DRIVE_PATH)
    log.info(f"[START] Baixando parquet de volumes: {drive_path}")

    content = download_sharepoint_file_with_graph_api(
        drive_path=drive_path,
        site_url=SHAREPOINT_SITE_URL,
    )

    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_bytes(content)
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

    range_start = _range_start().isoformat()
    log.info(f"[START] Carregando parquet (reporte_data >= {range_start})")

    conn_str = get_duckdb_conn("dbengenharia")

    with duckdb.connect() as con:
        con.execute("INSTALL mssql FROM community;")
        con.execute("LOAD mssql;")
        con.execute(f"ATTACH '{conn_str}' AS db (TYPE mssql);")
        # Cast explícito (inferência não é confiável) + filtro de range antes do COPY.
        projection = build_select_with_cast(DATA_FILE, VOLUME_FIELDS)
        filtered = f"SELECT * FROM ({projection}) WHERE \"reporte_data\" >= DATE '{range_start}'"
        con.execute(f"COPY ({filtered}) TO 'db.{STG_TABLE}' (FORMAT 'bcp', REPLACE true);")

    log.info(f"[DONE] Dados inseridos em {STG_TABLE}")
    STORE_FINISHED_FILE.touch()


@task(outlets=[MEL_VOLUME_REAL_DATASET])
def sync_layer():
    if MERGE_FINISHED_FILE.exists():
        log.info("[SKIP] merge já concluído")
        return

    range_start = _range_start().isoformat()
    log.info(f"[START] Executando merge (range_start={range_start})")

    sql = read_sql_file("merge_volume_real.sql", __file__).replace("{{ range_start }}", range_start)
    exec_query_eng_db(sql)

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
    dag_id="SILVER_MELHORIAS_VOLUME_REAL",
    default_args=default_args,
    schedule=[MEL_DATA_FAP_DATASET],
    catchup=False,
    max_active_runs=1,
    tags=["melhorias", "silver"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    _ = start >> extract_sharepoint() >> store_stg() >> sync_layer() >> delete_cache() >> end
