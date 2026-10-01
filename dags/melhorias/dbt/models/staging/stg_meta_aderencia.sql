-- Limpeza 1:1 sobre mel_meta_aderencia (meta por gerente/bimestre + roster RH).
-- Tabela CENTRAL: grão (bimestre, codigo/crachá). Deriva flag elegivel (Qlik: Grupo
-- Cargo <> 'Não Elegível' E Categoria = 'Considera') e o bimestre canônico
-- 'mes1-mes2/ano' a partir de inicio_bimestre (seed mel_bimestre). O bimestre de
-- origem é preservado como bimestre_origem.

with meta as (
    select
        bimestre as bimestre_origem,
        inicio_bimestre,
        fim_bimestre,
        gerente_meta,
        gerente_c_custo,
        atende_somente_um_gerente,
        grupo_cargo,
        categoria_situacao,
        descricao_situacao,
        setor_pnope,
        codigo,
        nome,
        setor,
        c_custo,
        cargo,
        situacao,
        -- Meta fixa: cada elegível deve fazer 1 melhoria/bimestre (CONTEXT: "meta 1
        -- fez 1, meta ok"). mel_meta_aderencia não carrega quantidade.
        cast(1 as int) as qtde,
        case
            when grupo_cargo <> 'Não Elegível' and categoria_situacao = 'Considera'
                then cast(1 as bit)
            else cast(0 as bit)
        end as elegivel
    from {{ source('aux', 'mel_meta_aderencia') }}
)

select
    m.*,
    case
        when m.inicio_bimestre is not null
            then b.bimestre + '/' + cast(year(m.inicio_bimestre) as varchar(4))
    end as bimestre
from meta as m
left join {{ ref('mel_bimestre') }} as b
    on month(m.inicio_bimestre) = b.mes
