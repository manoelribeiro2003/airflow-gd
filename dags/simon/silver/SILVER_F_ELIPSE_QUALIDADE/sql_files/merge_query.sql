MERGE INTO elipse.silver.oee_fqualidade AS q
USING elipse.silver.temp_qualidade AS o
ON (
  q.data_hora = o."E3TimeStamp"
  AND q.maquina_id = o."Maquina_ID"
  AND q.id_estabelecimento = o.id_estabelecimento
  AND q.codigo = o."Codigo"
)
WHEN MATCHED AND (
  q.id_estabelecimento IS DISTINCT FROM o.id_estabelecimento
  OR q.data_hora IS DISTINCT FROM o."E3TimeStamp"
  OR q.codigo IS DISTINCT FROM o."Codigo"
  OR q.valor IS DISTINCT FROM o."Valor"
  OR q.maquina_id IS DISTINCT FROM o."Maquina_ID"
  OR q.ciclo IS DISTINCT FROM o."Ciclo"
  OR q.pares_batida IS DISTINCT FROM o."Pares_Batida"
  OR q.turno IS DISTINCT FROM o."Turno"
  OR q.numero_produto IS DISTINCT FROM o."NumeroProduto"
  OR q.programa IS DISTINCT FROM o."Programa"
  OR q.documento IS DISTINCT FROM o."Documento"
  OR q.efetivo IS DISTINCT FROM o."Efetivo"
  OR q.maquina_id_origem IS DISTINCT FROM o."Maquina_ID_Origem"
)
  THEN
  UPDATE
    SET
      id_estabelecimento = o.id_estabelecimento
    , data_hora = o."E3TimeStamp"
    , codigo = o."Codigo"
    , valor = o."Valor"
    , maquina_id = o."Maquina_ID"
    , ciclo = o."Ciclo"
    , pares_batida = o."Pares_Batida"
    , turno = o."Turno"
    , numero_produto = o."NumeroProduto"
    , programa = o."Programa"
    , documento = o."Documento"
    , efetivo = o."Efetivo"
    , maquina_id_origem = o."Maquina_ID_Origem"
    , data_atualizacao_db = now() - INTERVAL '3 hours'
WHEN NOT MATCHED BY TARGET
  THEN
  INSERT (
    id_estabelecimento
  , data_hora
  , codigo
  , valor
  , maquina_id
  , ciclo
  , pares_batida
  , turno
  , numero_produto
  , programa
  , documento
  , efetivo
  , maquina_id_origem
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento
  , o."E3TimeStamp"
  , o."Codigo"
  , o."Valor"
  , o."Maquina_ID"
  , o."Ciclo"
  , o."Pares_Batida"
  , o."Turno"
  , o."NumeroProduto"
  , o."Programa"
  , o."Documento"
  , o."Efetivo"
  , o."Maquina_ID_Origem"
  , now() - INTERVAL '3 hours'
  )
WHEN NOT MATCHED BY SOURCE AND q.data_hora >= current_date - INTERVAL '90 days'
  THEN
  DELETE;


DROP TABLE elipse.silver.temp_qualidade;
