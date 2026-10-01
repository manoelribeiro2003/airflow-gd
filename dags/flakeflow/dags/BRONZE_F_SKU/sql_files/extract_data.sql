--Tabela SKU.
SELECT wl.id AS log_id,
  sku->>'sku' AS sku,
  sku->>'descricao' AS descricao,
  sku->>'status' AS STATUS,
  (sku->>'qtdCif')::float4 AS qtdCif,
  sku->>'codFabrica' AS Fabrica,
  sku->>'ferramenta' AS ferramenta,
  (sku->>'qtdEstoque')::float4 AS qtd_estoque
FROM workflow_logs wl
  CROSS JOIN LATERAL jsonb_array_elements(wl.data->'corpo'->'skuFerramentas') sku
WHERE 1 = 1
  AND (
    wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
    OR wl.workflow_id = '395ecda5-ab4f-442f-8115-196752a8a33e'
  )
  AND tipo = 'WEB_HOOK'
  AND wl.data->'corpo' ? 'skuFerramentas'
