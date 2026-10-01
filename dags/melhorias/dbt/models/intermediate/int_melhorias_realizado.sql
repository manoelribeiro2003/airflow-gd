-- Realizado de melhorias por (bimestre, crachá idealizador). Tabela central = meta;
-- este é o realizado que entra no fct_aderencia.
--
-- Definição de melhoria (regra confirmada): numero_fap classificada como 'Ganho'
-- (int_fap_resultado) E replicacao = 'Não'. Replicações não contam na quantidade.
-- ganho_total = soma de TODOS os ganhos por FAP no bimestre/idealizador, independente
-- de replicacao ou sinal (não compartilha o filtro da contagem).

with por_fap as (
    select
        g.bimestre,
        g.cracha_idealizador,
        g.numero_fap,
        max(g.nome_idealizador) as nome_idealizador,
        max(g.gerente_idealizador) as gerente_idealizador,
        -- COLLATE DATABASE_DEFAULT: replicacao e UTF8; o max() joga a precedencia pro
        -- default e o literal nao-N 'Não' (com acento) deixa de casar. Forca o default.
        max(g.replicacao) collate database_default as replicacao,
        max(r.resultado_fap) as resultado_fap,
        sum(g.ganho_reais) as ganho_fap
    from {{ ref('int_ganhos_long') }} as g
    left join {{ ref('int_fap_resultado') }} as r
        on g.numero_fap = r.numero_fap
    where g.bimestre is not null
    group by g.bimestre, g.cracha_idealizador, g.numero_fap
)

select
    bimestre,
    cracha_idealizador,
    max(nome_idealizador) as nome_idealizador,
    max(gerente_idealizador) as gerente_idealizador,
    -- quantidade: só FAPs nao-replicacao classificadas como Ganho
    count(distinct case
        when resultado_fap = 'Ganho' and replicacao = 'Não' then numero_fap
    end) as qtde_melhorias,
    -- ganho: soma tudo, independente de replicacao/sinal
    sum(ganho_fap) as ganho_total
from por_fap
group by bimestre, cracha_idealizador
