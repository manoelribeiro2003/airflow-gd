from global_modules.sharepoint.datetime_resolve import DatetimeConfig
from sqlalchemy import types as sa_types

LIST_FIELDS: dict[str, sa_types.TypeEngine] = {
    "id": sa_types.Integer(),
    "tipo_melhoria": sa_types.VARCHAR(255),
    "filial": sa_types.VARCHAR(255),  # lookup field
    "fabrica": sa_types.VARCHAR(255),  # lookup field
    "setor": sa_types.VARCHAR(255),  # lookup field
    "nome_solicitante": sa_types.VARCHAR(255),
    # "Title": "numero_fap",
    "numero_fap2": sa_types.VARCHAR(30),
    "dt_fap": sa_types.DATE,
    "cod_prod": sa_types.Text(),
    "preco_mp": sa_types.DECIMAL(18, 2),
    "consumo_anterior": sa_types.FLOAT(7),
    "consumo_atual": sa_types.FLOAT(7),
    "padrao_anterior": sa_types.FLOAT(2),
    "padrao_atual": sa_types.FLOAT(2),
    "efetivo_anterior": sa_types.FLOAT(2),
    "efetivo_atual": sa_types.FLOAT(2),
    "tc_anterior": sa_types.FLOAT(4),
    "tc_atual": sa_types.FLOAT(4),
    "mix": sa_types.FLOAT(2),
    "volume_mes_1": sa_types.FLOAT(2),
    "volume_mes_2": sa_types.FLOAT(2),
    "volume_mes_3": sa_types.FLOAT(2),
    "volume_mes_4": sa_types.FLOAT(2),
    # "desc_melhoria": sa_types.VARCHAR(),
    "_x0025__ganho": sa_types.FLOAT(2),
    "custo_par_anterior": sa_types.FLOAT(2),
    "custo_par_atual": sa_types.FLOAT(2),
    "origem_melhoria": sa_types.VARCHAR(255),
    "macro_setor": sa_types.VARCHAR(255),  # lookup field
    "replicavel": sa_types.VARCHAR(255),
    "nome_setor_replicavel": sa_types.VARCHAR(255),
    # "supervisor_setor": "nome_especialista",
    # "nome_aprovador": "nome_aprovador_setor",
    "is_lacamento_manual": sa_types.Boolean(),
    "investimento": sa_types.DECIMAL(18, 2),
    "cracha_idealizador": sa_types.Integer(),
    "descricao_proc_atual_outras_m": sa_types.Text(),
    "descricao_proc_prop_outras_m": sa_types.Text(),
    "qtde_mo_atual_outras_m": sa_types.FLOAT(2),
    "qtde_mo_proposto_outras_m": sa_types.FLOAT(2),
    "dt_fap_informada_por": sa_types.DateTime(),
    "salario_MOD": sa_types.DECIMAL(18, 2),
    "carga_horaria_mes": sa_types.DECIMAL(18, 2),
    "peso_ponderado_componente": sa_types.FLOAT(6),
    "ganho_previsto": sa_types.DECIMAL(18, 2),
    "tipo_alteracao": sa_types.VARCHAR(50),  # lookup field
    "id_solicitacao_assinatura": sa_types.INTEGER(),
    "gerente": sa_types.VARCHAR(255),
    "tipo_fap": sa_types.VARCHAR(255),
    "nome_idealizador": sa_types.VARCHAR(255),
    "cc_idealizador": sa_types.VARCHAR(255),
    "Gerente_x0020_Idealizador": sa_types.VARCHAR(255),
    "Created": sa_types.DateTime(),
    # Normalizado p/ hora local BR (naive) por resolve_datetimes -> TIMESTAMP, não TIMESTAMPTZ.
    "Modified": sa_types.DateTime(),
    "_x00c9__x0020_uma_x0020_replica_": sa_types.VARCHAR(255),
    "volume_x0020_foi_x0020_editado": sa_types.Boolean(),
    "Cargo": sa_types.VARCHAR(255),
    "Status_x0020_de_x0020_libera_x00": sa_types.VARCHAR(255),
    "tipo_produto": sa_types.VARCHAR(255),
    "Author": sa_types.VARCHAR(255),
    "Editor": sa_types.VARCHAR(255),
}

# Esta lista só tem Created/Modified (campos de sistema, ISO-UTC -> hora local BR naive).
# dt_fap deriva de dt_aprovacao_eng (SILVER) e dt_fap_informada_por é tratado pelo
# parse_by_schema (dayfirst=True), então não precisam de resolução ancorada aqui.
DATETIME_SYSTEM_FIELDS = [
    "Created",
    "Modified",
]

DATETIME_CONFIG = DatetimeConfig(system_fields=DATETIME_SYSTEM_FIELDS)
