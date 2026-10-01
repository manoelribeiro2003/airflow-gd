-- sqlfluff:dialect:tsql
SELECT
  CAST('{id_equipamento}' AS INT) AS id_equipamento
, MAX(e3timestamp)                AS max_ts
FROM [Elipse].dbo.[{table_name}] WITH (NOLOCK)
