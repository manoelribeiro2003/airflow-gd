SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRY
  BEGIN TRANSACTION;

  --------------------------------------------------------------------------
  -- 1) UPDATE incremental
  --------------------------------------------------------------------------
  UPDATE T
  SET
    T.Tipo_melhoria = S.Tipo_melhoria
  , T.Filial = S.Filial
  , T.Fabrica = S.Fabrica
  , T.Setor = S.Setor
  , T.Nome_solicitante = S.Nome_solicitante
  , T.Numero_fap = S.Numero_fap2
  , T.Dt_fap = CAST(S.Dt_fap AS DATE)
  , T.Cod_prod = S.Cod_prod
  , T.Preco_mp = S.Preco_mp
  , T.Consumo_anterior = S.Consumo_anterior
  , T.Consumo_atual = S.Consumo_atual
  , T.Padrao_anterior = S.Padrao_anterior
  , T.Padrao_atual = S.Padrao_atual
  , T.Efetivo_anterior = S.Efetivo_anterior
  , T.Efetivo_atual = S.Efetivo_atual
  , T.Tc_anterior = S.Tc_anterior
  , T.Tc_atual = S.Tc_atual
  , T.Mix = S.Mix
  , T.Volume_mes_1 = S.Volume_mes_1
  , T.Volume_mes_2 = S.Volume_mes_2
  , T.Volume_mes_3 = S.Volume_mes_3
  , T.Volume_mes_4 = S.Volume_mes_4
  , T.Percentual_ganho = S.[_x0025__ganho]
  , T.Custo_par_anterior = S.Custo_par_anterior
  , T.Custo_par_atual = S.Custo_par_atual
  , T.Origem_melhoria = S.Origem_melhoria
  , T.Macro_setor = S.Macro_setor
  , T.Replicavel = S.Replicavel
  , T.Nome_setor_replicavel = S.Nome_setor_replicavel
  , T.Is_lacamento_manual = S.Is_lacamento_manual
  , T.Investimento = S.Investimento
  , T.Cracha_idealizador = S.Cracha_idealizador
  , T.Descricao_proc_atual_outras_m = S.Descricao_proc_atual_outras_m
  , T.Descricao_proc_prop_outras_m = S.Descricao_proc_prop_outras_m
  , T.Qtde_mo_atual_outras_m = S.Qtde_mo_atual_outras_m
  , T.Qtde_mo_proposto_outras_m = S.Qtde_mo_proposto_outras_m
  , T.Dt_fap_informada_por = S.Dt_fap_informada_por
  , T.Custo_mod = S.Salario_mod
  , T.Carga_horaria_mes = S.Carga_horaria_mes
  , T.Peso_ponderado_componente = S.Peso_ponderado_componente
  , T.Ganho_previsto = S.Ganho_previsto
  , T.Tipo_alteracao = S.Tipo_alteracao
  , T.Id_solicitacao_assinatura = S.Id_solicitacao_assinatura
  , T.Gerente = S.Gerente
  , T.Tipo_fap = S.Tipo_fap
  , T.Nome_idealizador = S.Nome_idealizador
  , T.Cc_idealizador = S.Cc_idealizador
  , T.Gerente_idealizador = S.Gerente_x0020_idealizador
  , T.Created = S.Created
  , T.Modified = S.Modified
  , T.Replicacao = S.[_x00c9__x0020_uma_x0020_replica_]
  , T.Volume_foi_editado = S.Volume_x0020_foi_x0020_editado
  , T.Cargo = S.Cargo
  , T.Status_liberacao = S.Status_x0020_de_x0020_libera_x00
  , T.Tipo_produto = S.Tipo_produto
  , T.Author = S.Author
  , T.Editor = S.Editor
  FROM [dbengenharia].[dbo].[mel_ganhos] AS T
    INNER JOIN [dbengenharia].[dbo].[stg_mel_ganhos] AS S
    ON T.Id = S.Id
  WHERE
    T.Modified <> S.Modified
    OR (T.Modified IS NULL AND S.Modified IS NOT NULL)
    OR (T.Modified IS NOT NULL AND S.Modified IS NULL);

    --------------------------------------------------------------------------
    -- 2) INSERT de novos registros
    --------------------------------------------------------------------------
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
  )
  SELECT
    S.Id
  , S.Tipo_melhoria
  , S.Filial
  , S.Fabrica
  , S.Setor
  , S.Nome_solicitante
  , S.Numero_fap2
  , CAST(S.Dt_fap AS DATE)
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
  , S.[_x0025__ganho]
  , S.Custo_par_anterior
  , S.Custo_par_atual
  , S.Origem_melhoria
  , S.Macro_setor
  , S.Replicavel
  , S.Nome_setor_replicavel
  , S.Is_lacamento_manual
  , S.Investimento
  , S.Cracha_idealizador
  , S.Descricao_proc_atual_outras_m
  , S.Descricao_proc_prop_outras_m
  , S.Qtde_mo_atual_outras_m
  , S.Qtde_mo_proposto_outras_m
  , S.Dt_fap_informada_por
  , S.Salario_mod
  , S.Carga_horaria_mes
  , S.Peso_ponderado_componente
  , S.Ganho_previsto
  , S.Tipo_alteracao
  , S.Id_solicitacao_assinatura
  , S.Gerente
  , S.Tipo_fap
  , S.Nome_idealizador
  , S.Cc_idealizador
  , S.Gerente_x0020_idealizador
  , S.Created
  , S.Modified
  , S.[_x00c9__x0020_uma_x0020_replica_]
  , S.Volume_x0020_foi_x0020_editado
  , S.Cargo
  , S.Status_x0020_de_x0020_libera_x00
  , S.Tipo_produto
  , S.Author
  , S.Editor
  FROM [dbengenharia].[dbo].[stg_mel_ganhos] AS S
  WHERE
    NOT EXISTS (
      SELECT 1
      FROM [dbengenharia].[dbo].[mel_ganhos] AS T
      WHERE
        T.Id = S.Id
    );

    --------------------------------------------------------------------------
    -- 3) DELETE de registros removidos da origem (janela de SHAREPOINT_SEARCH_DAYS dias)
    --    Linhas importadas via planilha (insert_manual = 1) nao existem no SharePoint
    --    e sao geridas pela DAG MANUAL_MELHORIAS_GANHOS_PLANILHA.
    --------------------------------------------------------------------------
  DELETE T
  FROM [dbengenharia].[dbo].[mel_ganhos] AS T
  WHERE
    T.Created >= DATEADD(DAY, -:search_days, GETDATE())
    AND T.Insert_manual = 0
    AND NOT EXISTS (
      SELECT 1
      FROM [dbengenharia].[dbo].[stg_mel_ganhos] AS S
      WHERE
        S.Id = T.Id
    );

  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0
    ROLLBACK TRANSACTION;
  THROW;
END CATCH;
