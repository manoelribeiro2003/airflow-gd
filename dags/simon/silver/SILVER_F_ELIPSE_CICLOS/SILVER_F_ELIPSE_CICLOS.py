from datetime import datetime, timedelta
from pathlib import Path

import connectorx as cx
import duckdb as ddb
from airflow.decorators import dag, task
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import (
    Estabelecimento,
    get_ciclos_search_window,
    get_cx_conn,
    get_duckdb_conn,
    get_estab_code,
)
from global_modules.partitions import monthly_partition_bounds
from global_modules.pg_load import replace_pg_table
from global_modules.utils import get_parquet_file, get_sentinel_file, read_sql_file

log = LoggingMixin().log

STAGE_TABLE = "stage.stage_ciclos"

default_args = default_dag_args(owner="yan arcanjo", start_date=datetime(2025, 1, 26, 6, 5))


def _get_parquet_map() -> dict[Estabelecimento, Path]:
    return {
        "sob": get_parquet_file("sob", __file__),
        "for": get_parquet_file("for", __file__),
        "cra": get_parquet_file("cra", __file__),
    }


def _get_merged_parquet() -> Path:
    return get_parquet_file("merged", __file__)


def _get_sentinel(name: str) -> Path:
    return get_sentinel_file(name, __file__)


def _equipment_id(table_name: str) -> str:
    return table_name[6:]  # "Ciclo 123" → "123"


def _max_ts_by_equipment(df, ts_column: str) -> dict[str, datetime]:
    return {
        str(equip): ts
        for equip, ts in zip(df["id_equipamento"].to_pylist(), df[ts_column].to_pylist())
        if ts is not None
    }


def _discover_tables(estab: Estabelecimento) -> list[str]:
    tables = cx.read_sql(
        get_cx_conn(estab),
        read_sql_file("discover_tables.sql", __file__),
        return_type="arrow",
    )
    return tables["TABLE_NAME"].to_pylist()


def _fetch_silver_max_by_equipment(estab_code) -> dict[str, datetime]:
    """Último registro por máquina em silver.oee_fciclos."""
    silver_df = cx.read_sql(
        get_cx_conn("pg"),
        read_sql_file("silver_max_por_maquina.sql", __file__).format(estab_code=estab_code),
        return_type="arrow",
    )
    return _max_ts_by_equipment(silver_df, "ultima_data_hora")


def _fetch_source_max_by_equipment(
    estab: Estabelecimento, table_names: list[str]
) -> dict[str, datetime]:
    """MAX(E3TimeStamp) no SQL Server para todas as tabelas em lote."""
    source_max_template = read_sql_file("source_max_por_maquina.sql", __file__)
    max_parts = [
        source_max_template.format(id_equipamento=_equipment_id(name), table_name=name)
        for name in table_names
    ]
    source_df = cx.read_sql(
        get_cx_conn(estab),
        "\nUNION ALL\n".join(max_parts),
        return_type="arrow",
    )
    return _max_ts_by_equipment(source_df, "max_ts")


def _tables_with_new_data(
    table_names: list[str],
    source_maxima: dict[str, datetime],
    silver_maxima: dict[str, datetime],
) -> list[str]:
    tables_with_new_data = []
    for name in table_names:
        id_equip = _equipment_id(name)
        source_max = source_maxima.get(id_equip)
        silver_max = silver_maxima.get(id_equip)

        if source_max is None:
            log.info(f"[SKIP] {name}: sem dados no SQL Server")
            continue

        if silver_max is None or source_max > silver_max:
            tables_with_new_data.append(name)
        else:
            log.info(f"[SKIP] {name}: sem novos ciclos (source={source_max}, silver={silver_max})")

    return tables_with_new_data


def _build_extract_queries(
    table_names: list[str], estab_code, dt_inicio: datetime, dt_fim: datetime
) -> list[str]:
    """UNION ALL das tabelas, dividido em até 8 queries para rodar em paralelo."""
    extract_template = read_sql_file("extract_ciclos.sql", __file__)

    parts = [
        extract_template.format(
            estab=estab_code,
            id_equipamento=_equipment_id(name),
            table_name=name,
            dt_inicio=dt_inicio.strftime("%Y-%m-%d %H:%M:%S"),
            dt_fim=dt_fim.strftime("%Y-%m-%d %H:%M:%S"),
        )
        for name in table_names
    ]

    n_threads = min(8, len(parts))
    chunk_size = -(-len(parts) // n_threads)  # ceiling division
    return [
        "\nUNION ALL\n".join(parts[i : i + chunk_size]) for i in range(0, len(parts), chunk_size)
    ]


def _write_parquet(df, parquet_file: Path) -> None:
    """Grava parquet ZSTD com write atômico."""
    temp_file = parquet_file.with_suffix(".tmp")

    with ddb.connect() as con:
        con.register("df", df)
        con.execute(f"COPY (SELECT * FROM df) TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    temp_file.rename(parquet_file)


# Janela vem da Variable SILVER_F_CICLOS_DAYS_TO_SEARCH e cresce em reprocessamento;
# timeout acima do padrão para não matar extrações longas legítimas.
@task(retries=3, retry_delay=timedelta(minutes=2), execution_timeout=timedelta(minutes=90))
def extract_data(estab: Estabelecimento):
    parquet_file = _get_parquet_map()[estab]

    if parquet_file.exists():
        log.info(f"[SKIP] {estab} já processado")
        return

    log.info(f"[START] Descobrindo tabelas Ciclo em {estab}")

    table_names = _discover_tables(estab)

    log.info(f"[INFO] {len(table_names)} tabelas encontradas em {estab}")

    if not table_names:
        log.warning(f"[WARN] Nenhuma tabela Ciclo encontrada em {estab}, abortando")
        return

    # Janela de dias (fallback para máquinas novas)
    dt_fim = datetime.now()
    dt_inicio = dt_fim - timedelta(days=get_ciclos_search_window())

    estab_code = get_estab_code(estab)

    silver_maxima = _fetch_silver_max_by_equipment(estab_code)

    log.info(f"[INFO] {len(silver_maxima)} máquinas com registros em silver para {estab}")

    tables_with_new_data = _tables_with_new_data(
        table_names, _fetch_source_max_by_equipment(estab, table_names), silver_maxima
    )

    if not tables_with_new_data:
        log.info(f"[SKIP] {estab}: nenhuma máquina com novos ciclos")
        return

    log.info(
        f"[INFO] {len(tables_with_new_data)}/{len(table_names)} "
        f"máquinas com novos ciclos em {estab}"
    )

    queries = _build_extract_queries(tables_with_new_data, estab_code, dt_inicio, dt_fim)

    log.info(
        f"[INFO] Executando {len(queries)} queries em paralelo "
        f"({len(tables_with_new_data)} tabelas)"
    )
    df = cx.read_sql(get_cx_conn(estab), queries, return_type="arrow")

    log.info(f"[DONE QUERY] {df.shape[0]} linhas, {(df.nbytes / (1024**2)):.2f}MB")

    _write_parquet(df, parquet_file)

    log.info(f"[DONE] {estab} -> parquet gravado")


@task
def merge_parquets():
    merged_file = _get_merged_parquet()

    if merged_file.exists():
        log.info(f"[SKIP] '{merged_file.name}' já processado")
        return

    parquet_paths = [p for p in _get_parquet_map().values() if p.exists()]

    if not parquet_paths:
        log.warning("[WARN] Nenhum parquet disponível para mesclar")
        return

    temp_file = merged_file.with_suffix(".tmp")
    paths_glob = ", ".join(f"'{p}'" for p in parquet_paths)

    with ddb.connect() as con:
        con.execute(
            f"COPY (SELECT * FROM read_parquet([{paths_glob}], union_by_name=true)) "
            f"TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )

    temp_file.rename(merged_file)
    log.info(f"[DONE] {len(parquet_paths)} parquets mesclados → {merged_file.name}")


@task(retries=2, retry_delay=timedelta(minutes=1))
def copy_to_stage():
    sentinel = _get_sentinel("copy_to_stage")

    if sentinel.exists():
        log.info("[SKIP] copy_to_stage já concluído")
        return

    merged_file = _get_merged_parquet()

    if not merged_file.exists():
        log.warning("[WARN] Parquet mesclado não encontrado, abortando")
        return

    pg_con_str = get_duckdb_conn("pg")

    # Limpa o stage na mesma transação da carga: se o worker morrer entre a carga
    # e a sentinela, o retry recria o mesmo stage em vez de duplicar as linhas.
    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_con_str}' AS pg (TYPE POSTGRES);")
        total_rows = replace_pg_table(
            con, STAGE_TABLE, f"SELECT * FROM read_parquet('{merged_file}')"
        )

    sentinel.touch()
    log.info(f"[DONE] Carga concluída → {STAGE_TABLE} — {total_rows} registros")


@task
def ensure_partition():
    # Sempre criar 1 partição a frente.
    start, end = monthly_partition_bounds(datetime.now() + timedelta(days=30))

    partition_name = f"oee_fciclos_{start:%Y_%m}"

    create_partition = (
        f"CREATE TABLE IF NOT EXISTS silver.{partition_name} "
        f"PARTITION OF silver.oee_fciclos "
        f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')"
    )

    create_index = (
        f"CREATE INDEX IF NOT EXISTS idx_brin_data_{start:%Y_%m} "
        f"ON silver.{partition_name} "
        f"USING BRIN (data_hora) "
        f"WITH (pages_per_range = 32)"
    )

    pg_con_str = get_duckdb_conn("pg")

    with ddb.connect() as con:
        con.execute(f"ATTACH '{pg_con_str}' AS pg (TYPE POSTGRES);")

        log.info(f"[INFO] Criando partição: \n {create_partition}")
        con.execute(f"CALL postgres_execute('pg', $${create_partition}$$)")
        log.info(f"[DONE] Partição silver.{partition_name}.")

        log.info(f"[INFO] Criando índice: \n {create_index}")
        con.execute(f"CALL postgres_execute('pg', $${create_index}$$)")
        log.info(f"[DONE] Índice BRIN idx_brin_data_{start:%Y_%m}.")


@task
def clear_cache():
    log.info("[CLEANUP] Limpando parquets e sentinelas.")

    for parquet in [*_get_parquet_map().values(), _get_merged_parquet()]:
        parquet.unlink(missing_ok=True)

    _get_sentinel("copy_to_stage").unlink(missing_ok=True)


@dag(
    dag_id="SILVER_F_CICLOS_SIMON",
    default_args=default_args,
    schedule="30 9,18 * * *",
    catchup=False,
    max_active_runs=1,
    concurrency=3,
    tags=["elipse", "ciclos", "silver"],
)
def dag_factory():
    sob_data = extract_data.override(task_id="extract_data_sob")("sob")
    for_data = extract_data.override(task_id="extract_data_for")("for")
    cra_data = extract_data.override(task_id="extract_data_cra")("cra")

    merge_parquet = merge_parquets()
    copy = copy_to_stage()
    partition = ensure_partition()

    merge_table = SQLExecuteQueryOperator(
        task_id="merge_stage_to_silver",
        conn_id="postgres_eng_server",
        sql=read_sql_file("merge_query.sql", __file__),
        autocommit=True,
    )

    truncate = SQLExecuteQueryOperator(
        task_id="truncate_stage",
        conn_id="postgres_eng_server",
        sql=f"TRUNCATE TABLE {STAGE_TABLE};",
    )

    clear = clear_cache()

    _ = (
        [sob_data, for_data, cra_data]
        >> merge_parquet
        >> copy
        >> partition
        >> merge_table
        >> truncate
        >> clear
    )


dag_factory()
