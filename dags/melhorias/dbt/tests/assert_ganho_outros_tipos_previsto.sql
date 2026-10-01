-- FAP aprovada de tipo fora de volume (Manutenção, GGF, Administrativas...) cujo
-- ganho_reais do mês 1 diverge do ganho_previsto cadastrado. A planilha (R$ Mês) usa
-- o ganho_previsto em qualquer setor; o setor Ting% já zerou essas FAPs (issue #23).
--
-- Tolerância relativa: ganho_reais sai do case como real (float32, ~7 dígitos), então
-- R$ 980.056,10 vira 980.056,125. Corte fixo em centavos acusaria esse arredondamento.

with calc as (
    select
        c.numero_fap,
        sum(coalesce(c.ganho_previsto, 0)) as ganho_previsto
    from {{ ref('int_ganhos_calc') }} as c
    inner join {{ ref('stg_mel_aprovacao') }} as a
        on c.numero_fap = a.numero_fap
    where c.dt_fap is not null
        and a.status = 'Aprovado'
        and c.tipo_melhoria not in (
            N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
        )
    group by c.numero_fap
),

realizado as (
    select
        numero_fap,
        sum(coalesce(ganho_reais, 0)) as ganho_reais
    from {{ ref('int_ganhos_long') }}
    where mes_offset = 1
        and tipo_melhoria not in (
            N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
        )
    group by numero_fap
)

select
    c.numero_fap,
    c.ganho_previsto,
    r.ganho_reais
from calc as c
left join realizado as r
    on c.numero_fap = r.numero_fap
where abs(c.ganho_previsto - coalesce(r.ganho_reais, 0))
    > 0.01 + abs(c.ganho_previsto) * 1e-6
