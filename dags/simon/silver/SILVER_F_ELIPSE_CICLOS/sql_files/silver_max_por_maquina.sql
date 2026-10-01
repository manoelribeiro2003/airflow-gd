SELECT
  id_equipamento
, MAX(data_hora) AS ultima_data_hora
FROM silver.oee_fciclos
WHERE
  id_estabelecimento = CAST('{estab_code}' AS INT)
GROUP BY id_equipamento
