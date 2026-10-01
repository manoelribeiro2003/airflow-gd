--Tabela ProdutosRelacionados
SELECT wl.id AS log_id,
  sku->>'estab' AS estabelecimento,
  sku->>'produto' AS produto,
  sku->>'codProduto' AS codProduto,
  sku->>'descProduto' AS descProduto,
  sku->>'desMarcaGrendene' AS desMarcaGrendene,
  sku->>'ultimoLancamento' AS ultimoLancamento,
  sku->>'descricaoComponente' AS descricaoComponente
FROM workflow_logs wl
  CROSS JOIN LATERAL jsonb_array_elements(wl.data->'corpo'->'produtosRelacionados') sku
WHERE 1 = 1
  AND (
    wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
    OR wl.workflow_id = '395ecda5-ab4f-442f-8115-196752a8a33e'
  )
  AND tipo = 'WEB_HOOK'
  AND wl.data->'corpo' ? 'produtosRelacionados'
