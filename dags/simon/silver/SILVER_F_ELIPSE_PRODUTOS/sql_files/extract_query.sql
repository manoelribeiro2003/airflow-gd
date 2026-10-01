SELECT
  {estab}                                id_estabelecimento
, [ID]
, [ID_Maq]
, [NumeroProduto]
, [Programa]
, [Documento]
, [DataInicio]
, COALESCE([DataFim], CURRENT_TIMESTAMP) AS [DataFim]
, [Ciclo]
, [ParesBatidas]
, [Efetivo]
FROM elipse.dbo.[Produtos] WITH (NOLOCK)
WHERE
  ([DataInicio] >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
  OR
  (COALESCE([DataFim], CURRENT_TIMESTAMP) >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
