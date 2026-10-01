from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb as ddb
from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.database import get_cx_conn, get_duckdb_conn
from global_modules.pg_load import pg_transaction
from global_modules.utils import read_sql_file

log = LoggingMixin().log

default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 7, 0))

# Fonte (workflow_logs) e destino (ferramental.fl_nota_fiscal) sao bancos Postgres
# DIFERENTES; a transferencia passa pelo cliente via DuckDB em streaming.
SRC_ATTACH = get_cx_conn("flakeflow")  # URI postgres, aceita pelo ATTACH do DuckDB
DST_ATTACH = get_duckdb_conn("pg_flakeflow")

DEST_TABLE = "ferramental.fl_nota_fiscal"
BACKFILL_START = "2025-11-04"
DUCKDB_MEMORY_LIMIT = "3GB"
DUCKDB_THREADS = 4

FOLDER = Path(__file__).parent


def _parquet_file(label: str) -> Path:
    return FOLDER / f"extract_data_{label}.parquet"


def _sentinel(name: str) -> Path:
    return FOLDER / f"{name}.finished"


def _new_duckdb() -> ddb.DuckDBPyConnection:
    con = ddb.connect()
    con.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"SET threads={DUCKDB_THREADS}")
    con.execute("SET preserve_insertion_order=false")
    return con


def _sql_literal(text: str) -> str:
    """Escapa aspas simples para embutir SQL dentro de string SQL do DuckDB."""
    return text.replace("'", "''")


def _month_windows(start_str: str, end: date) -> list[dict]:
    """Gera janelas mensais [lower, upper) de `start_str` ate hoje."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    windows: list[dict] = []
    cur = start
    while cur <= end:
        # primeiro dia do mes seguinte, sem depender do numero do mes
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        windows.append({
            "mode": "backfill",
            "label": cur.strftime("%Y_%m"),
            "lower": cur.isoformat(),
            "upper": nxt.isoformat(),
        })
        cur = nxt
    return windows


# Fonte grava atualizado_em/criado_em como timestamptz; o destino guarda o valor
# ja convertido para o horario local (America/Fortaleza, naive). O watermark lido
# do destino e, portanto, local-naive. Comparar direto contra a coluna timestamptz
# faria o Postgres interpretar o literal no fuso da sessao (UTC), deslocando a
# janela em 3h e reprocessando batches a cada run. Converter a coluna da fonte
# para o mesmo fuso local antes de comparar mantem a comparacao consistente.
SOURCE_TZ = "America/Fortaleza"


def _window_clause(window: dict) -> str:
    if window["mode"] == "incremental":
        return f"AND (wl.atualizado_em AT TIME ZONE '{SOURCE_TZ}') > '{window['watermark']}'"
    return (
        f"AND (wl.criado_em AT TIME ZONE '{SOURCE_TZ}') >= '{window['lower']}' "
        f"AND (wl.criado_em AT TIME ZONE '{SOURCE_TZ}') < '{window['upper']}'"
    )


def _build_extract_sql(window: dict) -> str:
    base = read_sql_file("fl_nota_fiscal.sql", __file__)
    return base.replace("-- __WINDOW__", _window_clause(window))


@task(retries=2, retry_delay=timedelta(minutes=1))
def ensure_table():
    create_sql = read_sql_file("create_table.sql", __file__)
    with _new_duckdb() as con:
        con.execute(f"ATTACH '{DST_ATTACH}' AS pg (TYPE POSTGRES)")
        con.execute(f"CALL postgres_execute('pg', '{_sql_literal(create_sql)}')")
    log.info(f"[OK] {DEST_TABLE} garantida/migrada")


@task
def resolve_mode() -> list[dict]:
    """Vazio no destino -> backfill (janelas mensais). Caso contrario ->
    incremental (uma janela por atualizado_em > watermark)."""
    with _new_duckdb() as con:
        con.execute(f"ATTACH '{DST_ATTACH}' AS pg (TYPE POSTGRES, READ_ONLY)")
        row = con.execute(f"SELECT max(atualizado_em) FROM pg.{DEST_TABLE}").fetchone()

    watermark = row[0] if row else None

    if watermark is None:
        windows = _month_windows(BACKFILL_START, date.today())
        log.info(f"[MODE] backfill — {len(windows)} janela(s) mensal(is)")
        return windows

    window = {
        "mode": "incremental",
        "label": "incremental",
        "watermark": watermark.isoformat(sep=" "),
    }
    log.info(f"[MODE] incremental — atualizado_em > {window['watermark']}")
    return [window]


# max_active_tis_per_dag=1: serializa as janelas mensais. Paralelizar abriria
# varios DuckDB (memory_limit alto) no mesmo worker e marteleria o servidor fonte.
@task(
    retries=3,
    retry_delay=timedelta(minutes=2),
    execution_timeout=timedelta(hours=1),
    max_active_tis_per_dag=1,
)
def extract_window(window: dict):
    label = window["label"]
    parquet_file = _parquet_file(label)
    sentinel = _sentinel(f"extract_{label}")

    if sentinel.exists():
        log.info(f"[SKIP] extracao da janela {label} ja processada")
        return

    log.info(f"[START] extraindo janela {label} ({window['mode']})")

    extract_sql = _build_extract_sql(window)
    temp_file = parquet_file.with_suffix(".tmp")

    with _new_duckdb() as con:
        con.execute(f"ATTACH '{SRC_ATTACH}' AS srcpg (TYPE POSTGRES, READ_ONLY)")
        con.execute(
            f"""
            COPY (
                SELECT * FROM postgres_query('srcpg', '{_sql_literal(extract_sql)}')
            ) TO '{temp_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        rows = con.execute(f"SELECT count(*) FROM read_parquet('{temp_file}')").fetchone() or (0,)

    temp_file.rename(parquet_file)
    sentinel.touch()
    log.info(f"[DONE] janela {label} — {rows[0]} linhas gravadas")


STAGING_TABLE = "ferramental._fl_nf_stg"
LOAD_COLS = (
    "sku, numero_fl, numero_nf, data_movimento, acao, num_lote, criado_em, atualizado_em, log_id"
)


@task(retries=2, retry_delay=timedelta(minutes=1))
def load_table(windows: list[dict]):
    """UPSERT por sku. Dedup global sobre os parquets (mais recente por sku),
    grava numa staging no PG e promove para o alvo com ON CONFLICT (sku) e guarda
    de recencia (nao regride atualizado_em/data_movimento). Backfill e incremental
    seguem o mesmo caminho: no alvo vazio, todo upsert vira INSERT."""
    sentinel = _sentinel("load_table")
    if sentinel.exists():
        log.info("[SKIP] load_table ja concluido")
        return

    mode = windows[0]["mode"]
    files = [str(_parquet_file(w["label"])) for w in windows if _parquet_file(w["label"]).exists()]

    if not files:
        log.info("[SKIP] nenhum parquet para carregar")
        sentinel.touch()
        return

    files_list = "[" + ", ".join(f"'{f}'" for f in files) + "]"

    create_stg = (
        f"CREATE UNLOGGED TABLE IF NOT EXISTS {STAGING_TABLE} ("
        "sku text, numero_fl text, numero_nf text, data_movimento date, "
        "acao text, num_lote text, "
        "criado_em timestamp, atualizado_em timestamp, log_id uuid)"
    )

    # dedup global por sku: entre janelas diferentes o mesmo sku pode aparecer.
    dedup_select = (
        f"SELECT {LOAD_COLS} FROM read_parquet({files_list}) "
        "QUALIFY row_number() OVER ("
        "PARTITION BY sku ORDER BY atualizado_em DESC, data_movimento DESC) = 1"
    )

    upsert_sql = (
        f"INSERT INTO {DEST_TABLE} AS t ({LOAD_COLS}) "
        f"SELECT {LOAD_COLS} FROM {STAGING_TABLE} "
        "ON CONFLICT (sku) DO UPDATE SET "
        "numero_fl = EXCLUDED.numero_fl, numero_nf = EXCLUDED.numero_nf, "
        "data_movimento = EXCLUDED.data_movimento, criado_em = EXCLUDED.criado_em, "
        "acao = EXCLUDED.acao, num_lote = EXCLUDED.num_lote, "
        "atualizado_em = EXCLUDED.atualizado_em, log_id = EXCLUDED.log_id, "
        "loaded_at = current_timestamp "
        "WHERE EXCLUDED.atualizado_em > t.atualizado_em "
        "OR (EXCLUDED.atualizado_em = t.atualizado_em "
        "AND EXCLUDED.data_movimento > t.data_movimento)"
    )

    with _new_duckdb() as con:
        con.execute(f"ATTACH '{DST_ATTACH}' AS pg (TYPE POSTGRES)")
        con.execute(f"CALL postgres_execute('pg', '{_sql_literal(create_stg)}')")
        # staging + upsert numa transacao so: falha no meio nao deixa staging
        # parcial nem upsert pela metade; retry repete tudo.
        with pg_transaction(con):
            con.execute(f"CALL postgres_execute('pg', 'TRUNCATE TABLE {STAGING_TABLE}')")
            con.execute(f"INSERT INTO pg.{STAGING_TABLE} ({LOAD_COLS}) {dedup_select}")
            staged = con.execute(f"SELECT count(*) FROM pg.{STAGING_TABLE}").fetchone() or (0,)
            con.execute(f"CALL postgres_execute('pg', '{_sql_literal(upsert_sql)}')")

    sentinel.touch()
    log.info(f"[DONE] {DEST_TABLE} ({mode}) — {staged[0]} sku(s) na staging, upsert aplicado")


@task
def clear_cache():
    log.info("[CLEANUP] limpando parquets e sentinelas")
    for f in FOLDER.glob("extract_data_*.parquet"):
        f.unlink(missing_ok=True)
    for f in FOLDER.glob("*.finished"):
        f.unlink(missing_ok=True)


@dag(
    dag_id="BRONZE_F_FL_NOTA_FISCAL",
    default_args=default_args,
    schedule="0 7 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["flakeflow", "nota_fiscal", "ferramental", "bronze"],
)
def dag_factory():
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    ensure = ensure_table()
    windows = resolve_mode()
    extract = extract_window.expand(window=windows)
    load = load_table(windows)
    clear = clear_cache()

    _ = start >> ensure >> windows
    _ = extract >> load >> clear >> end


dag_factory()
