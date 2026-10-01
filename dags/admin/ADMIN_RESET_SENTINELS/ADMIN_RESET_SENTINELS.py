import logging
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
from global_modules.dag_defaults import DEFAULT_EXECUTION_TIMEOUT
from global_modules.ms_teams import notify_teams_on_failure

log = logging.getLogger(__name__)

# raiz dos DAGs: .../dags/admin/ADMIN_RESET_SENTINELS/file.py -> parents[2] = /opt/airflow/dags
DAGS_ROOT = Path(__file__).resolve().parents[2]

default_args = {
    "on_failure_callback": notify_teams_on_failure,
    "retries": 0,  # operacao manual; nao faz sentido retry automatico
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
}


@task
def reset_cache():
    ctx = get_current_context()
    params = ctx["params"]
    target: str = (params.get("target") or "").strip()
    dry_run: bool = bool(params.get("dry_run", True))
    include_parquet: bool = bool(params.get("include_parquet", True))

    patterns = ["*.finished"] + (["*.parquet"] if include_parquet else [])
    candidates = sorted(f for pat in patterns for f in DAGS_ROOT.rglob(pat))

    # filtro por substring no caminho relativo (vazio = todas)
    if target:
        candidates = [f for f in candidates if target in str(f.relative_to(DAGS_ROOT))]

    if not candidates:
        log.info(
            "[RESET] Nenhum arquivo de cache encontrado (target=%r).",
            target or "<todas>",
        )
        return

    mode = "DRY-RUN (nada apagado)" if dry_run else "APAGANDO"
    log.warning(
        "[RESET] %s | target=%r | %d arquivo(s). Garanta que nenhuma DAG alvo esteja em execucao.",
        mode,
        target or "<todas>",
        len(candidates),
    )
    for f in candidates:
        rel = f.relative_to(DAGS_ROOT)
        if dry_run:
            log.info("[RESET][dry-run] apagaria: %s", rel)
        else:
            f.unlink(missing_ok=True)
            log.info("[RESET] apagado: %s", rel)


@dag(
    dag_id="ADMIN_RESET_SENTINELS",
    default_args=default_args,
    schedule=None,  # disparo manual apenas
    catchup=False,
    max_active_runs=1,
    tags=["admin", "cache", "manual"],
    params={
        "target": Param(
            "",
            type="string",
            description="Substring do caminho relativo da DAG (ex: 'CICLOS'). Vazio = todas.",
        ),
        "dry_run": Param(
            True,
            type="boolean",
            description="True = apenas lista no log. False = apaga de fato.",
        ),
        "include_parquet": Param(
            True,
            type="boolean",
            description="Tambem remover parquets de cache (*.parquet) orfaos.",
        ),
    },
)
def dag_factory():
    reset_cache()


dag_factory()
