-- Grão de mel_ganhos_hist (ADR 0008). Tipos sem volume: uma linha por FAP, porque o
-- ganho_previsto é da FAP e uma linha repetida somaria de novo. Tipos com volume: sem
-- ganho_previsto, porque o ganho sai do volume real (int_ganhos_calc).

select
    numero_fap,
    tipo_melhoria,
    count(*)              as linhas,
    count(ganho_previsto) as linhas_com_ganho_previsto
from {{ source('aux', 'mel_ganhos_hist') }}
group by numero_fap, tipo_melhoria
having
    (
        tipo_melhoria not in (
            N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
        )
        and count(*) > 1
    )
    or (
        tipo_melhoria in (
            N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
        )
        and count(ganho_previsto) > 0
    )
