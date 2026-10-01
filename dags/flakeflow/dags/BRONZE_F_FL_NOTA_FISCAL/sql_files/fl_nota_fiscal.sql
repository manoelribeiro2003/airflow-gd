-- sqlfluff:dialect:postgres
-- Roda no servidor fonte (via DuckDB postgres_query). Os predicados de coluna
-- filtram pelo indice de no_id ANTES do detoast/expansao do JSONB; so as linhas
-- sobreviventes sao detoastadas. O marcador __WINDOW__ e trocado em Python
-- pela janela de backfill (criado_em) ou incremental (atualizado_em).
-- DISTINCT ON (codSku): ja devolve 1 linha por sku (a mais recente) por janela,
-- entao o parquet fica minusculo (~5.6k linhas em vez de dezenas de milhoes).
SELECT DISTINCT ON (fer ->> 'codSku')
  fer ->> 'codSku'                               AS sku
, fer ->> 'numFL'                                AS numero_fl
, fer ->> 'numNF'                                AS numero_nf
, TO_DATE(fer ->> 'dataMovimento', 'DD/MM/YYYY') AS data_movimento
, fer->>'acao'                                   AS acao
, fer->>'numLote'                                AS num_lote
, wl.criado_em
, wl.atualizado_em
, wl.id                                          AS log_id
FROM workflow_logs wl
  CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(
    wl.data -> 'response' -> 'Ferramentais'
  ) fer
WHERE
  wl.workflow_id = 'd78ebcfe-d1c5-4ea2-86d1-e2f405c0c78e'
  AND wl.no_id = 'c332e642-b545-4c6f-8234-5b20a5172e1f'
  AND wl.data ->> 'status' = '200'
  -- linha com pagina TOAST corrompida (block 754725); id <> poda no heap
  -- antes do detoast, evitando 'invalid page'. Remover apos reparo do banco.
  AND wl.id <> 'bf8e6b50-d476-430d-bea9-926ddf5672df'
  -- __WINDOW__
  AND NULLIF(TRIM(fer ->> 'numFL'), '') IS NOT NULL
  AND NULLIF(TRIM(fer ->> 'codSku'), '') IS NOT NULL
ORDER BY
  fer ->> 'codSku'
, wl.atualizado_em DESC
, TO_DATE(fer ->> 'dataMovimento', 'DD/MM/YYYY') DESC
