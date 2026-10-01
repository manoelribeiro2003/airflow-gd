-- ADR 0005: tabela com clustered columnstore (as_columnstore default). Extração
-- instantânea no refresh do Power BI; lê int_ganhos_long já materializado.
{{ config(materialized="table") }}

-- Fato de ganhos LONG: uma linha por (FAP, mês de competência 1..4). ADR 0003.
-- ganho_reais (R$) convertido por tipo em int_ganhos_long. Chaveado em
-- (bimestre, crachá) para relacionar com a meta no Power BI.
--
-- int_ganhos_long está no grão de COMPONENTE: mel_ganhos tem uma linha por Id
-- (cod_prod/componente) da FAP, então cada mês aparece N vezes (1 com valor, demais
-- zeradas). O Qlik base_melhoria soma os componentes por FAP (sum em ganho_melhorias.md).
-- Aqui colapsamos com group by + sum para uma linha por (FAP, mês).

select
    numero_fap,
    id_solicitacao_assinatura,
    tipo_melhoria,
    filial,
    setor,
    macro_setor,
    cracha_idealizador,
    nome_idealizador,
    gerente_idealizador,
    bimestre,
    concat(trim(bimestre), '|', cast(cracha_idealizador as varchar(20))) collate database_default
        as sk_idealizador,
    replicacao,
    mes_offset,
    dt_competencia,
    sum(hrs_ganhas) as hrs_ganhas,
    sum(ganho_reais) as ganho_reais,
    sum(ganho_pessoas) as ganho_pessoas
from {{ ref('int_ganhos_long') }}
where dt_competencia is not null
group by
    numero_fap,
    id_solicitacao_assinatura,
    tipo_melhoria,
    filial,
    setor,
    macro_setor,
    cracha_idealizador,
    nome_idealizador,
    gerente_idealizador,
    bimestre,
    concat(trim(bimestre), '|', cast(cracha_idealizador as varchar(20))) collate database_default,
    replicacao,
    mes_offset,
    dt_competencia
