WITH cte_qualidade AS (
  SELECT
    q.id_estabelecimento
  , q.data_hora
  , q.codigo
  , cm.descricao
  , cm.peso_oee
  , q.maquina_id                         AS id_equipamento
  , maq.nome                             AS nome_equipamento
  , cs.descricao                         AS setor
  , cf.descricao                         AS fabrica
  , q.ciclo
  , q.valor
  , q.pares_batida
  , (q.ciclo * q.valor) / q.pares_batida AS tempo_perda_qualidade
  , q.efetivo
  , q.turno
  , q.numero_produto
  , q.programa
  , q.documento
  , q.maquina_id_origem
  , maq2.nome                            AS nome_equipamento_origem
  FROM elipse.silver.oee_fqualidade q
    LEFT JOIN elipse.silver.cadastros_motivos cm ON
      q.codigo = cm.codigo AND q.id_estabelecimento = cm.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_maquinas maq ON
      q.maquina_id = maq.id AND q.id_estabelecimento = maq.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_setores cs ON
      maq.id_setor = cs.id AND q.id_estabelecimento = cs.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_fabricas cf ON
      cf.id = cs.id_fabrica AND q.id_estabelecimento = cf.id_estabelecimento
    LEFT JOIN elipse.silver.cadastros_maquinas maq2 ON
      q.maquina_id_origem = maq2.id AND q.id_estabelecimento = maq2.id_estabelecimento
  WHERE
    q.data_hora >= CURRENT_DATE - INTERVAL '90 days'
)

MERGE INTO elipse.gold.oee_fqualidade q
USING cte_qualidade o
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
    , pares_batida = o.pares_batida
    , tempo_perda_qualidade = o.tempo_perda_qualidade
    , efetivo = o.efetivo
    , turno = o.turno
    , numero_produto = o.numero_produto
    , programa = o.programa
    , documento = o.documento
    , maquina_id_origem = o.maquina_id_origem
    , nome_equipamento_origem = o.nome_equipamento_origem
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
  , pares_batida
  , tempo_perda_qualidade
  , efetivo
  , turno
  , numero_produto
  , programa
  , documento
  , maquina_id_origem
  , nome_equipamento_origem
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
  , o.pares_batida
  , o.tempo_perda_qualidade
  , o.efetivo
  , o.turno
  , o.numero_produto
  , o.programa
  , o.documento
  , o.maquina_id_origem
  , o.nome_equipamento_origem
  , NOW() - INTERVAL '3 hours'
  )
WHEN NOT MATCHED BY SOURCE AND q.data_hora >= CURRENT_DATE - INTERVAL '90 days'
  THEN
  DELETE;
