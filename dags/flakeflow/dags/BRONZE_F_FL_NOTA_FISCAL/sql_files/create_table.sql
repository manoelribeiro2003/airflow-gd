-- sqlfluff:dialect:postgres
-- Tabela destino no formato final: 1 linha por sku (estado atual). PK em sku ja
-- serve como indice de busca; ~5.6k linhas, sem particao. Idempotente, nunca dropa.
CREATE TABLE IF NOT EXISTS ferramental.fl_nota_fiscal (
  sku text PRIMARY KEY
, numero_fl text
, numero_nf text
, data_movimento date
, acao text
, num_lote text
, criado_em timestamp
, atualizado_em timestamp
, log_id uuid
, loaded_at timestamptz NOT NULL DEFAULT current_timestamp
);
