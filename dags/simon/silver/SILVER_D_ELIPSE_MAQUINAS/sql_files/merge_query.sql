-- sqlfluff:dialect:tsql
MERGE INTO elipse.silver.cadastros_maquinas maq USING
  elipse.silver.temp_maquinas e ON (
  maq.id = e."ID"
  AND maq.id_estabelecimento = e.id_estabelecimento
)
WHEN MATCHED
  THEN
  UPDATE
    SET
      id_estabelecimento = e.id_estabelecimento
    , id = e."ID"
    , id_setor = e."ID_Pavilhao"
    , nome = e."Nome"
    , descricao = e."Descricao"
    , hora_criacao = e."Hora_Criacao"
    , ip = e."IP"
    , ativo = true
    , data_atualizacao_db = CURRENT_TIMESTAMP
WHEN NOT MATCHED BY TARGET
  THEN
  INSERT (
    id_estabelecimento
  , id
  , id_setor
  , nome
  , descricao
  , hora_criacao
  , ip
  , ativo
  , data_atualizacao_db
  )
  VALUES (
    e.id_estabelecimento
  , e."ID"
  , e."ID_Pavilhao"
  , e."Nome"
  , e."Descricao"
  , e."Hora_Criacao"
  , e."IP"
  , true
  , CURRENT_TIMESTAMP
  )
WHEN NOT MATCHED BY SOURCE
AND data_desativacao IS null
  THEN
  UPDATE
    SET
      ativo = false
    , data_desativacao = COALESCE(data_desativacao, CURRENT_TIMESTAMP)
    , data_atualizacao_db = CURRENT_TIMESTAMP;
DROP TABLE elipse.silver.temp_maquinas;
