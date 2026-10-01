-- Limpeza 1:1 sobre o bronze mel_aprovacao.
-- Deriva dt_fap (antes feito via UPDATE in-place pela DAG SILVER_MELHORIAS_DATA_FAP):
-- quando aprovado e dt_fap nulo, usa dt_aprovacao_eng (ADR 0003: dt_fap = data mestra).
-- Bimestre canônico 'mes1-mes2/ano' derivado de dt_bimestre (data efetiva por status)
-- via seed mel_bimestre: Aprovado usa dt_fap; Em andamento usa data atual; Reprovado usa
-- a data da etapa que reprovou (ordem inmetro > analista > setor > especialista, fallback
-- created); demais usam created. Garante bimestre (e sk_idealizador) não-nulo p/ não-aprovados.

with aprovacao as (
    select
        id,
        numero_fap,
        numero_fap_pai,
        tipo_melhoria,
        tipo_fap,
        status,
        status_aprov_especialista,
        status_aprov_setor,
        status_aprov_analista,
        status_aprovador_inmetro,
        setor,
        gerente_melhoria,
        cracha_idealizador,
        nome_idealizador,
        cc_idealizador,
        gerente_idealizador,
        cargo_idealizador,
        dt_aprovacao_eng,
        dt_aprovacao_producao,
        dt_aprovacao_analista,
        dt_aprovacao_inmetro,
        dt_inicio_fluxo,
        eh_ganho,
        tipo_produto,
        ganho_previsto = cast(null as decimal(18, 2)),  -- placeholder: aprovacao não tem ganho_previsto
        created,
        modified,
        -- ADR 0003: data mestra
        cast(
            coalesce(dt_fap, case when status = 'Aprovado' then dt_aprovacao_eng end) as date
        ) as dt_fap,
        nome_especialista,
        nome_aprovador_setor
    from {{ source('bronze', 'mel_aprovacao') }}
),

com_dt_bimestre as (
    select
        a.*,
        -- data efetiva p/ bimestre por status (não altera dt_fap / ADR 0003):
        -- Aprovado usa dt_fap; Em andamento usa data atual; Reprovado usa a data da
        -- etapa que reprovou; demais usam created.
        cast(
            case
                when a.status = 'Aprovado' then a.dt_fap
                when a.status = 'Em andamento' then getdate()
                when a.status = 'Reprovado'
                    then coalesce(
                            case
                                when a.status_aprovador_inmetro = 'Reprovado'
                                    then a.dt_aprovacao_inmetro
                                when a.status_aprov_analista = 'Reprovado'
                                    then a.dt_aprovacao_analista
                                when a.status_aprov_setor = 'Reprovado'
                                    then a.dt_aprovacao_producao
                                when a.status_aprov_especialista = 'Reprovado'
                                    then a.dt_aprovacao_eng
                            end,
                            a.created
                        )
                else a.created
            end as date
        ) as dt_bimestre
    from aprovacao as a
)

select
    c.*,
    case
        when c.dt_bimestre is not null
            then b.bimestre + '/' + cast(year(c.dt_bimestre) as varchar(4))
    end as bimestre
from com_dt_bimestre as c
left join {{ ref('mel_bimestre') }} as b
    on month(c.dt_bimestre) = b.mes
