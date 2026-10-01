SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRY
  BEGIN TRANSACTION;

  --------------------------------------------------------------------------
  -- 1) Atualiza mel_aprovacao.dt_fap onde status = 'Aprovado' e dt_fap nulo
  --------------------------------------------------------------------------
  UPDATE [dbengenharia].[dbo].[mel_aprovacao]
  SET
    dt_fap = CAST(dt_aprovacao_eng AS DATE)
  WHERE
    1 = 1
    AND status = 'Aprovado'
    AND dt_fap IS NULL;

  --------------------------------------------------------------------------
  -- 2) Sincroniza mel_ganhos.dt_fap com a fonte da verdade (mel_aprovacao.dt_fap)
  --    Antes so preenchia nulos a partir de dt_aprovacao_eng. Problema: quando a
  --    dt_fap e recalculada/repopulada em mel_aprovacao (ex.: correcao de datas
  --    legadas), o ganho ja tinha uma data crua do SharePoint (nao-nula) e nunca
  --    era atualizado -> divergia do bimestre/competencia. Agora usa a.dt_fap
  --    (verdade) e sobrescreve sempre que diverge. numero_fap/id_solic dao a mesma
  --    cobertura; FAPs sem aprovacao mantem o dt_fap proprio.
  --------------------------------------------------------------------------
  UPDATE g
  SET
    g.dt_fap = CAST(a.dt_fap AS DATE)
  FROM [dbengenharia].[dbo].[mel_ganhos] AS g
    INNER JOIN [dbengenharia].[dbo].[mel_aprovacao] AS a
    ON g.id_solicitacao_assinatura = a.[ID]
  WHERE
    1 = 1
    AND a.status = 'Aprovado'
    AND a.dt_fap IS NOT NULL
    AND (g.dt_fap IS NULL OR g.dt_fap <> CAST(a.dt_fap AS DATE));

  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0
    ROLLBACK TRANSACTION;
  THROW;
END CATCH;
