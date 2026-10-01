-- mel_ganhos_fonte_planilha tira a FAP do bronze em stg_mel_ganhos (ADR 0013). A FAP
-- precisa ter as linhas da planilha em mel_ganhos_hist: sem elas, some do dbt. Só vale
-- para tipo com ganho por volume; nos demais o ajuste é por mel_ganhos_ajuste (ADR
-- 0011). Correção: recarregar mel_ganhos_hist (dags/melhorias/scripts/ganhos_hist.py)
-- ou tirar a FAP do seed.

select
    fp.numero_fap,
    count(h.id) as linhas_hist,
    max(h.tipo_melhoria) as tipo_melhoria
from {{ ref('mel_ganhos_fonte_planilha') }} as fp
left join {{ source('aux', 'mel_ganhos_hist') }} as h
    on fp.numero_fap = h.numero_fap
group by fp.numero_fap
having count(h.id) = 0
    or min(
        case
            when h.tipo_melhoria in (
                N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
            ) then 1
            else 0
        end
    ) = 0
