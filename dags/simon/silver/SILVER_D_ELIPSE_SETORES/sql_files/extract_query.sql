-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [ID]
, [ID_Fabrica]
, [Pavilhao]
FROM [elipse].[dbo].[Pavilhao] WITH (NOLOCK)
