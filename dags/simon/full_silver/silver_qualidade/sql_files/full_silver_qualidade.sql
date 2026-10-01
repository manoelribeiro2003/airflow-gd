SELECT 
    ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as linha,
    ? AS id_estabelecimento,
    E3TimeStamp
    ,Codigo
    ,Valor
    ,Maquina_ID
    ,Ciclo
    ,Pares_Batida
    ,Turno
    ,Programa
    ,Documento
    ,NumeroProduto
    ,Efetivo
    ,Maquina_ID_Origem
FROM [Elipse].[dbo].[Perdas_Qualidade] WITH (NOLOCK)
WHERE
E3TimeStamp between ? and ?
