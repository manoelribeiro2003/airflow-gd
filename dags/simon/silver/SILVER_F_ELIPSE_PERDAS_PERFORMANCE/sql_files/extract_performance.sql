SELECT
  {estab} AS id_estabelecimento
, [E3TimeStamp]
, [Maquina_ID]
, [Codigo]
, [Valor]
, [Ciclo]
, [Turno]
, [Programa]
, [Documento]
, [Cracha_operador]
, [NumeroProduto]
, [Efetivo]
, [Cracha_Preparador]
, [Cracha_Lider]
FROM [Elipse].[dbo].[Perdas_Performance] WITH (NOLOCK)
WHERE
  ([E3TimeStamp] >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
