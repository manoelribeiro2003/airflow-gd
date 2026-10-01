-- Limpeza 1:1 sobre mel_volume_real (volume real de produção por melhoria).
-- Grão: (numero_fap, cod_prod, mes_ano). mes_ano canônico 'MM/YYYY', já gravado nesse
-- formato pela DAG SILVER_MELHORIAS_VOLUME_REAL.

select
    numero_fap,
    cod_prod,
    mes_ano,
    volume,
    data_inicio,
    data_fim
from {{ source('silver', 'mel_volume_real') }}
