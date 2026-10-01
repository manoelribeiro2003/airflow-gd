-- FAP com linha nas duas fontes de stg_mel_ganhos (ADR 0008). mel_ganhos_hist só pode
-- ter FAP sem nenhuma linha em mel_ganhos; se o bronze passar a ter a FAP, o ganho
-- dobraria. Correção: gerar a lista de FAPs de novo e recarregar mel_ganhos_hist
-- (dags/melhorias/scripts/ganhos_hist.py).
-- Exceção: FAP de mel_ganhos_fonte_planilha, que stg_mel_ganhos tira do bronze
-- (ADR 0013).

select distinct h.numero_fap
from {{ source('aux', 'mel_ganhos_hist') }} as h
inner join {{ source('bronze', 'mel_ganhos') }} as g
    on h.numero_fap = g.numero_fap
left join {{ ref('mel_ganhos_fonte_planilha') }} as fp
    on h.numero_fap = fp.numero_fap
where fp.numero_fap is null
