CREATE TABLE IF NOT EXISTS ferramental.area (
    id                uuid not null,
    data_criacao      TIMESTAMPtz,
    atualizado_em     TIMESTAMPtz,
    status            TEXT,
    id_flake          TEXT,
    cod_usuario       TEXT,
    des_area          TEXT,
    data_reserva      DATE,
    justificativa     TEXT,
    cod_sku           TEXT,
    webhook_node_id   uuid
    ,loaded_at timestamptz not null default current_timestamp
)
