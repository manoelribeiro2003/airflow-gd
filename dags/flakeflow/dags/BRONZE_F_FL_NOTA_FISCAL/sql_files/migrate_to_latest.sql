-- sqlfluff:dialect:postgres
-- Migracao UNICA (rodar manualmente via worker, fora do fluxo diario da DAG).
-- Recalcula o estado atual (1 linha por sku) a partir das 161M ja no destino,
-- faz swap de nomes e (apos validar) dropa a tabela antiga.
--
-- Colunas + PK definidas explicitamente: NAO usa LIKE, pois a tabela existente
-- ainda esta no formato antigo (161M, sem PK) e o LIKE copiaria esse formato.

CREATE TABLE ferramental.fl_nota_fiscal_new (
  sku text PRIMARY KEY
, numero_fl text
, numero_nf text
, data_movimento date
, criado_em timestamp
, atualizado_em timestamp
, log_id uuid
, loaded_at timestamptz NOT NULL DEFAULT current_timestamp
);

INSERT INTO ferramental.fl_nota_fiscal_new
(sku, numero_fl, numero_nf, data_movimento, criado_em, atualizado_em, log_id)
SELECT DISTINCT ON (sku)
  sku
, numero_fl
, numero_nf
, data_movimento
, criado_em
, atualizado_em
, log_id
FROM ferramental.fl_nota_fiscal
WHERE
  sku IS NOT NULL AND sku <> ''            -- sku e PK: nao pode nulo/vazio
ORDER BY sku, atualizado_em DESC, data_movimento DESC;

-- swap de nomes: a antiga vira _old_161m, a nova assume o nome canonico.
ALTER TABLE ferramental.fl_nota_fiscal RENAME TO fl_nota_fiscal_old_161m;
ALTER TABLE ferramental.fl_nota_fiscal_new RENAME TO fl_nota_fiscal;

-- so depois de validar count (~5.6k) e ausencia de sku duplicado:
-- DROP TABLE ferramental.fl_nota_fiscal_old_161m;
