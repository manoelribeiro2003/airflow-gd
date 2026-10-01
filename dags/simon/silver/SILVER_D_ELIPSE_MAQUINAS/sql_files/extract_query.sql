-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [ID]
, [ID_Pavilhao]
, [Nome]
, [Descricao]
, [Hora_Criacao]
, [IP]
FROM elipse.dbo.[Maquinas] WITH (NOLOCK)
