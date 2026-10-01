MERGE INTO elipse.silver.oee_fperformance AS q
USING elipse.silver.temp_performance AS o
ON q.data_hora = o."E3TimeStamp"
  AND q.maquina_id = o."Maquina_ID"
  AND q.id_estabelecimento = o.id_estabelecimento
  AND q.codigo = o."Codigo"
WHEN MATCHED AND (
  q.id_estabelecimento IS DISTINCT FROM o.id_estabelecimento
  OR q.data_hora IS DISTINCT FROM o."E3TimeStamp"
  OR q.codigo IS DISTINCT FROM o."Codigo"
  OR q.valor IS DISTINCT FROM o."Valor"
  OR q.maquina_id IS DISTINCT FROM o."Maquina_ID"
  OR q.ciclo IS DISTINCT FROM o."Ciclo"
  OR q.turno IS DISTINCT FROM o."Turno"
  OR q.numero_produto IS DISTINCT FROM o."NumeroProduto"
  OR q.programa IS DISTINCT FROM o."Programa"
  OR q.documento IS DISTINCT FROM o."Documento"
  OR q.efetivo IS DISTINCT FROM o."Efetivo"
  OR q.cracha_preparador IS DISTINCT FROM o."Cracha_Preparador"
  OR q.cracha_lider IS DISTINCT FROM o."Cracha_Lider"

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
    , turno = o."Turno"
    , numero_produto = o."NumeroProduto"
    , programa = o."Programa"
    , documento = o."Documento"
    , efetivo = o."Efetivo"
    , cracha_preparador = o."Cracha_Preparador"
    , cracha_lider = o."Cracha_Lider"
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
  , turno
  , numero_produto
  , programa
  , documento
  , efetivo
  , cracha_preparador
  , cracha_lider
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento
  , o."E3TimeStamp"
  , o."Codigo"
  , o."Valor"
  , o."Maquina_ID"
  , o."Ciclo"
  , o."Turno"
  , o."NumeroProduto"
  , o."Programa"
  , o."Documento"
  , o."Efetivo"
  , o."Cracha_Preparador"
  , o."Cracha_Lider"
  , now() - INTERVAL '3 hours'
  )
WHEN NOT MATCHED BY SOURCE AND q.data_hora >= current_date - INTERVAL '90 days'
  THEN
  DELETE;


DROP TABLE elipse.silver.temp_performance;
