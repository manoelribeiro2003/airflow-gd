-- sqlfluff:dialect:tsql
MERGE INTO elipse.silver.oee_fciclos AS q
USING (
  SELECT
    *
  FROM stage.stage_ciclos
) AS o
ON
  q.data_hora = o."E3TimeStamp"
  AND q.id_equipamento = o.id_equipamento
  AND q.id_estabelecimento = o.id_estabelecimento
WHEN MATCHED AND (
  q.ciclo_atual IS DISTINCT FROM o."Ciclo Atual"
  OR q.ciclo_ti IS DISTINCT FROM o."Ciclo TI"
  OR q.diferenca IS DISTINCT FROM o."Diferenca"
  OR q.turno IS DISTINCT FROM o."Turno"
  OR q.programa IS DISTINCT FROM o."Programa"
  OR q.documento IS DISTINCT FROM o."Documento"
  OR q.numero_produto IS DISTINCT FROM o."NumeroProduto"
  OR q.efetivo IS DISTINCT FROM o."Efetivo"
  OR q.ferramental IS DISTINCT FROM o.ferramental
  OR q.cod_refer_matriz IS DISTINCT FROM o.cod_refer_matriz
  OR q.par_bat IS DISTINCT FROM o."ParBat"
)
  THEN UPDATE SET
    ciclo_atual = o."Ciclo Atual"
  , ciclo_ti = o."Ciclo TI"
  , diferenca = o."Diferenca"
  , turno = o."Turno"
  , programa = o."Programa"
  , documento = o."Documento"
  , numero_produto = o."NumeroProduto"
  , efetivo = o."Efetivo"
  , ferramental = o.ferramental
  , cod_refer_matriz = o.cod_refer_matriz
  , par_bat = o."ParBat"
  , data_atualizacao_db = CURRENT_TIMESTAMP
WHEN NOT MATCHED BY TARGET
  THEN INSERT (
    id_estabelecimento
  , id_equipamento
  , data_hora
  , ciclo_atual
  , ciclo_ti
  , diferenca
  , turno
  , programa
  , documento
  , numero_produto
  , efetivo
  , ferramental
  , cod_refer_matriz
  , par_bat
  , data_atualizacao_db
  )
  VALUES (
    o.id_estabelecimento::int2
  , o.id_equipamento::int4
  , o."E3TimeStamp"
  , o."Ciclo Atual"::float4
  , o."Ciclo TI"::float4
  , o."Diferenca"::float4
  , o."Turno"
  , o."Programa"::int4
  , o."Documento"::int2
  , o."NumeroProduto"
  , o."Efetivo"
  , o.ferramental
  , o.cod_refer_matriz
  , o."ParBat"::int2
  , CURRENT_TIMESTAMP
  )
WHEN NOT MATCHED BY SOURCE
AND q.data_hora >= (
  SELECT MIN("E3TimeStamp")
  FROM stage.stage_ciclos
) THEN DELETE;
