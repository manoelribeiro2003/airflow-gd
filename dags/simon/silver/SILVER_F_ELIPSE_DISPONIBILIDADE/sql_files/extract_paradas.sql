SELECT
  {estab} AS id_estabelecimento
, [Id]
, [Maquina_ID]
, [Codigo]
, [Hora_Inicio]
, [E3TimeStamp]
, [tempo]
, [Turno]
, [Status]
, [Programa]
, [Documento]
, [NumeroProduto]
, [Efetivo]
, [ID_Grupo]
, [Ref_Matriz]
, [Ferramental]
, [Cracha_Operador]
, [Cracha_Preparador]
, [Cracha_Lider]
, [Cracha_Apoio]
FROM [Elipse].[dbo].[Paradas] WITH (NOLOCK)
WHERE
  ([Hora_Inicio] >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
  OR
  ([E3TimeStamp] >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
