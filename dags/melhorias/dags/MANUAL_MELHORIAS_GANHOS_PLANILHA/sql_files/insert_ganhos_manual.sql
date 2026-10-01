SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRY
  BEGIN TRANSACTION;

  --------------------------------------------------------------------------
  -- 1) Reimportacao idempotente: remove as linhas manuais anteriores das FAPs
  --    presentes na planilha antes de inserir de novo.
  --------------------------------------------------------------------------
  DELETE T
  FROM [dbengenharia].[dbo].[mel_ganhos] AS T
  WHERE
    T.Insert_manual = 1
    AND EXISTS (
      SELECT 1
      FROM [dbengenharia].[dbo].[stg_mel_ganhos_manual] AS S
      WHERE
        S.Numero_fap = T.Numero_fap COLLATE DATABASE_DEFAULT
    );

  --------------------------------------------------------------------------
  -- 2) INSERT das linhas da planilha
  --    - Id: SharePoint usa ids positivos; linhas manuais recebem ids negativos
  --      decrescentes para nunca colidir (a lock evita corrida entre imports).
  --    - Colunas que a planilha nao traz vem da primeira linha da FAP vinda do
  --      SharePoint (insert_manual = 0, menor id).
  --    - Atributos de cabecalho da FAP (tipo_melhoria, filial, setor,
  --      nome_solicitante, dt_fap) tambem vem da linha base, ignorando a planilha:
  --      fct_ganhos agrupa por eles, entao divergencia duplicaria a FAP no grao
  --      (numero_fap, mes_offset). Setor da planilha tambem nao casa com o
  --      macro_setor, que so existe na linha base.
  --    - ganho_previsto fica nulo: e valor da FAP somado por linha em
  --      int_fap_resultado; copiar para cada linha multiplicaria o total.
  --    - (numero_fap, cod_prod) que ja existe no SharePoint e ignorado.
  --    - dt_fap e ressincronizado com mel_aprovacao pelo SILVER_MELHORIAS_DATA_FAP
  --      (disparado pelo Dataset desta DAG).
  --------------------------------------------------------------------------
  DECLARE @min_id INT = (
    SELECT ISNULL(MIN(G.Id), 0)
    FROM [dbengenharia].[dbo].[mel_ganhos] AS G WITH (UPDLOCK, HOLDLOCK)
    WHERE
      G.Id < 0
  );

  WITH base AS (
    SELECT
      B.*
    , ROW_NUMBER() OVER (PARTITION BY B.Numero_fap ORDER BY B.Id) AS Rn
    FROM [dbengenharia].[dbo].[mel_ganhos] AS B
    WHERE
      B.Insert_manual = 0
      AND EXISTS (
        SELECT 1
        FROM [dbengenharia].[dbo].[stg_mel_ganhos_manual] AS S
        WHERE
          S.Numero_fap = B.Numero_fap COLLATE DATABASE_DEFAULT
      )
  )

  INSERT INTO [dbengenharia].[dbo].[mel_ganhos] (
    Id
  , Tipo_melhoria
  , Filial
  , Fabrica
  , Setor
  , Nome_solicitante
  , Numero_fap
  , Dt_fap
  , Cod_prod
  , Preco_mp
  , Consumo_anterior
  , Consumo_atual
  , Padrao_anterior
  , Padrao_atual
  , Efetivo_anterior
  , Efetivo_atual
  , Tc_anterior
  , Tc_atual
  , Mix
  , Volume_mes_1
  , Volume_mes_2
  , Volume_mes_3
  , Volume_mes_4
  , Percentual_ganho
  , Custo_par_anterior
  , Custo_par_atual
  , Origem_melhoria
  , Macro_setor
  , Replicavel
  , Nome_setor_replicavel
  , Is_lacamento_manual
  , Investimento
  , Cracha_idealizador
  , Descricao_proc_atual_outras_m
  , Descricao_proc_prop_outras_m
  , Qtde_mo_atual_outras_m
  , Qtde_mo_proposto_outras_m
  , Dt_fap_informada_por
  , Custo_mod
  , Carga_horaria_mes
  , Peso_ponderado_componente
  , Ganho_previsto
  , Tipo_alteracao
  , Id_solicitacao_assinatura
  , Gerente
  , Tipo_fap
  , Nome_idealizador
  , Cc_idealizador
  , Gerente_idealizador
  , Created
  , Modified
  , Replicacao
  , Volume_foi_editado
  , Cargo
  , Status_liberacao
  , Tipo_produto
  , Author
  , Editor
  , Insert_manual
  )
  SELECT
    @min_id - ROW_NUMBER() OVER (ORDER BY S.Linha)
  , B.Tipo_melhoria
  , B.Filial
  , B.Fabrica
  , B.Setor
  , B.Nome_solicitante
  , S.Numero_fap
  , B.Dt_fap
  , S.Cod_prod
  , S.Preco_mp
  , S.Consumo_anterior
  , S.Consumo_atual
  , S.Padrao_anterior
  , S.Padrao_atual
  , S.Efetivo_anterior
  , S.Efetivo_atual
  , S.Tc_anterior
  , S.Tc_atual
  , S.Mix
  , S.Volume_mes_1
  , S.Volume_mes_2
  , S.Volume_mes_3
  , S.Volume_mes_4
  , S.Percentual_ganho
  , S.Custo_par_anterior
  , S.Custo_par_atual
  , B.Origem_melhoria
  , B.Macro_setor
  , B.Replicavel
  , B.Nome_setor_replicavel
  , B.Is_lacamento_manual
  , B.Investimento
  , B.Cracha_idealizador
  , B.Descricao_proc_atual_outras_m
  , B.Descricao_proc_prop_outras_m
  , B.Qtde_mo_atual_outras_m
  , B.Qtde_mo_proposto_outras_m
  , B.Dt_fap_informada_por
  , B.Custo_mod
  , B.Carga_horaria_mes
  , B.Peso_ponderado_componente
  , NULL
  , B.Tipo_alteracao
  , B.Id_solicitacao_assinatura
  , B.Gerente
  , B.Tipo_fap
  , B.Nome_idealizador
  , B.Cc_idealizador
  , B.Gerente_idealizador
  , B.Created
  , SYSDATETIME()
  , B.Replicacao
  , B.Volume_foi_editado
  , B.Cargo
  , B.Status_liberacao
  , B.Tipo_produto
  , B.Author
  , B.Editor
  , 1
  FROM [dbengenharia].[dbo].[stg_mel_ganhos_manual] AS S
    INNER JOIN base AS B
    ON
      B.Numero_fap COLLATE DATABASE_DEFAULT = S.Numero_fap
      AND B.Rn = 1
  WHERE
    NOT EXISTS (
      SELECT 1
      FROM [dbengenharia].[dbo].[mel_ganhos] AS G
      WHERE
        G.Insert_manual = 0
        AND G.Numero_fap COLLATE DATABASE_DEFAULT = S.Numero_fap
        AND G.Cod_prod COLLATE DATABASE_DEFAULT = S.Cod_prod
    );

  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0
    ROLLBACK TRANSACTION;
  THROW;
END CATCH;
