"""Importacao manual de ganhos a partir de planilha Excel para mel_ganhos.

Excecao do pipeline das melhorias: quando a FAP tem linhas demais para a lista do
SharePoint, ela e aberta so com o minimo para ser aprovada e os ganhos chegam via
planilha. Esta DAG valida a planilha e insere as linhas em mel_ganhos com
insert_manual = 1.

Disparo: pagina "Melhorias > Importar ganhos (planilha)" (plugin
melhorias_ganhos_upload), que salva o arquivo em UPLOAD_DIR e dispara a DAG com o
caminho no conf. Tambem pode ser disparada pelo form de trigger com um arquivo que
ja esteja em UPLOAD_DIR.
"""

import os
from datetime import datetime
from pathlib import Path

import duckdb
from airflow import Dataset
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import get_current_context
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import DEFAULT_EXECUTION_TIMEOUT
from global_modules.database import exec_query_eng_db, get_duckdb_conn, get_eng_conn
from global_modules.ms_teams import notify_teams_on_failure
from global_modules.utils import read_sql_file
from melhorias.dags.MANUAL_MELHORIAS_GANHOS_PLANILHA.spreadsheet import (
    parse_fap_list,
    read_spreadsheet,
)
from sqlalchemy import text

log = LoggingMixin().log

# Mesmo Dataset do BRONZE_MELHORIA_GANHOS: dispara SILVER_MELHORIAS_DATA_FAP (sincroniza
# dt_fap com mel_aprovacao) e, em cascata, o dbt.
MEL_GANHOS_DATASET = Dataset("melhorias://bronze/melhoria_ganhos")

# Volume compartilhado entre webserver (upload) e worker (leitura). Manter igual ao plugin.
UPLOAD_DIR = Path(os.getenv("MELHORIAS_UPLOAD_DIR", "/opt/airflow/uploads/melhorias_ganhos"))

STAGING_TABLE = "dbo.stg_mel_ganhos_manual"

STAGING_PROJECTION = """
SELECT
    CAST(linha AS INTEGER) AS linha,
    CAST(tipo_melhoria AS VARCHAR(255)) AS tipo_melhoria,
    CAST(filial AS VARCHAR(255)) AS filial,
    CAST(setor AS VARCHAR(255)) AS setor,
    CAST(nome_solicitante AS VARCHAR(255)) AS nome_solicitante,
    CAST(numero_fap AS VARCHAR(30)) AS numero_fap,
    CAST(dt_fap AS DATE) AS dt_fap,
    CAST(cod_prod AS VARCHAR(50)) AS cod_prod,
    CAST(preco_mp AS DECIMAL(18, 2)) AS preco_mp,
    CAST(consumo_anterior AS DOUBLE) AS consumo_anterior,
    CAST(consumo_atual AS DOUBLE) AS consumo_atual,
    CAST(padrao_anterior AS DOUBLE) AS padrao_anterior,
    CAST(padrao_atual AS DOUBLE) AS padrao_atual,
    CAST(efetivo_anterior AS DOUBLE) AS efetivo_anterior,
    CAST(efetivo_atual AS DOUBLE) AS efetivo_atual,
    CAST(tc_anterior AS DOUBLE) AS tc_anterior,
    CAST(tc_atual AS DOUBLE) AS tc_atual,
    CAST(mix AS DOUBLE) AS mix,
    CAST(volume_mes_1 AS DOUBLE) AS volume_mes_1,
    CAST(volume_mes_2 AS DOUBLE) AS volume_mes_2,
    CAST(volume_mes_3 AS DOUBLE) AS volume_mes_3,
    CAST(volume_mes_4 AS DOUBLE) AS volume_mes_4,
    CAST(percentual_ganho AS DOUBLE) AS percentual_ganho,
    CAST(custo_par_anterior AS DOUBLE) AS custo_par_anterior,
    CAST(custo_par_atual AS DOUBLE) AS custo_par_atual
FROM planilha
"""


def _resolve_upload(file_path: str) -> Path:
    """Aceita so arquivos dentro de UPLOAD_DIR (o conf vem do usuario)."""
    if not file_path:
        raise ValueError("Parametro 'file_path' vazio.")
    path = Path(file_path)
    resolved = (path if path.is_absolute() else UPLOAD_DIR / path).resolve()
    if not resolved.is_relative_to(UPLOAD_DIR.resolve()):
        raise ValueError(f"'file_path' deve estar dentro de {UPLOAD_DIR}: {file_path}")
    return resolved


@task
def load_spreadsheet() -> dict:
    params = get_current_context()["params"]
    path = _resolve_upload(params.get("file_path") or "")
    faps = parse_fap_list(params.get("numero_faps"))

    log.info(
        "[START] Lendo planilha %s (aba=%r, faps=%s)",
        path.name,
        params.get("sheet_name"),
        faps or "<todas>",
    )
    data = read_spreadsheet(path, params.get("sheet_name") or None, faps)
    rows = data.rows

    log.info(
        "[INFO] Aba '%s': %d linha(s), %d FAP(s). Linhas vazias descartadas: %d",
        data.sheet_name,
        len(rows),
        rows["numero_fap"].nunique(),
        data.empty_rows_dropped,
    )

    conn_str = get_duckdb_conn("dbengenharia")
    with duckdb.connect() as con:
        con.execute("INSTALL mssql FROM community;")
        con.execute("LOAD mssql;")
        con.execute(f"ATTACH '{conn_str}' AS db (TYPE mssql);")
        con.register("planilha", rows)
        con.execute(
            f"COPY ({STAGING_PROJECTION}) TO 'db.{STAGING_TABLE}' (FORMAT 'bcp', REPLACE true);"
        )

    log.info("[DONE] %d linha(s) gravadas em %s", len(rows), STAGING_TABLE)
    return {"sheet_name": data.sheet_name, "rows": len(rows)}


@task
def validate_faps() -> list[dict]:
    with get_eng_conn().connect() as conn:
        result = conn.execute(text(read_sql_file("validate_faps.sql", __file__)))
        summary = [dict(row._mapping) for row in result]

    errors = []
    for item in summary:
        fap = item["Numero_fap"]
        a_inserir = item["Linhas_planilha"] - item["Linhas_sobrepostas"]
        log.info(
            "[FAP %s] aprovacoes=%d | linhas SharePoint=%d | manuais atuais=%d | "
            "planilha=%d | ja no SharePoint (ignoradas)=%d | a inserir=%d",
            fap,
            item["Aprovacoes"],
            item["Linhas_base"],
            item["Linhas_manuais_atuais"],
            item["Linhas_planilha"],
            item["Linhas_sobrepostas"],
            a_inserir,
        )
        if item["Aprovacoes"] == 0:
            errors.append(f"FAP {fap}: sem linha 'Aprovado' em mel_aprovacao")
        if item["Linhas_base"] == 0:
            errors.append(f"FAP {fap}: sem linha do SharePoint em mel_ganhos para servir de base")
        if a_inserir == 0:
            log.warning("[WARN] FAP %s: todas as linhas ja existem no SharePoint", fap)
        for campo in ("Tipo_melhoria", "Filial", "Setor"):
            planilha, base = item[f"{campo}_planilha"], item[f"{campo}_base"]
            if base is not None and planilha != base:
                log.warning(
                    "[WARN] FAP %s: %s da planilha (%r) diferente do SharePoint (%r). "
                    "Vale o do SharePoint.",
                    fap,
                    campo.lower(),
                    planilha,
                    base,
                )

    if errors:
        raise ValueError("Validacao falhou, nada foi inserido:\n" + "\n".join(errors))

    log.info("[DONE] %d FAP(s) validadas", len(summary))
    return summary


@task.short_circuit
def is_not_dry_run() -> bool:
    dry_run = bool(get_current_context()["params"].get("dry_run", True))
    if dry_run:
        log.info("[DRY-RUN] Validacao concluida; nada sera inserido em mel_ganhos.")
    return not dry_run


@task(outlets=[MEL_GANHOS_DATASET])
def insert_ganhos() -> None:
    log.info("[START] Inserindo linhas manuais em mel_ganhos")
    exec_query_eng_db(read_sql_file("insert_ganhos_manual.sql", __file__))
    log.info("[DONE] Insert manual concluido")


@task
def remove_upload() -> None:
    path = _resolve_upload(get_current_context()["params"].get("file_path") or "")
    path.unlink(missing_ok=True)
    log.info("[CLEANUP] Planilha removida: %s", path.name)


default_args = {
    "owner": "Antonio Albuquerque",
    "start_date": datetime(2026, 9, 1),
    "on_failure_callback": notify_teams_on_failure,
    "retries": 0,  # operacao manual; erro de validacao nao se resolve com retry
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
}


@dag(
    dag_id="MANUAL_MELHORIAS_GANHOS_PLANILHA",
    default_args=default_args,
    schedule=None,  # disparo manual (pagina de upload ou trigger com conf)
    catchup=False,
    max_active_runs=1,  # stg_mel_ganhos_manual e compartilhado entre runs
    tags=["melhorias", "bronze", "manual"],
    doc_md=__doc__,
    params={
        "file_path": Param(
            "",
            type="string",
            minLength=1,
            description=f"Planilha .xlsx em {UPLOAD_DIR} (preenchido pela pagina de upload).",
        ),
        "sheet_name": Param(
            "",
            type="string",
            minLength=1,
            description="Aba da planilha (ex.: BASE_LANCAMENTO-f).",
        ),
        "numero_faps": Param(
            "",
            type="string",
            description="FAPs a importar, separadas por virgula. Vazio = todas as FAPs da aba.",
        ),
        "dry_run": Param(
            True,
            type="boolean",
            description="True = so valida e mostra o resumo no log. False = insere em mel_ganhos.",
        ),
    },
)
def dag_factory():
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    _ = (
        start
        >> load_spreadsheet()
        >> validate_faps()
        >> is_not_dry_run()
        >> insert_ganhos()
        >> remove_upload()
        >> end
    )


dag_factory()
