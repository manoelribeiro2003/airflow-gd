-- Migração one-off: trocar a PK de dbengenharia.dbo.mel_volume_real.
--   ANTES: id int IDENTITY(1,1) PRIMARY KEY + índice NC não-único
--          mel_volume_real_numero_fap_IDX (numero_fap, cod_prod, mes_ano).
--   DEPOIS: PK natural composta (numero_fap, cod_prod, mes_ano); coluna id removida;
--           índice NC removido (redundante com a PK clustered).
--
-- Motivo: id era surrogate não-referenciado. A chave de negócio é a tripla; promovê-la
-- a PK garante unicidade no banco (o índice NC era não-único) e simplifica o schema.
-- Idempotência do merge preservada (delete-by-range + insert; data_inicio determinístico
-- por chave). Ver SILVER_MELHORIAS_VOLUME_REAL/sql_files/merge_volume_real.sql.
--
-- Executar uma única vez contra dbengenharia (SQL Server 2019).

SET XACT_ABORT ON;

-- 0) Pré-check: NÃO deve haver duplicatas na chave natural antes de criar a PK.
--    Se retornar linhas, deduplicar manualmente antes de prosseguir.
SELECT numero_fap, cod_prod, mes_ano, COUNT(*) AS qt
FROM dbengenharia.dbo.mel_volume_real
GROUP BY numero_fap, cod_prod, mes_ano
HAVING COUNT(*) > 1;

BEGIN TRANSACTION;

-- 1) Dropar a PK atual (id)
ALTER TABLE dbengenharia.dbo.mel_volume_real
  DROP CONSTRAINT mel_volume_real_pk;

-- 2) Dropar a coluna surrogate
ALTER TABLE dbengenharia.dbo.mel_volume_real
  DROP COLUMN id;

-- 3) Dropar o índice NC (redundante: a nova PK clustered já lidera por essas colunas)
DROP INDEX mel_volume_real_numero_fap_IDX ON dbengenharia.dbo.mel_volume_real;

-- 4) Criar a PK composta (clustered por default). Colunas já são NOT NULL.
ALTER TABLE dbengenharia.dbo.mel_volume_real
  ADD CONSTRAINT mel_volume_real_pk
  PRIMARY KEY (numero_fap, cod_prod, mes_ano);

COMMIT TRANSACTION;
