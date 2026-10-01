-- mel_ganhos.insert_manual: marca linhas importadas via planilha pela DAG
-- MANUAL_MELHORIAS_GANHOS_PLANILHA (FAPs com linhas demais para a lista do SharePoint).
--
-- 0 = linha vinda do SharePoint (BRONZE_MELHORIA_GANHOS), 1 = linha manual.
-- Linhas manuais recebem id negativo (SharePoint usa ids positivos) e sao ignoradas
-- pelo DELETE do merge_ganhos.sql.
--
-- Aplicar ANTES de subir a nova versao do merge_ganhos.sql (ele referencia a coluna).

ALTER TABLE dbengenharia.dbo.mel_ganhos
ADD insert_manual bit NOT NULL
CONSTRAINT DF_mel_ganhos_insert_manual DEFAULT 0;

-- Rollback (so depois de remover as linhas manuais e reverter o merge_ganhos.sql):
-- DELETE FROM dbengenharia.dbo.mel_ganhos WHERE insert_manual = 1;
-- ALTER TABLE dbengenharia.dbo.mel_ganhos DROP CONSTRAINT DF_mel_ganhos_insert_manual;
-- ALTER TABLE dbengenharia.dbo.mel_ganhos DROP COLUMN insert_manual;
