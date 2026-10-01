# ADR = Architecture Decision Record.

# 0004 — Seeds carregados manualmente no SQL Server (não via dbt)

- Status: aceito
- Data: 2026-06-03

## Contexto

O projeto tinha 4 tabelas auxiliares estáticas como seeds dbt (CSV versionado em
`seeds/`): `mel_gerente_remap`, `mel_gerente_area`, `mel_categoria_melhorias`,
`mel_bimestre`. A DAG `GOLD_MELHORIAS_DBT` rodava `dbt seed` antes do `dbt build`.

Na prática essas tabelas são mantidas pelo negócio, igual às demais aux já populadas
fora do dbt e declaradas só como `sources` (`mel_meta_aderencia`, `mel_carga_horaria`,
`mel_custo_funcionario`). Carregar metade das aux por seed e a outra metade à mão gera
dois fluxos para o mesmo tipo de dado. Optou-se por unificar: tudo manual no SQL Server.

Restrição técnica: os models referenciam os seeds via `ref()`
(`stg_mel_aprovacao`, `stg_mel_ganhos`, `stg_meta_aderencia` → `ref('mel_bimestre')`;
`int_gerente_remap` → `ref('mel_gerente_remap')` + `ref('mel_gerente_area')`;
`dim_tipo_melhoria` → `ref('mel_categoria_melhorias')`). Os nós de seed precisam
continuar existindo no grafo, senão o `ref()` quebra no parse.

## Decisão

As tabelas `dbo.mel_*` auxiliares passam a ser criadas e populadas manualmente no
SQL Server (via DBeaver/SQL) quando necessário. O dbt deixa de gerenciá-las:

- A task `dbt_seed` da DAG fica comentada e sai da cadeia
  (`start >> dbt_deps >> dbt_build >> end`).
- O build roda com `dbt build --exclude resource_type:seed`, para não recarregar os
  CSVs (`dbt build` roda seed por padrão).
- O bloco `seeds:` em `dbt_project.yml` fica comentado. **Não** se usa `+enabled: false`:
  isso removeria os nós do grafo e quebraria o `ref()`. Com os seeds habilitados mas
  excluídos do build, o `ref('mel_bimestre')` etc. resolve para a relação
  `dbo.mel_bimestre` criada à mão.

Os CSVs em `seeds/` e o `seeds/_seeds.yml` permanecem versionados, como referência do
dado e contrato de schema (tipos das colunas).

## Consequências

- Um único fluxo para tabelas auxiliares (todas manuais no SQL Server).
- Pré-requisito operacional: as 4 tabelas `dbo.mel_*` precisam existir e estar
  populadas antes do `dbt build`, senão os models que as referenciam falham em runtime.
- `dbt seed` ainda funciona se rodado à mão (os arquivos seguem no projeto), mas não faz
  parte da orquestração.
- Reativar é simples: descomentar a task `dbt_seed`, recolocá-la na cadeia, tirar o
  `--exclude resource_type:seed` do build e descomentar o bloco `seeds:`.

## Alternativas consideradas

- **Converter os seeds em `sources`** e trocar os `ref()` por `source()` nos models:
  alinharia conceitualmente com as outras aux, mas é refator maior nos models e perde os
  CSVs como referência versionada. Preferiu-se manter os nós de seed e só não executá-los.
- **`+enabled: false` nos seeds**: removeria os nós do grafo e quebraria o `ref()` no
  parse. Inviável sem antes migrar os models para `source()`.
