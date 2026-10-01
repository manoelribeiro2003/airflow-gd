-- Pipeline: melhorias em andamento (status = 'Em andamento'). ADR 0003: fora dos
-- fatos de aprovadas. Referenciada por created (não dt_fap). Carrega status do fluxo.

select
    id,
    numero_fap,
    tipo_melhoria,
    status,
    status_aprov_especialista,
    status_aprov_setor,
    status_aprov_analista,
    status_aprovador_inmetro,
    setor,
    gerente_idealizador,
    cracha_idealizador,
    nome_idealizador,
    created as dt_referencia,
    dt_inicio_fluxo,
    nome_especialista,
    nome_aprovador_setor
from {{ ref('stg_mel_aprovacao') }}
where status = 'Em andamento'
