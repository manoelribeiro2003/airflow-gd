-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [Codigo]
, [Descricao]
, [PesoOEE]
, [ID_Familia]
, [E3TimeStamp]
FROM [elipse].[dbo].[Motivo_Paradas] WITH (NOLOCK)
