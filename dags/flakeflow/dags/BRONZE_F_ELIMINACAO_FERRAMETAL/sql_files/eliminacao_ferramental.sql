-- sqlfluff:dialect:postgres
with tabela_unificada as (
 SELECT DISTINCT
     wl.id AS identificador,
     wl.workflow_executado_id AS id_workflow_exe,
     wl.data->'corpo'->>'estab' AS estabelecimento,
     wl.data->'corpo'->>'mercado' AS mercado,
     wl.data->'corpo'->>'produto' AS produto,
     wl.data->'corpo'->>'codEstab' AS cod_estabelecimento,
     wl.data->'corpo'->>'deposito' AS deposito,
     wl.data->'corpo'->>'codProduto' AS cod_produto,
     wl.data->'corpo'->>'codDeposito' AS cod_deposito,
     wl.data->'corpo'->>'descProduto' AS descricao_produto,
     wl.data->'corpo'->>'marcaGrendene' AS marca,
     wl.data->'corpo'->>'statusProduto' AS status_produto,
     wl.data->'corpo'->>'valorResidual' AS valor_residual,
     wl.data->'corpo'->>'descFerramenta' AS descricao_ferramenta,
     wl.data->'corpo'->>'numeroProcesso' AS numero_processo,
     wl.data->'corpo'->>'tipoFerramenta' AS tipo_ferramenta,
     wl.data->'corpo'->>'dataLimiteAnalise' AS data_limite_analise,
     wl.data->'corpo'->>'segmentoDeNegocio' AS segmento_negocio,
     wl.data->'corpo'->>'codGrupoFerramental' AS cod_grupo_ferramental,
     wl.data->'corpo'->>'descGrupoFerramental' AS descricao_grupo_ferramental,
     sku_item->>'sku' AS sku,
     sku_item->>'descricao' AS descricao_sku,
     sku_item->>'qtdEstoque' AS qtd_estoque_sku,
     p.data_reserva,
     p.justificativa
 FROM workflow_logs wl
 LEFT JOIN LATERAL jsonb_array_elements(
     wl.data->'corpo'->'skuFerramentas'
 ) AS sku_item ON TRUE
 LEFT JOIN (
     SELECT
         wl.workflow_executado_id,
         MAX(CASE
             WHEN resp->>'id' = '01fd5581-c5ad-4c26-bf8b-0879e0b4a501'
             THEN resp->>'valor'
         END) AS data_reserva,
         MAX(CASE
             WHEN resp->>'id' = '77fec7fd-fb53-43a5-a880-bbae1887b8c2'
             THEN resp->>'valor'
         END) AS justificativa
     FROM workflow_logs wl
     CROSS JOIN LATERAL jsonb_array_elements(wl.data->'respostas') resp
     WHERE wl.no_id = '217528b8-69db-4f71-8111-00357f76355b'
     GROUP BY wl.workflow_executado_id
 ) p ON p.workflow_executado_id = wl.workflow_executado_id
 WHERE
     wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
     AND wl.log_anterior_id IS NULL
     AND wl.criado_em > '2025-11-04'
 UNION ALL
 SELECT
     wl.id AS identificador,
     wl.workflow_executado_id AS id_workflow_exe,
     fer->>'estab' AS estabelecimento,
     fer->>'mercado' AS mercado,
     fer->>'produto' AS produto,
     fer->>'codEstab' AS cod_estabelecimento,
     fer->>'deposito' AS deposito,
     fer->>'codProduto' AS cod_produto,
     fer->>'codDeposito' AS cod_deposito,
     fer->>'descProduto' AS descricao_produto,
     fer->>'marcaGrendene' AS marca,
     fer->>'statusProduto' AS status_produto,
     fer->>'valorResidual' AS valor_residual,
     fer->>'descFerramenta' AS descricao_ferramenta,
     fer->>'numeroProcesso' AS numero_processo,
     fer->>'tipoFerramenta' AS tipo_ferramenta,
     NULL AS data_limite_analise,
     fer->>'segmentoDeNegocio' AS segmento_negocio,
     fer->>'codGrupoFerramental' AS cod_grupo_ferramental,
     fer->>'descGrupoFerramental' AS descricao_grupo_ferramental,
     sku->>'sku' AS sku,
     sku->>'descricao' AS descricao_sku,
     sku->>'qtdEstoque' AS qtd_estoque_sku,
     NULL AS data_reserva,
     NULL AS justificativa
 FROM workflow_logs wl
 LEFT JOIN LATERAL jsonb_array_elements(
     wl.data->'result'->'ferramentais'
 ) fer ON TRUE
 LEFT JOIN LATERAL jsonb_array_elements(
     fer->'skuFerramentas'
 ) sku ON TRUE
 WHERE
     wl.workflow_id = '395ecda5-ab4f-442f-8115-196752a8a33e'
     AND wl.no_id = 'fb0d1bd2-39c3-4cfa-848f-ec64be4ed1a8'
     AND wl.criado_em > '2025-11-04'
),
area_sku as (
 select distinct
     ferr->>'desArea' AS area,
     sku->>'codSku' AS sku
 FROM workflow_logs wl
 LEFT JOIN LATERAL jsonb_array_elements(
     wl.data->'result'->'corpoParaAPIReservar'->'Ferramentais'
 ) ferr ON TRUE
 LEFT JOIN LATERAL jsonb_array_elements(
     ferr->'skuFerramentas'
 ) sku ON TRUE
 where 1=1
 and wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
 AND wl.tipo = 'CODE' and wl.data->'result'->>'corpoParaAPIReservar' is not null
 and criado_em > '2025-11-04'
)
select
tu.*,
a.area
from tabela_unificada tu
left join area_sku a
on a.sku = tu.sku
