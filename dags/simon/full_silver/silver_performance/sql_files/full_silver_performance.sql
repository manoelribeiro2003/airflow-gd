SELECT
  ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as linha,
  ? AS id_estabelecimento,
  E3TimeStamp,
  Maquina_ID,
  Codigo,
  Valor,
  Ciclo,
  Turno,
  Programa,
  Documento,
  Cracha_Operador,
  NumeroProduto,
  Efetivo
FROM [Elipse].[dbo].[Perdas_Performance] WITH(NOLOCK)
WHERE
E3TimeStamp between ? and ?