-- sqlfluff:dialect:postgres
DELETE FROM elipse.gold.elipse_fapoio
WHERE
  data_hora_inicio >= CURRENT_DATE - INTERVAL '90 days'
  OR data_hora_fim >= CURRENT_DATE - INTERVAL '90 days';


INSERT INTO elipse.gold.elipse_fapoio (
  id_estabelecimento
, id
, data_hora_inicio
, data_hora_fim
, tempo
, status
, codigo
, descricao_motivo
, familia
, peso_oee
, maquina_id
, nome_equipamento
, id_setor
, setor
, id_fabrica
, fabrica
, cracha_preparador
, cracha_lider
)
SELECT
  apoio.id_estabelecimento
, apoio.id
, apoio.data_hora_inicio
, apoio.data_hora_fim
, apoio.tempo
, apoio.status
, apoio.codigo
, mtv.descricao AS descricao_motivo
, cfa.descricao AS familia
, mtv.peso_oee
, apoio.maquina_id
, maq.nome      AS nome_equipamento
, maq.id_setor
, cs.descricao  AS setor
, cs.id_fabrica
, cf.descricao  AS fabrica
, apoio.cracha_preparador
, apoio.cracha_lider
FROM elipse.silver.elipse_fapoio apoio
  LEFT JOIN elipse.silver.cadastros_motivos mtv ON
    apoio.codigo = mtv.codigo AND apoio.id_estabelecimento = mtv.id_estabelecimento
  LEFT JOIN elipse.silver.cadastros_maquinas maq ON
    apoio.maquina_id = maq.id AND apoio.id_estabelecimento = maq.id_estabelecimento
  LEFT JOIN elipse.silver.cadastros_setores cs ON
    maq.id_setor = cs.id AND maq.id_estabelecimento = cs.id_estabelecimento
  LEFT JOIN elipse.silver.cadastros_fabricas cf ON
    cs.id_fabrica = cf.id AND cs.id_estabelecimento = cf.id_estabelecimento
  LEFT JOIN elipse.silver.cadastros_familias cfa ON
    mtv.id_familia = cfa.id AND mtv.id_estabelecimento = cfa.id_estabelecimento
WHERE
  data_hora_inicio >= CURRENT_DATE - INTERVAL '90 days'
  OR data_hora_fim >= CURRENT_DATE - INTERVAL '90 days'
ON CONFLICT DO NOTHING;
-- ON CONFLICT (id_estabelecimento, id)
-- DO UPDATE SET
--   data_hora_inicio     = EXCLUDED.data_hora_inicio,
--   data_hora_fim        = EXCLUDED.data_hora_fim,
--   tempo                = EXCLUDED.tempo,
--   status               = EXCLUDED.status,
--   codigo               = EXCLUDED.codigo,
--   descricao_motivo     = EXCLUDED.descricao_motivo,
--   familia              = EXCLUDED.familia,
--   peso_oee             = EXCLUDED.peso_oee,
--   maquina_id           = EXCLUDED.maquina_id,
--   nome_equipamento     = EXCLUDED.nome_equipamento,
--   id_setor             = EXCLUDED.id_setor,
--   setor                = EXCLUDED.setor,
--   id_fabrica           = EXCLUDED.id_fabrica,
--   fabrica              = EXCLUDED.fabrica,
--   cracha_preparador    = EXCLUDED.cracha_preparador,
--   cracha_lider         = EXCLUDED.cracha_lider;
