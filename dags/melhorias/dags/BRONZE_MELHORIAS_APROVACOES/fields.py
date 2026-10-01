from global_modules.sharepoint.datetime_resolve import DatetimeConfig
from sqlalchemy import types as sa_types

LIST_FIELDS: dict[str, sa_types.TypeEngine] = {
    "id": sa_types.Integer(),
    "Title": sa_types.VARCHAR(255),
    "email_aprovador_eng": sa_types.VARCHAR(),
    "dt_aprovacao_eng": sa_types.DateTime(),
    "comentarios_especialista": sa_types.VARCHAR(),
    "email_aprovador_producao": sa_types.VARCHAR(),
    "dt_aprovacao_producao": sa_types.DateTime(),
    "comentarios_aprov_setor": sa_types.VARCHAR(255),
    "status": sa_types.VARCHAR(255),
    "nome_quem_aprovou_setor": sa_types.VARCHAR(255),
    "nome_quem_aprovou_especialista": sa_types.VARCHAR(255),
    # Normalizado p/ hora local BR (naive) por resolve_datetimes -> TIMESTAMP, não TIMESTAMPTZ.
    "Modified": sa_types.DateTime(),
    "status_aprov_setor": sa_types.VARCHAR(255),
    "status_aprov_especialista": sa_types.VARCHAR(255),
    "codigos_produto": sa_types.VARCHAR(),
    "dt_inicio_fluxo": sa_types.DateTime(),
    "status_aprov_analista": sa_types.VARCHAR(255),
    "nome_quem_aprovou_analista": sa_types.VARCHAR(255),
    "dt_aprovacao_analista": sa_types.DateTime(),
    "ID_x0020_do_x0020_anexo": sa_types.Integer(),
    "nome_especialista": sa_types.VARCHAR(255),
    "nome_aprovador_setor": sa_types.VARCHAR(255),
    "email_analistas": sa_types.VARCHAR(),
    "email_sup_engenharia": sa_types.VARCHAR(),
    "dt_fap": sa_types.DateTime(),
    "solicitante": sa_types.VARCHAR(255),
    "tipo_melhoria": sa_types.VARCHAR(255),
    "setor": sa_types.VARCHAR(255),
    "numero_fap_pai": sa_types.VARCHAR(255),
    "guid_anexos": sa_types.VARCHAR(255),
    "cracha_idealizador": sa_types.Integer(),
    "nome_idealizador": sa_types.VARCHAR(255),
    "cc_idealizador": sa_types.VARCHAR(255),
    "setor_idealizador": sa_types.VARCHAR(255),
    "gerente_idealizador": sa_types.VARCHAR(255),
    "cargo_idealizador": sa_types.VARCHAR(255),
    "tipo_fap": sa_types.VARCHAR(255),
    "dt_fap_informada_por": sa_types.DateTime(),
    "desc_melhoria": sa_types.VARCHAR(),
    "investimento": sa_types.Float(4),
    "custo_MOD": sa_types.Float(4),
    "desc_processo_atual": sa_types.VARCHAR(),
    "desc_processo_proposto": sa_types.VARCHAR(),
    "carga_horaria_mes": sa_types.Float(4),
    "gerente_melhoria": sa_types.VARCHAR(255),
    # Normalizado p/ hora local BR (naive) por resolve_datetimes -> TIMESTAMP, não TIMESTAMPTZ.
    "Created": sa_types.DateTime(),
    "comentarios_analista": sa_types.VARCHAR(),
    "CertificacaoImetro": sa_types.VARCHAR(255),
    "status_aprovador_inmetro": sa_types.VARCHAR(255),
    "dt_aprovacao_inmetro": sa_types.DateTime(),
    "comentario_aprovador_inmetro": sa_types.VARCHAR(),
    "nome_quem_aprovou_inmetro": sa_types.VARCHAR(255),
    "eh_ganho": sa_types.VARCHAR(255),
    "quem_aprovou_gerencia_eng": sa_types.VARCHAR(255),
    "status_aprovador_gerencia_eng": sa_types.VARCHAR(255),
    "comentarios_aprovador_gerencia_e": sa_types.VARCHAR(),
    "dt_aprovacao_gerencia_eng": sa_types.DateTime(),
    "tipo_produto": sa_types.VARCHAR(255),
    # Lookup / Person fields
    "fabrica_melhoria": sa_types.VARCHAR(255),
    "filial_melhoria": sa_types.VARCHAR(255),
    "origem_melhoria": sa_types.VARCHAR(255),
    "macro_setor": sa_types.VARCHAR(255),
    "tipo_alteracao": sa_types.VARCHAR(255),
    "Author": sa_types.VARCHAR(255),
    "Editor": sa_types.VARCHAR(255),
}

EXPAND_FIELDS = [
    "fabrica_melhoria",
    "filial_melhoria",
    "origem_melhoria",
    "macro_setor",
    "tipo_alteracao",
    "Author",
    "Editor",
]

# Configuração de datas para resolve_datetimes (ver datetime_resolve.py).
# O fuso é fixado por categoria; o formato (dd/MM vs MM/dd) é desambiguado pela âncora
# Created/Modified. Resultado final: todas as colunas em hora local BR (naive).

# Eventos preenchidos via convertFromUtc -> texto dd/MM em hora local BR.
DATETIME_EVENT_LOCAL_FIELDS = [
    "dt_aprovacao_eng",
    "dt_aprovacao_producao",
    "dt_inicio_fluxo",
    "dt_aprovacao_inmetro",
    "dt_aprovacao_gerencia_eng",
]

# Eventos vindos de powerautomate.approvals.responseDate -> sempre UTC.
DATETIME_EVENT_UTC_FIELDS = [
    "dt_aprovacao_analista",
]

# Campos de sistema do SharePoint -> ISO-UTC. São a âncora temporal.
DATETIME_SYSTEM_FIELDS = [
    "Created",
    "Modified",
]

# Datas preenchidas manualmente (sem âncora): assume dd/MM em hora local.
# dt_fap é sobrescrito depois pela SILVER_MELHORIAS_DATA_FAP a partir de dt_aprovacao_eng.
DATETIME_MANUAL_FIELDS = [
    "dt_fap",
    "dt_fap_informada_por",
]

DATETIME_CONFIG = DatetimeConfig(
    event_local_fields=DATETIME_EVENT_LOCAL_FIELDS,
    event_utc_fields=DATETIME_EVENT_UTC_FIELDS,
    system_fields=DATETIME_SYSTEM_FIELDS,
    manual_fields=DATETIME_MANUAL_FIELDS,
)
