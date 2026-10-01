-- FAP de mel_ganhos_hist que não está (mais) aprovada em mel_aprovacao (ADR 0008).
-- O hist só leva FAP aprovada; mudança de status no app exige recarregar a tabela.

select h.numero_fap
from {{ source('aux', 'mel_ganhos_hist') }} as h
left join {{ source('bronze', 'mel_aprovacao') }} as a
    on h.numero_fap = a.numero_fap
group by h.numero_fap
having max(case when a.status = 'Aprovado' then 1 else 0 end) = 0
