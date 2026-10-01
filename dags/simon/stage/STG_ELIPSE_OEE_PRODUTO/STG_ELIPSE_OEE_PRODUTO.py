from datetime import datetime, timedelta
from pathlib import Path

import connectorx as cx
import duckdb as ddb
from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import Estabelecimento, get_cx_conn, get_duckdb_conn, get_estab_code
from global_modules.utils import get_parquet_file, get_sentinel_file, read_sql_file

log = LoggingMixin().log

default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 6, 5))

extraction_sql = "oee_produto.sql"

LOOKBACK_DAYS = 31
N_THREADS = 8

# Por que o buffer de 12h.
# Turno começa 06:00h do dia N.
# Ciclo com E3TimeStamp = 01:00h do dia N+1 → adjustedDate = dia N (shift back).
# Chunk A (OEE dia N, @DataFim=N):
#   ciclos raw: até N+1 06:00 (buffer)
#     → inclui o ciclo, adjustedDate=N, @DataFimAnalise=N → contabilizado ✓
#   Chunk B (OEE dia N+1, @DataInicio=N+1):
#     mesmos ciclos brutos entram, mas adjustedDate=N < @DataInicioAnalise=N+1 → filtrado ✓
# Nenhum ciclo duplicado. Nenhum ciclo perdido.
SHIFT_BUFFER_H = 12  # captura ciclos madrugada que mapeiam para o dia anterior
DAYS_PER_CHUNK = max(1, -(-LOOKBACK_DAYS // N_THREADS))


def _get_parquet_map() -> dict[Estabelecimento, Path]:
    return {
        "sob": get_parquet_file("sob", __file__),
        "for": get_parquet_file("for", __file__),
        "cra": get_parquet_file("cra", __file__),
    }


def _get_sentinel(name: str) -> Path:
    return get_sentinel_file(name, __file__)


def _discover_tables(estab: Estabelecimento) -> list[str]:
    tables = cx.read_sql(
        get_cx_conn(estab),
        read_sql_file("discover_tables.sql", __file__),
        return_type="arrow",
    )
    return tables["TABLE_NAME"].to_pylist()


def _date_chunks(dt_inicio: datetime, dt_fim: datetime) -> list[tuple[datetime, datetime]]:
    date_chunks: list[tuple[datetime, datetime]] = []
    chunk_start = dt_inicio
    while chunk_start < dt_fim:
        chunk_end = min(chunk_start + timedelta(days=DAYS_PER_CHUNK), dt_fim)
        date_chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end
    return date_chunks


def _build_queries(
    table_names: list[str], estab_code, dt_inicio: datetime, dt_fim: datetime
) -> list[str]:
    """Uma query OEE por chunk: ciclos brutos com buffer de turno, análise no intervalo exato."""
    part_template = read_sql_file("ciclo_union_part.sql", __file__)
    extraction_template = read_sql_file(extraction_sql, __file__)

    queries = []
    for oee_start, oee_end in _date_chunks(dt_inicio, dt_fim):
        raw_inicio = oee_start - timedelta(hours=SHIFT_BUFFER_H)
        raw_fim = oee_end + timedelta(hours=SHIFT_BUFFER_H)
        chunk_parts = [
            part_template.format(
                id_maquina=name[6:],
                table_name=name,
                dt_inicio=raw_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                dt_fim=raw_fim.strftime("%Y-%m-%d %H:%M:%S"),
            )
            for name in table_names
        ]
        queries.append(
            extraction_template.format(
                ciclos_union="\nUNION ALL\n".join(chunk_parts),
                estab=estab_code,
                dt_inicio=oee_start.strftime("%Y-%m-%d %H:%M:%S"),
                dt_fim=oee_end.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    return queries


def _write_parquet(df, parquet_file: Path) -> None:
    """Grava parquet ZSTD com write atômico."""
    temp_file = parquet_file.with_suffix(".tmp")

    with ddb.connect() as con:
        con.register("df", df)
        con.execute(f"COPY (SELECT * FROM df) TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    temp_file.rename(parquet_file)


# Lookback de 31 dias no SQL Server 2008 R2; historicamente perto de 18min,
# timeout acima do padrão para absorver variação.
@task(retries=3, retry_delay=timedelta(minutes=2), execution_timeout=timedelta(minutes=90))
def extract_data(estab: Estabelecimento):
    parquet_file = _get_parquet_map()[estab]

    if parquet_file.exists():
        log.info(f"[SKIP] {estab} já processado")
        return

    log.info(f"[START] Extraindo {estab}")

    table_names = _discover_tables(estab)

    if not table_names:
        log.warning(f"[WARN] Nenhuma tabela Ciclo encontrada em {estab}, abortando")
        return

    log.info(f"[INFO] {len(table_names)} tabelas Ciclo em {estab}")

    dt_fim = datetime.now()
    dt_inicio = dt_fim - timedelta(days=LOOKBACK_DAYS)
    estab_code = get_estab_code(estab)

    queries = _build_queries(table_names, estab_code, dt_inicio, dt_fim)

    log.info(
        f"[INFO] Executando {len(queries)} queries em paralelo "
        f"({LOOKBACK_DAYS} dias / {DAYS_PER_CHUNK} dias por chunk, {len(table_names)} tabelas)"
    )
    df = cx.read_sql(get_cx_conn(estab), queries, return_type="arrow")

    log.info(f"[DONE QUERY] recuperados {df.shape[0]} linhas, {(df.nbytes / (1024**2)):.2f}MB")

    _write_parquet(df, parquet_file)

    log.info(f"[DONE] {estab} -> parquet gravado")


@task(retries=2, retry_delay=timedelta(minutes=1))
def store_stage():
    sentinel = _get_sentinel("store_stage")

    if sentinel.exists():
        log.info("[SKIP] store_stage já concluído")
        return

    parquet_map = _get_parquet_map()
    parquet_paths = list(parquet_map.values())
    paths_glob = ", ".join(f"'{p}'" for p in parquet_paths)
    pg_con_str = get_duckdb_conn("pg")
    tmp_table = "stage.stg_oee_produto"

    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_con_str}' AS pg (TYPE POSTGRES);")

        size_mb = con.sql(
            "SELECT SUM(total_uncompressed_size) / (1024*1024.0) FROM parquet_metadata "
            f"([{paths_glob}])"
        ).fetchone() or (0,)

        log.info(f"[START] Carregando parquets ({size_mb[0]:.2f}MB)")

        con.execute(
            f"CREATE TEMP VIEW v_source AS SELECT * FROM read_parquet([{paths_glob}], "
            "union_by_name=true)"
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
    _get_sentinel("store_stage").unlink(missing_ok=True)


@dag(
    dag_id="STG_ELIPSE_OEE_PRODUTO",
    default_args=default_args,
    schedule="12 9 * * *",
    catchup=False,
    max_active_runs=1,
    concurrency=3,
    tags=["elipse", "stage", "oee"],
)
def dag_factory():
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    sob_data = extract_data.override(task_id="extract_data_sob")("sob")
    for_data = extract_data.override(task_id="extract_data_for")("for")
    cra_data = extract_data.override(task_id="extract_data_cra")("cra")

    concat = store_stage()

    clear = clear_cache()

    _ = start >> [sob_data, for_data, cra_data] >> concat >> clear >> end


dag_factory()
