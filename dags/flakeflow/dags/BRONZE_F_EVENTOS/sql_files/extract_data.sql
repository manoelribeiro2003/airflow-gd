--Tabela Eventos.
SELECT --tipo,
  --data->>'corpo' as Corpo,
  id AS ID_Log,
  criado_em AS Data_Criacao,
  atualizado_em AS Atualizado_Em,
  data->'corpo'->>'estab' AS Estabelecimento,
  data->'corpo'->>'mercado' AS Mercado,
  data->'corpo'->>'produto' AS Produto,
  (data->'corpo'->>'codEstab')::int2 AS CodEstabelecimento,
  data->'corpo'->>'deposito' AS Deposito,
  data->'corpo'->>'codDeposito' AS codDeposito,
  data->'corpo'->>'codProduto' AS codProduto,
  data->'corpo'->>'descProduto' AS descProduto,
  (data->'corpo'->>'qtdeEliminar')::int4 AS qtdeEliminar,
  data->'corpo'->>'marcaGrendene' AS marcaGrendene,
  data->'corpo'->>'statusProduto' AS statusProduto,
  data->'corpo'->>'valorResidual' AS valorResidual,
  data->'corpo'->>'descFerramenta' AS descFerramenta,
  data->'corpo'->>'numeroProcesso' AS numeroProcesso,
  data->'corpo'->>'tipoFerramenta' AS tipoFerramenta,
  (data->'corpo'->>'qtdeEstoqueAtual')::float4 AS qtdeEstoqueAtual,
  to_date(
    data->'corpo'->>'dataLimiteAnalise',
    'DD/MM/YYYY'
  ) AS dataLimiteAnalise,
  (data->'corpo'->>'segmentoDeNegocio')::int4 AS segmentoDeNegocio,
  data->'corpo'->>'codGrupoFerramental' AS codGrupoFerramental,
  data->'corpo'->>'descSegmentoNegocio' AS descSegmentoNegocio,
  data->'corpo'->>'descGrupoFerramental' AS descGrupoFerramental
FROM workflow_logs wl
WHERE 1 = 1
  AND (
    wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
    OR wl.workflow_id = '395ecda5-ab4f-442f-8115-196752a8a33e'
  )
  AND data IS NOT NULL
  AND tipo = 'WEB_HOOK'
  AND data->'corpo'->>'estab' IS NOT NULL
