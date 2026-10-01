-- Dimensão de tipo de melhoria + categoria (seed mel_categoria_melhorias).

select
    tipo_melhoria,
    categoria
from {{ ref('mel_categoria_melhorias') }}
