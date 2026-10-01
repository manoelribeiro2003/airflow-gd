-- Limpeza 1:1 sobre mel_volume_real_hist (volume real das planilhas BASE_LANCAMENTO do
-- Qlik, 2021-2025). Grão: (numero_fap, cod_prod, mes_offset). Offset 1 = mês de
-- dt_fap, 2 = mês seguinte (ADR 0007).

select
    numero_fap,
    cod_prod,
    mes_offset,
    volume,
    arquivo_origem
from {{ source('aux', 'mel_volume_real_hist') }}
