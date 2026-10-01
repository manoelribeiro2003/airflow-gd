-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [ID]
, [Fabrica]
FROM elipse.dbo.fabricas WITH (NOLOCK)
