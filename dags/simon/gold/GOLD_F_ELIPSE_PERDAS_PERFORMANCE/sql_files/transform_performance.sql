WITH cte_performance AS (
  SELECT
    q.id_estabelecimento
  , q.data_hora
  , q.codigo
  , cm.descricao
  , cm.peso_oee
  , q.maquina_id        AS id_equipamento
  , maq.nome            AS nome_equipamento
  , cs.descricao        AS setor
  , cf.descricao        AS fabrica
  , q.ciclo
  , q.valor
  , (q.ciclo * q.valor) AS tempo_perda_performance
  , q.efetivo
  , q.turno
  , q.numero_produto
  , q.programa
  , q.documento
  , q.cracha_preparador
  , q.cracha_lider
  FROM elipse.silver.oee_fperformance q
    LEFT JOIN elipse.silver.cadastros_motivos cm ON
      q.codigo = cm.codigo AND q.id_estabelecimento = cm.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_maquinas maq ON
      q.maquina_id = maq.id AND q.id_estabelecimento = maq.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_setores cs ON
      maq.id_setor = cs.id AND q.id_estabelecimento = cs.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_fabricas cf ON
      cf.id = cs.id_fabrica AND q.id_estabelecimento = cf.id_estabelecimento
  WHERE
    q.data_hora >= CURRENT_DATE - INTERVAL '90 days'
)

MERGE INTO elipse.gold.oee_fperformance q
USING cte_performance o
ON q.id_estabelecimento = o.id_estabelecimento
  AND q.id_equipamento = o.id_equipamento
  AND q.data_hora = o.data_hora
  AND q.codigo = o.codigo
WHEN MATCHED
  THEN
  UPDATE
    SET
      id_estabelecimento = o.id_estabelecimento
    , data_hora = o.data_hora
    , codigo = o.codigo
    , descricao = o.descricao
    , peso_oee = o.peso_oee
    , id_equipamento = o.id_equipamento
    , nome_equipamento = o.nome_equipamento
    , setor = o.setor
    , fabrica = o.fabrica
    , ciclo = o.ciclo
    , valor = o.valor
    , tempo_perda_performance = o.tempo_perda_performance
    , efetivo = o.efetivo
    , turno = o.turno
    , numero_produto = o.numero_produto
    , programa = o.programa
    , documento = o.documento
    , cracha_preparador = o.cracha_preparador
    , cracha_lider = o.cracha_lider
    , data_atualizacao_db = NOW() - INTERVAL '3 hours'
WHEN NOT MATCHED BY TARGET
  THEN
  INSERT (
    id_estabelecimento
  , data_hora
  , codigo
  , descricao
  , peso_oee
  , id_equipamento
  , nome_equipamento
  , setor
  , fabrica
  , ciclo
  , valor
  , tempo_perda_performance
  , efetivo
  , turno
  , numero_produto
  , programa
  , documento
  , cracha_preparador
  , cracha_lider
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento
  , o.data_hora
  , o.codigo
  , o.descricao
  , o.peso_oee
  , o.id_equipamento
  , o.nome_equipamento
  , o.setor
  , o.fabrica
  , o.ciclo
  , o.valor
  , o.tempo_perda_performance
  , o.efetivo
  , o.turno
  , o.numero_produto
  , o.programa
  , o.documento
  , o.cracha_preparador
  , o.cracha_lider
  , NOW() - INTERVAL '3 hours'
  )
WHEN NOT MATCHED BY SOURCE AND q.data_hora >= CURRENT_DATE - INTERVAL '90 days'
  THEN
  DELETE;
