TRUNCATE TABLE elipse.gold.cadastros_maquinas;

INSERT INTO elipse.gold.cadastros_maquinas
SELECT
  cm.id_estabelecimento
, cm.id
, cm.nome
, cm.descricao
, cm.hora_criacao
, cm.ip
, cm.ativo
, cm.data_desativacao
, cs.id_fabrica
, cf.descricao AS fabrica
, cm.id_setor
, cs.descricao AS setor
FROM
  elipse.silver.cadastros_maquinas cm
  LEFT JOIN (
    SELECT
      id_estabelecimento
    , id
    , descricao
    , id_fabrica
    FROM
      elipse.silver.cadastros_setores
  ) cs
  ON
    cm.id_setor = cs.id AND cm.id_estabelecimento = cs.id_estabelecimento
  LEFT JOIN (
    SELECT
      id_estabelecimento
    , id
    , descricao
    FROM elipse.silver.cadastros_fabricas
  ) cf
  ON cs.id_fabrica = cf.id AND cs.id_estabelecimento = cf.id_estabelecimento
