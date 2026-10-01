-- Linhas TC/Aglutinação de FAP aprovada com horas ganhas mas sem carga horária (nula
-- ou 0 nas duas fontes, ADR 0006). O ganho em pessoas/R$ dessas linhas vira 0; o warn
-- expõe o buraco para o negócio completar a planilha de carga (setor/macro setor).
{{ config(severity="warn") }}

select
    c.numero_fap,
    c.filial,
    c.setor,
    c.macro_setor,
    c.dt_fap,
    c.ch_mensal
from {{ ref('int_ganhos_calc') }} as c
inner join {{ ref('stg_mel_aprovacao') }} as a
    on c.numero_fap = a.numero_fap
where c.dt_fap is not null
    and a.status = 'Aprovado'
    and c.eh_tempo_ciclo = 1
    and coalesce(c.ch_mensal, 0) = 0
    and (
        {% for n in range(1, 5) %}
        c.hrs_ganhas_{{ n }} <> 0{{ " or" if not loop.last }}
        {% endfor %}
    )
