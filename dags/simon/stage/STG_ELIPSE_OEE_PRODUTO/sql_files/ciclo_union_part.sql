SELECT
    {id_maquina}  AS cod_maquina,
    E3TimeStamp   AS ts_ciclo,
    NumeroProduto AS cod_produto,
    CASE WHEN Diferenca <= 0 THEN Diferenca ELSE 0 END AS ganho_ciclo,
    CASE WHEN Diferenca >= 0 THEN Diferenca ELSE 0 END AS perda_ciclo
FROM [Elipse].dbo.[{table_name}] WITH (NOLOCK)
WHERE E3TimeStamp >= '{dt_inicio}'
  AND E3TimeStamp <= '{dt_fim}'
