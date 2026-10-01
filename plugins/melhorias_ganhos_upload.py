"""Pagina de upload da planilha de ganhos das melhorias.

Menu "Melhorias > Importar ganhos (planilha)": recebe o .xlsx, salva em UPLOAD_DIR
(volume compartilhado com o worker) e dispara MANUAL_MELHORIAS_GANHOS_PLANILHA com o
caminho do arquivo no conf. Toda a validacao e o insert ficam na DAG.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from airflow.api.common.trigger_dag import trigger_dag
from airflow.auth.managers.models.resource_details import DagAccessEntity, DagDetails
from airflow.models.dag import DagModel
from airflow.plugins_manager import AirflowPlugin
from airflow.www.extensions.init_auth_manager import get_auth_manager
from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_appbuilder import BaseView, expose
from werkzeug.utils import secure_filename

DAG_ID = "MANUAL_MELHORIAS_GANHOS_PLANILHA"

# Manter igual ao UPLOAD_DIR da DAG.
UPLOAD_DIR = Path(os.getenv("MELHORIAS_UPLOAD_DIR", "/opt/airflow/uploads/melhorias_ganhos"))

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}


def _ensure_can_trigger() -> None:
    # Mesma permissao do botao "Trigger DAG" da UI.
    allowed = get_auth_manager().is_authorized_dag(
        method="POST",
        access_entity=DagAccessEntity.RUN,
        details=DagDetails(id=DAG_ID),
    )
    if not allowed:
        abort(403)


class MelhoriasGanhosUploadView(BaseView):
    route_base = "/melhorias_ganhos_upload"
    default_view = "index"

    @expose("/", methods=["GET"])
    def index(self):
        _ensure_can_trigger()
        return self.render_template(
            "melhorias_ganhos_upload/upload.html",
            dag_id=DAG_ID,
            allowed_extensions=", ".join(sorted(ALLOWED_EXTENSIONS)),
        )

    @expose("/", methods=["POST"])
    def upload(self):  # noqa: PLR6301 - FAB exige metodo de instancia
        _ensure_can_trigger()

        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            flash("Selecione a planilha.", "error")
            return redirect(url_for(".index"))

        sheet_name = request.form.get("sheet_name", "").strip()
        if not sheet_name:
            flash("Informe a aba da planilha.", "error")
            return redirect(url_for(".index"))

        filename = secure_filename(uploaded.filename)
        if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            flash(f"Formato nao suportado. Use {', '.join(sorted(ALLOWED_EXTENSIONS))}.", "error")
            return redirect(url_for(".index"))

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        target = UPLOAD_DIR / f"{stamp}_{filename}"
        uploaded.save(target)

        conf = {
            "file_path": str(target),
            "sheet_name": sheet_name,
            "numero_faps": request.form.get("numero_faps", "").strip(),
            "dry_run": request.form.get("dry_run") == "on",
        }
        run_id = f"manual_upload__{stamp}"
        try:
            trigger_dag(dag_id=DAG_ID, run_id=run_id, conf=conf)
        except Exception as exc:  # noqa: BLE001 - mostrar o motivo na tela
            target.unlink(missing_ok=True)
            flash(f"Falha ao disparar a DAG: {exc}", "error")
            return redirect(url_for(".index"))

        mode = "validacao (dry-run)" if conf["dry_run"] else "importacao"
        flash(f"Planilha '{filename}' enviada. Run '{run_id}' de {mode} disparado.", "info")
        dag_model = DagModel.get_current(DAG_ID)
        if dag_model is not None and dag_model.is_paused:
            flash(f"A DAG {DAG_ID} esta pausada: o run so executa depois de despausar.", "warning")

        return redirect(url_for("Airflow.grid", dag_id=DAG_ID, dag_run_id=run_id))


blueprint = Blueprint(
    "melhorias_ganhos_upload",
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
)


class MelhoriasGanhosUploadPlugin(AirflowPlugin):
    name = "melhorias_ganhos_upload"
    flask_blueprints = [blueprint]
    appbuilder_views = [
        {
            "name": "Importar ganhos (planilha)",
            "category": "Melhorias",
            "view": MelhoriasGanhosUploadView(),
        }
    ]
