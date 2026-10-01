MERGE INTO {{params.database_id}}.{{params.target}} AS p
USING {{params.database_id}}.{{params.source}} AS o
ON (p.id = o."Id" AND p.id_estabelecimento = o.id_estabelecimento)
WHEN MATCHED AND (
  p.maquina_id IS DISTINCT FROM o."Maquina_ID"
  OR p.codigo IS DISTINCT FROM o."Codigo"
  OR p.data_hora_inicio IS DISTINCT FROM o."Hora_Inicio"
  OR p.data_hora_fim IS null
  OR (p.data_hora_fim IS NOT null AND p.data_hora_fim IS DISTINCT FROM o."E3TimeStamp")
  OR p.tempo IS DISTINCT FROM o.tempo
  OR p.turno IS DISTINCT FROM o."Turno"
  OR p.status IS DISTINCT FROM o."Status"
  OR p.programa IS DISTINCT FROM o."Programa"
  OR p.documento IS DISTINCT FROM o."Documento"
  OR p.numero_produto IS DISTINCT FROM o."NumeroProduto"
  OR p.efetivo::TEXT IS DISTINCT FROM o."Efetivo"::TEXT
  OR p.id_grupo IS DISTINCT FROM o."ID_Grupo"
  OR p.ref_matriz IS DISTINCT FROM o."Ref_Matriz"
  OR p.ferramental IS DISTINCT FROM o."Ferramental"
  OR p.cracha_apoio IS DISTINCT FROM o."Cracha_Apoio"
  OR p.cracha_operador IS DISTINCT FROM o."Cracha_Operador"
  OR p.cracha_preparador IS DISTINCT FROM o."Cracha_Preparador"
  OR p.cracha_lider IS DISTINCT FROM o."Cracha_Lider"
)
  THEN
  UPDATE
    SET
      maquina_id = o."Maquina_ID"
    , codigo = o."Codigo"
    , data_hora_inicio = o."Hora_Inicio"
    , data_hora_fim = o."E3TimeStamp"
    , tempo = o.tempo
    , turno = o."Turno"
    , status = o."Status"
    , programa = o."Programa"
    , documento = o."Documento"
    , numero_produto = o."NumeroProduto"
    , efetivo = o."Efetivo"
    , id_grupo = o."ID_Grupo"
    , ref_matriz = o."Ref_Matriz"
    , ferramental = o."Ferramental"
    , cracha_apoio = o."Cracha_Apoio"
    , cracha_operador = o."Cracha_Operador"
    , cracha_preparador = o."Cracha_Preparador"
    , cracha_lider = o."Cracha_Lider"
    , data_atualizacao_db = CURRENT_TIMESTAMP
WHEN NOT MATCHED BY TARGET
  THEN
  INSERT (
    id_estabelecimento
  , id
  , maquina_id
  , codigo
  , data_hora_inicio
  , data_hora_fim
  , tempo
  , turno
  , status
  , programa
  , documento
  , numero_produto
  , efetivo
  , id_grupo
  , ref_matriz
  , ferramental
  , cracha_apoio
  , cracha_operador
  , cracha_preparador
  , cracha_lider
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento
  , o."Id"
  , o."Maquina_ID"
  , o."Codigo"
  , o."Hora_Inicio"
  , o."E3TimeStamp"
  , o.tempo
  , o."Turno"
  , o."Status"
  , o."Programa"
  , o."Documento"
  , o."NumeroProduto"
  , o."Efetivo"
  , o."ID_Grupo"
  , o."Ref_Matriz"
  , o."Ferramental"
  , o."Cracha_Apoio"
  , o."Cracha_Operador"
  , o."Cracha_Preparador"
  , o."Cracha_Lider"
  , CURRENT_TIMESTAMP
  )
WHEN NOT MATCHED BY SOURCE AND (
  p.data_hora_inicio >= CURRENT_DATE - INTERVAL '90 days'
  OR p.data_hora_fim >= CURRENT_DATE - INTERVAL '90 days'
)
  THEN
  DELETE;
