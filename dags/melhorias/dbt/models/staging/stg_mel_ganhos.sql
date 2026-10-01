-- Limpeza 1:1 sobre o bronze mel_ganhos + FAPs aprovadas cujo ganho só existe nas
-- planilhas do Qlik (aux mel_ganhos_hist, ADR 0008). As duas fontes são disjuntas por
-- numero_fap (teste assert_mel_ganhos_hist_disjunto); fonte diz de onde veio a linha.
-- FAPs do seed mel_ganhos_fonte_planilha têm linha no bronze, mas com o cadastro
-- incompleto ou diferente da planilha: as linhas do bronze saem e entram as do hist,
-- com os atributos da FAP (setor, idealizador...) do próprio bronze (ADR 0013).
-- mel_ganhos tem dt_fap nativo -> bimestre sai direto daqui, sem join com
-- aprovacao. Bimestre canônico 'mes1-mes2/ano' via seed mel_bimestre (month -> bimestre).
-- ganho_previsto do bronze é trocado pelo valor da planilha nas FAPs de mel_ganhos_ajuste
-- (cadastro ajustado só na planilha, ADR 0011).
-- macro_setor nulo (Crato 2021-2024, na maior parte) é preenchido pelo seed
-- mel_macro_setor (filial + setor), nas duas fontes; o valor cadastrado sempre ganha.
-- Sem macro setor a linha não acha carga horária em int_ganhos_calc (ADR 0012).

with bronze as (
    select
        'bronze' as fonte,
        g.id,
        g.id_solicitacao_assinatura,
        g.numero_fap,
        g.tipo_melhoria,
        g.tipo_fap,
        g.filial,
        g.fabrica,
        g.setor,
        coalesce(g.macro_setor, ms.macro_setor) as macro_setor,
        g.cod_prod,
        g.cracha_idealizador,
        g.nome_idealizador,
        g.cc_idealizador,
        g.gerente,
        g.gerente_idealizador,
        g.preco_mp,
        g.consumo_anterior,
        g.consumo_atual,
        g.tc_anterior,
        g.tc_atual,
        g.custo_par_anterior,
        g.custo_par_atual,
        g.mix,
        g.volume_mes_1,
        g.volume_mes_2,
        g.volume_mes_3,
        g.volume_mes_4,
        case
            when aj.numero_fap is not null then aj.ganho_previsto else g.ganho_previsto
        end as ganho_previsto,
        g.investimento,
        g.replicacao,
        g.origem_melhoria,
        g.cargo,
        cast(g.dt_fap as date) as dt_fap,
        g.created,
        g.modified
    from {{ source('bronze', 'mel_ganhos') }} as g
    left join {{ ref('mel_ganhos_ajuste') }} as aj
        on g.numero_fap = aj.numero_fap
    left join {{ ref('mel_macro_setor') }} as ms
        on g.filial = ms.filial
        and g.setor = ms.setor
    left join {{ ref('mel_ganhos_fonte_planilha') }} as fp
        on g.numero_fap = fp.numero_fap
    where fp.numero_fap is null
),

-- Atributos da FAP no SharePoint, para as FAPs cujo ganho vem da planilha (ADR 0013).
-- A planilha só é referência dos componentes do ganho (código, TC, consumo, custo par,
-- mix) e da data; setor e idealizador dela divergem do cadastro em parte dessas FAPs
-- (crachá que não é o do nome ao lado, mais de um setor na mesma FAP). Constantes por
-- FAP no bronze; max só colapsa as linhas.
bronze_fap as (
    select
        g.numero_fap,
        max(g.filial) as filial,
        max(g.setor) as setor,
        max(g.macro_setor) as macro_setor,
        max(g.cracha_idealizador) as cracha_idealizador,
        max(g.nome_idealizador) as nome_idealizador,
        max(g.gerente_idealizador) as gerente_idealizador,
        max(g.replicacao) as replicacao,
        max(g.origem_melhoria) as origem_melhoria,
        max(g.cargo) as cargo
    from {{ source('bronze', 'mel_ganhos') }} as g
    inner join {{ ref('mel_ganhos_fonte_planilha') }} as fp
        on g.numero_fap = fp.numero_fap
    group by g.numero_fap
),

aprovacao as (
    select
        id,
        numero_fap,
        tipo_fap,
        fabrica_melhoria,
        cracha_idealizador,
        nome_idealizador,
        cc_idealizador,
        gerente_melhoria,
        gerente_idealizador,
        -- ADR 0003 para FAP aprovada (única que entra no hist)
        cast(coalesce(dt_fap, dt_aprovacao_eng) as date) as dt_fap,
        created,
        modified
    from {{ source('bronze', 'mel_aprovacao') }}
),

-- Ganho e idealizador vêm da planilha; o que ela não tem sai de mel_aprovacao
-- (id_solicitacao_assinatura, tipo_fap, fabrica, gerente, cc, created/modified).
-- Sem volume previsto nem investimento: a planilha só traz o volume real, que fica em
-- mel_volume_real_hist (int_ganhos_calc). ganho_previsto só nos tipos sem volume
-- ("Ganho mês R$" da planilha, uma linha por FAP); nulo nos tipos com volume.
-- COLLATE: mel_aprovacao é Latin1 e o union all com mel_ganhos (UTF8) estoura
-- conflito de collation sem isto.
hist as (
    select
        'hist' as fonte,
        h.id,
        a.id as id_solicitacao_assinatura,
        h.numero_fap,
        h.tipo_melhoria,
        a.tipo_fap collate Latin1_General_100_CI_AS_SC_UTF8 as tipo_fap,
        coalesce(bf.filial, h.filial) as filial,
        a.fabrica_melhoria collate Latin1_General_100_CI_AS_SC_UTF8 as fabrica,
        coalesce(bf.setor, h.setor) as setor,
        coalesce(bf.macro_setor, h.macro_setor, ms.macro_setor) as macro_setor,
        h.cod_prod,
        coalesce(bf.cracha_idealizador, h.cracha_idealizador, a.cracha_idealizador)
            as cracha_idealizador,
        coalesce(
            bf.nome_idealizador,
            h.nome_idealizador,
            a.nome_idealizador collate Latin1_General_100_CI_AS_SC_UTF8
        ) as nome_idealizador,
        a.cc_idealizador collate Latin1_General_100_CI_AS_SC_UTF8 as cc_idealizador,
        a.gerente_melhoria collate Latin1_General_100_CI_AS_SC_UTF8 as gerente,
        coalesce(
            bf.gerente_idealizador,
            h.gerente_idealizador,
            a.gerente_idealizador collate Latin1_General_100_CI_AS_SC_UTF8
        ) as gerente_idealizador,
        h.preco_mp,
        h.consumo_anterior,
        h.consumo_atual,
        h.tc_anterior,
        h.tc_atual,
        h.custo_par_anterior,
        h.custo_par_atual,
        h.mix,
        cast(null as real) as volume_mes_1,
        cast(null as real) as volume_mes_2,
        cast(null as real) as volume_mes_3,
        cast(null as real) as volume_mes_4,
        h.ganho_previsto,
        cast(null as decimal(18, 2)) as investimento,
        coalesce(bf.replicacao, h.replicacao) as replicacao,
        coalesce(bf.origem_melhoria, h.origem_melhoria) as origem_melhoria,
        coalesce(bf.cargo, h.cargo) as cargo,
        coalesce(h.dt_fap, a.dt_fap) as dt_fap,
        a.created,
        a.modified
    from {{ source('aux', 'mel_ganhos_hist') }} as h
    left join aprovacao as a
        on h.numero_fap = a.numero_fap
    left join bronze_fap as bf
        on h.numero_fap = bf.numero_fap
    left join {{ ref('mel_macro_setor') }} as ms
        on coalesce(bf.filial, h.filial) = ms.filial
        and coalesce(bf.setor, h.setor) = ms.setor
),

ganhos as (
    select * from bronze
    union all
    select * from hist
)

select
    g.*,
    -- bimestre canônico (ADR 0003): mel_bimestre.bimestre + '/' + ano de dt_fap
    case
        when g.dt_fap is not null
            then b.bimestre + '/' + cast(year(g.dt_fap) as varchar(4))
    end as bimestre
from ganhos as g
left join {{ ref('mel_bimestre') }} as b
    on month(g.dt_fap) = b.mes
