--Tabela Area.
SELECT wl.id,
  wl.criado_em AS Data_Criacao,
  wl.atualizado_em AS atualizadoem,
  wl.status AS STATUS,
  param->>'id_flake' AS id_flake,
  param->>'cod_usuario' AS cod_usuario,
  ferr->>'desArea' AS des_area,
  TO_DATE(ferr->>'datReserva', 'DD/MM/YYYY') AS data_reserva,
  ferr->>'desJustificativa' AS justificativa,
  sku->>'codSku' AS cod_sku,
  (
    regexp_matches(
      input->>'code',
      'getWorkflowVariable\("([a-f0-9\-]+)\.numeroProcesso"\)'
    )
  ) [1] AS webhook_node_id
FROM workflow_logs wl
  LEFT JOIN LATERAL jsonb_array_elements(
    wl.data->'result'->'corpoParaAPIReservar'->'param'
  ) param ON TRUE
  LEFT JOIN LATERAL jsonb_array_elements(
    wl.data->'result'->'corpoParaAPIReservar'->'Ferramentais'
  ) ferr ON TRUE
  LEFT JOIN LATERAL jsonb_array_elements(ferr->'skuFerramentas') sku ON TRUE
WHERE 1 = 1
  AND (
    wl.workflow_id = '8b301608-9bc5-4042-9835-7e02d4beec52'
    OR wl.workflow_id = '395ecda5-ab4f-442f-8115-196752a8a33e'
  )
  AND wl.tipo = 'CODE'
  AND wl.data->'result'->>'corpoParaAPIReservar' IS NOT NULL
