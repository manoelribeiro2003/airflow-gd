CREATE TABLE IF NOT EXISTS ferramental.produtos_relacionados (
    log_id              uuid not null,
    estabelecimento     TEXT,
    produto             TEXT,
    cod_produto         TEXT,
    desc_produto        TEXT,
    des_marca_grendene  TEXT,
    ultimo_lancamento   TEXT,
    descricao_componente TEXT
    ,loaded_at timestamptz not null default current_timestamp
)
