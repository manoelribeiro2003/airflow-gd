from sqlalchemy import types as sa_types

# Schema do .parquet de volumes exportado pelo Qlik SaaS. As keys são as colunas do
# parquet; os values controlam o CAST explícito no DuckDB (build_select_with_cast).
# reporte_data vem como timestamp no parquet -> CAST para DATE (granularidade diária).
VOLUME_FIELDS: dict[str, sa_types.TypeEngine] = {
    "local_producao_cod": sa_types.VARCHAR(20),
    "produto_cod": sa_types.VARCHAR(16),
    "produto_cod_com_grade": sa_types.VARCHAR(30),
    "centro_custo_codtc": sa_types.VARCHAR(20),
    "reporte_data": sa_types.Date(),
    "Mes": sa_types.Integer(),
    "Ano": sa_types.Integer(),
    "mesch": sa_types.VARCHAR(10),
    "volume_producao": sa_types.FLOAT(2),
}
