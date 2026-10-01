-- sqlfluff:dialect:tsql
SELECT
  CAST('{estab}' AS INT)          AS id_estabelecimento
, CAST('{id_equipamento}' AS INT) AS id_equipamento
, [E3TimeStamp]
, [Ciclo Atual]
, [Ciclo TI]
, [Diferenca]
, [Turno]
, [Programa]
, [Documento]
, [NumeroProduto]
, [Efetivo]
, [ferramental]
, [cod_refer_matriz]
, [ParBat]
FROM [Elipse].dbo.[{table_name}] WITH (NOLOCK)
WHERE
  e3timestamp >= '{dt_inicio}'
  AND e3timestamp < '{dt_fim}'
