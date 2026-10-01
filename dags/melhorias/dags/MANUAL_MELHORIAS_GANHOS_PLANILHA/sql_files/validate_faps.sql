-- Resumo por FAP da planilha carregada em stg_mel_ganhos_manual.
-- Aprovacoes: linhas 'Aprovado' em mel_aprovacao (precisa ser >= 1).
-- Linhas_base: linhas vindas do SharePoint (insert_manual = 0); a primeira delas
-- fornece as colunas que a planilha nao traz (precisa ser >= 1).
-- Linhas_sobrepostas: linhas da planilha cujo (numero_fap, cod_prod) ja existe no
-- SharePoint; sao ignoradas no insert (vale o valor do SharePoint).
-- *_planilha x *_base: atributos de cabecalho da FAP. O insert usa sempre os da linha
-- base; divergencia so vira aviso no log, para a area corrigir a planilha.
-- COLLATE: o staging usa a collation default do banco, mel_ganhos usa UTF8.
WITH planilha AS (
  SELECT
    S.Numero_fap
  , S.Tipo_melhoria
  , S.Filial
  , S.Setor
  , CASE
      WHEN EXISTS (
        SELECT 1
        FROM [dbengenharia].[dbo].[mel_ganhos] AS G
        WHERE
          G.Insert_manual = 0
          AND G.Numero_fap COLLATE DATABASE_DEFAULT = S.Numero_fap
          AND G.Cod_prod COLLATE DATABASE_DEFAULT = S.Cod_prod
      ) THEN 1
      ELSE 0
    END AS Sobreposta
  FROM [dbengenharia].[dbo].[stg_mel_ganhos_manual] AS S
)

, resumo AS (
  SELECT
    P.Numero_fap
  , COUNT(*) AS Linhas_planilha
  , SUM(P.Sobreposta) AS Linhas_sobrepostas
  , MIN(P.Tipo_melhoria) AS Tipo_melhoria_planilha
  , MIN(P.Filial) AS Filial_planilha
  , MIN(P.Setor) AS Setor_planilha
  FROM planilha AS P
  GROUP BY P.Numero_fap
)

SELECT
  R.Numero_fap
, R.Linhas_planilha
, R.Linhas_sobrepostas
, (
  SELECT COUNT(*)
  FROM [dbengenharia].[dbo].[mel_aprovacao] AS A
  WHERE
    A.Numero_fap COLLATE DATABASE_DEFAULT = R.Numero_fap
    AND A.Status = 'Aprovado'
) AS Aprovacoes
, (
  SELECT COUNT(*)
  FROM [dbengenharia].[dbo].[mel_ganhos] AS G
  WHERE
    G.Numero_fap COLLATE DATABASE_DEFAULT = R.Numero_fap
    AND G.Insert_manual = 0
) AS Linhas_base
, (
  SELECT COUNT(*)
  FROM [dbengenharia].[dbo].[mel_ganhos] AS G
  WHERE
    G.Numero_fap COLLATE DATABASE_DEFAULT = R.Numero_fap
    AND G.Insert_manual = 1
) AS Linhas_manuais_atuais
, R.Tipo_melhoria_planilha
, R.Filial_planilha
, R.Setor_planilha
, B.Tipo_melhoria AS Tipo_melhoria_base
, B.Filial AS Filial_base
, B.Setor AS Setor_base
FROM resumo AS R
  OUTER APPLY (
    SELECT TOP 1
      G.Tipo_melhoria
    , G.Filial
    , G.Setor
    FROM [dbengenharia].[dbo].[mel_ganhos] AS G
    WHERE
      G.Numero_fap COLLATE DATABASE_DEFAULT = R.Numero_fap
      AND G.Insert_manual = 0
    ORDER BY G.Id
  ) AS B
ORDER BY R.Numero_fap;
