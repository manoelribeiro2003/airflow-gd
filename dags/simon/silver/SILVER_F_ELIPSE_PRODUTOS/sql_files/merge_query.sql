MERGE INTO elipse.silver.cadastros_produtos AS cp
USING elipse.silver.temp_produtos AS o ON
  cp.id_estabelecimento = o.id_estabelecimento AND cp.id = o."ID"
WHEN MATCHED AND (
  cp.id_estabelecimento IS DISTINCT FROM o.id_estabelecimento
  OR cp.id IS DISTINCT FROM o."ID"
  OR cp.id_equipamento IS DISTINCT FROM o."ID_Maq"
  OR cp.numero_produto IS DISTINCT FROM o."NumeroProduto"
  OR cp.programa IS DISTINCT FROM o."Programa"
  OR cp.documento IS DISTINCT FROM o."Documento"
  OR cp.data_inicio IS DISTINCT FROM o."DataInicio"
  OR cp.data_fim IS DISTINCT FROM o."DataFim"
  OR cp.ciclo IS DISTINCT FROM o."Ciclo"
  OR cp.pares_batidas IS DISTINCT FROM o."ParesBatidas"
  OR cp.efetivo IS DISTINCT FROM o."Efetivo"
)
  THEN
  UPDATE
    SET
      id_estabelecimento = o.id_estabelecimento
    , id = o."ID"
    , id_equipamento = o."ID_Maq"
    , numero_produto = o."NumeroProduto"
    , programa = o."Programa"
    , documento = o."Documento"
    , data_inicio = o."DataInicio"
    , data_fim = o."DataFim"
    , ciclo = o."Ciclo"
    , pares_batidas = o."ParesBatidas"
    , efetivo = o."Efetivo"
    , data_atualizacao_db = now() - INTERVAL '3 hours'
WHEN NOT MATCHED BY TARGET
  THEN
  INSERT (
    id_estabelecimento
  , id
  , id_equipamento
  , numero_produto
  , programa
  , documento
  , data_inicio
  , data_fim
  , ciclo
  , pares_batidas
  , efetivo
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento
  , o."ID"
  , o."ID_Maq"
  , o."NumeroProduto"
  , o."Programa"
  , o."Documento"
  , o."DataInicio"
  , o."DataFim"
  , o."Ciclo"
  , o."ParesBatidas"
  , o."Efetivo"
  , now() - INTERVAL '3 hours'
  )
WHEN NOT MATCHED BY SOURCE AND (
  cp.data_inicio >= current_date - INTERVAL '31 days'
  OR cp.data_fim >= current_date - INTERVAL '31 days'
)
  THEN
  DELETE;


DROP TABLE elipse.silver.temp_produtos
