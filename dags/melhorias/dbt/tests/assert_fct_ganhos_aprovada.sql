-- FAP em fct_ganhos sem status 'Aprovado' em mel_aprovacao (ADR 0003). dt_fap
-- preenchido não prova aprovação: mel_ganhos.dt_fap vem cru do SharePoint (issue #24).

select distinct
    g.numero_fap,
    a.status
from {{ ref('fct_ganhos') }} as g
left join {{ ref('stg_mel_aprovacao') }} as a
    on g.numero_fap = a.numero_fap
where a.status is null or a.status <> 'Aprovado'
