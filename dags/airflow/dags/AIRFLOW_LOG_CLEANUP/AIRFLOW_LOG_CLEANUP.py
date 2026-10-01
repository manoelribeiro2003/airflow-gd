import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.configuration import conf
from airflow.decorators import dag, task
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args

log = LoggingMixin().log

RETENTION_DAYS = 7

# Volume compartilhado das planilhas enviadas pela UI (plugins/). A DAG consumidora
# apaga o arquivo ao terminar com sucesso; aqui sobram so os de runs que falharam.
UPLOADS_FOLDER = Path("/opt/airflow/uploads")

default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2026, 4, 1))


def _get_base_log_folder() -> Path:
    return Path(conf.get("logging", "base_log_folder"))


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _is_old(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime < cutoff


@task
def clean_dag_logs():
    base_log_folder = _get_base_log_folder()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=RETENTION_DAYS)

    deleted_dirs = 0
    freed_bytes = 0

    for dag_dir in base_log_folder.glob("dag_id=*"):
        if not dag_dir.is_dir():
            continue
        for run_dir in dag_dir.glob("run_id=*"):
            if not run_dir.is_dir():
                continue
            if _is_old(run_dir, cutoff):
                freed_bytes += _dir_size(run_dir)
                shutil.rmtree(run_dir)
                deleted_dirs += 1
                log.info(f"[DEL] {run_dir.name}")
        if dag_dir.exists() and not any(dag_dir.iterdir()):
            dag_dir.rmdir()

    log.info(
        f"[DONE] Logs de DAGs: removidos {deleted_dirs} diretórios, "
        f"liberados {freed_bytes / (1024**2):.2f} MB"
    )


@task
def clean_scheduler_logs():
    scheduler_dir = _get_base_log_folder() / "scheduler"
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=RETENTION_DAYS)

    if not scheduler_dir.exists():
        log.info("[SKIP] Diretório do scheduler não encontrado")
        return

    deleted_dirs = 0
    freed_bytes = 0

    for date_dir in scheduler_dir.iterdir():
        if not date_dir.is_dir():
            continue
        if _is_old(date_dir, cutoff):
            freed_bytes += _dir_size(date_dir)
            shutil.rmtree(date_dir)
            deleted_dirs += 1
            log.info(f"[DEL] scheduler/{date_dir.name}")

    log.info(
        f"[DONE] Logs do scheduler: removidos {deleted_dirs} diretórios, "
        f"liberados {freed_bytes / (1024**2):.2f} MB"
    )


@task
def clean_uploads():
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=RETENTION_DAYS)

    if not UPLOADS_FOLDER.exists():
        log.info("[SKIP] Diretório de uploads não encontrado")
        return

    deleted_files = 0
    freed_bytes = 0

    # So arquivos: os subdiretorios sao criados pelo plugin e ficam no lugar.
    for file in UPLOADS_FOLDER.rglob("*"):
        if not file.is_file():
            continue
        if _is_old(file, cutoff):
            freed_bytes += file.stat().st_size
            file.unlink(missing_ok=True)
            deleted_files += 1
            log.info(f"[DEL] uploads/{file.relative_to(UPLOADS_FOLDER)}")

    log.info(
        f"[DONE] Uploads: removidos {deleted_files} arquivos, "
        f"liberados {freed_bytes / (1024**2):.2f} MB"
    )


@dag(
    dag_id="AIRFLOW_LOG_CLEANUP",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["maintenance"],
)
def dag_factory():
    _ = clean_dag_logs() >> clean_scheduler_logs() >> clean_uploads()


dag_factory()
