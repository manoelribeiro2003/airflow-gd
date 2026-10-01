SELECT
  {estab} AS id_estabelecimento
, [E3TimeStamp]
, [Codigo]
, [Valor]
, [Maquina_ID]
, [Ciclo]
, [Pares_Batida]
, [Turno]
, [Programa]
, [Documento]
, [NumeroProduto]
, [Efetivo]
, [Maquina_ID_Origem]
FROM [Elipse].[dbo].[Perdas_Qualidade] WITH (NOLOCK)
WHERE
  ([E3TimeStamp] >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
