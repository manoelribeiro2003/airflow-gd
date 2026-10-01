-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [E3TimeStamp]
, [Indice]
, [Familia]
, [ID]
FROM [elipse].[dbo].[Familia_Paradas] WITH (NOLOCK)
