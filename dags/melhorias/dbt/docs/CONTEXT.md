# CONTEXT — Melhorias (migração Qlik → SQL + dbt)

Glossário do domínio de Melhorias (Indicador de Melhorias / Aderência / Ganhos).
Apenas termos de negócio. Decisões de implementação vão em `docs/adr/`.
Linhagem dos dados (diagramas Mermaid source → marts): [`docs/lineage.md`](lineage.md).

## Termos

### Melhoria
Proposta de melhoria de processo registrada pela engenharia. Identificada por um
**Nº F.A.P**. Tem um **Idealizador**, um **Tipo de Melhoria** e gera **Ganho**.
O fato `fct_melhoria` a resume no grão 1 linha/FAP (aprovação + ganho agregado),
para consumo direto no Power BI.

### FAP (Nº F.A.P)
Ficha de Alteração de Processo. Identificador de negócio de uma Melhoria.
Uma FAP passa por um fluxo de **Aprovação**.

### FAO (Nº F.A.P)
Ficha de Aproveitamento de Obsoleto. Identificador de negócio de uma Melhoria de aproveitamento de material obsoleto (parado mais de 30 dias em estoque).
Uma FAO passa por um fluxo de **Aprovação**.

### Aprovação / Assinatura
Fluxo de aprovação de uma Melhoria (especialista, setor, analista, gerência eng,
inmetro). Origem: lista SharePoint `Coletar_Assinaturas` → tabela `mel_aprovacao`.
`Status = 'Aprovado'` + `dt_aprovacao_eng` definem quando a melhoria conta.

### Ganho
Resultado financeiro/produtivo de uma Melhoria. Três tipos mutuamente exclusivos:
- **Tempo Ciclo (TC)** — horas ganhas → pessoas → R$ via custo do funcionário.
- **Aglutinação** — Mesmo que **TC**.
- **Consumo** — economia de matéria-prima (Cons_Anterior - Cons_Atual).
- **Troca de Matéria Prima (Troca MP)** — diferença de custo par.
- **Outros tipos** — O ganho fica em `Ganho mês R$` e `mel_ganhos.ganho_previsto`
Origem: lista SharePoint `Melhorias` → tabela `mel_ganhos`. FAPs aprovadas de 2021-2025
que nunca tiveram linha em `mel_ganhos` entram pelas planilhas `BASE_LANCAMENTO` do Qlik
(`mel_ganhos_hist`); uma FAP vem de uma fonte ou da outra, nunca das duas. Ver `adr/0008`.
FAP de TC, Consumo ou Troca MP com cadastro incompleto ou divergente da planilha (seed
`mel_ganhos_fonte_planilha`) sai do bronze e usa as linhas da planilha; os atributos da
FAP continuam os do SharePoint. Ver `adr/0013`.

### Volume de produção (real)
Volume real produzido por **data**, **local de produção** e **produto/componente**,
exportado pelo Qlik SaaS como `.parquet` no SharePoint. A DAG
`SILVER_MELHORIAS_VOLUME_REAL` ingere o parquet e atribui o volume a cada melhoria por
`numero_fap` + `cod_prod` na janela `[dt_fap, dt_fap + 30 dias]`, particionado por
`mes_ano` ('MM/YYYY'), somando o volume por local válido (locais em
`mel_local_producao_volume_desconsiderados` são excluídos para resolver duplicação entre
locais). **Só existe volume para melhorias dos tipos Tempo Ciclo, Aglutinação, Consumo e
Troca de Matéria Prima**; os demais tipos ("Outros") usam `ganho_previsto` fixo e não
entram em `mel_volume_real`. Resultado em `mel_volume_real`. **Substitui** o volume estimado
(`mel_ganhos.volume_mes_1..4`) no cálculo de **Ganho** (`int_ganhos_calc`); melhoria sem
linha de volume real conta zero naquele mês. Range recomputado é configurável via Airflow
Variable `MEL_VOLUME_REAL_MONTHS` (default 3 meses).

`mel_volume_real` só começa em 2025-05. Para competências anteriores ao corte
`volume_hist_ate` (2026-01) o volume vem de `mel_volume_real_hist`: o volume das
planilhas `BASE_LANCAMENTO` que alimentavam o Qlik, por FAP + código + offset (1 = mês de
dt_fap, 2 = mês seguinte). Ver `adr/0007`. A reconciliação desse histórico contra o
Qlik, com as diferenças que sobram explicadas por FAP, está em
[`reconciliacao-qlik-2021-2025.md`](reconciliacao-qlik-2021-2025.md).

### Meta
Alvo de melhorias por **Gerente** e **Bimestre**. Define quem é **Elegível**
(`Grupo Cargo` <> 'Não Elegível' E `Categoria Situação` = 'Considera').
Origem: planilha de metas → tabela `mel_meta_aderencia`.

### Aderência
Indicador que compara o **Realizado** (melhorias por idealizador/gerente) contra a
**Meta** do bimestre. É o KPI central do dashboard. Exemplo: meta 1 fez 1 melhoria, meta ok, meta 1 fez 'n' melhorias, meta ok.

### Em andamento
Melhoria com `status = 'Em andamento'` (ainda não aprovada). **Não** entra nos fatos
de aprovadas (`fct_ganhos`, `fct_aderencia`); vive num fato próprio
`fct_melhorias_em_andamento` (pipeline), referenciada por `Criado` em vez de `dt_fap`.
Carrega `status` do fluxo e os status/nomes dos aprovadores de cada etapa. Decisão
consciente: KPI principal só conta aprovadas.

### Data da FAP (dt_fap)
**Data mestra** da Melhoria — quando a melhoria "conta". Deriva de
`dt_aprovacao_eng` (`status='Aprovado'`). É o único link temporal dos fatos com
`dim_calendario` (ganhos e aderência). Unifica o que o Qlik espalhava em "Data da
FAP" (ganhos) e "Data para Meta" (aderência).

### Idealizador
Colaborador que registra a Melhoria. Identidade = **(Bimestre, Crachá)**, não só
crachá: gerente, cargo, grupo de cargo e elegibilidade variam por bimestre. Um
idealizador por bimestre. Chave equivalente ao `%ChaveCodigoBimestre` do Qlik.
No gold essa identidade composta vira a chave surrogate `sk_idealizador`
(`bimestre|crachá`) — coluna única de relação do Power BI (import só relaciona por
1 coluna): `dim_idealizador` é a dimensão-ponte (PK) e os fatos `fct_aderencia`/
`fct_ganhos` referenciam por ela (FK).

### Bimestre
Grão temporal central. 6 bimestres/ano (jan-fev, mar-abr, …, nov-dez).
Identificado como `'mes1-mes2/ano'` (ex. `jan-fev/2026`) — formato do Qlik. Derivado
da data via tabela `mel_bimestre`: `month(data) → mel_bimestre.bimestre`, concatenado
com o ano. Vem de `dt_fap` (ganhos/aprovacao) ou `inicio_bimestre` (meta). Não há
mais "bimestre corrente" pinado por config — gold reconstrói todo histórico; Power BI fatia.

### Gerente
Responsável por uma área. Sofre **remapeamento** (Qlik tinha cadeia de if's:
Andre Miorelli→Andre - F4, etc.) e join com tabela de áreas (`gerentes`).

### Elegível
Flag derivada na Meta: colaborador conta para aderência quando `Grupo Cargo` é
elegível e `Categoria Situação` = 'Considera'.

## Camadas (medallion → SQL Server dbengenharia, schema dbo)

- **Bronze**: ingestão crua do SharePoint (`mel_aprovacao`, `mel_ganhos`). Source
  imutável; dbt não escreve aqui. Ingerida pelas DAGs Airflow.
- **Silver**: limpeza/derivações como VIEWS dbt (ex.: derivar `dt_fap` em vez de
  UPDATE in-place). Também inclui tabelas materializadas por DAGs Airflow (não-dbt),
  ex.: `mel_volume_real` (volume real por melhoria), lida pelo dbt como source `silver`.
- **Gold**: fatos (`fct_ganhos`, `fct_aderencia`, `fct_melhorias_em_andamento`) + dims conformes
  (`dim_calendario`, `dim_gerente`, `dim_idealizador`, `dim_tipo_melhoria`), tudo
  como VIEWS, consumido pelo Power BI em modo import. Ver `adr/0001`.

## Tabelas auxiliares

Todas carregadas manualmente no SQL Server (sem DAG); o dbt só as lê. Dois grupos:

- **Mapeamentos estáticos** (CSV versionado em `seeds/` como referência/contrato de
  schema; tabelas com prefixo `mel_`): `mel_gerente_remap` + `mel_gerente_area`
  (remap + área), `mel_categoria_melhorias` (tipo→categoria), `mel_bimestre`
  (mês→bimestre), `mel_ganhos_ajuste` (ganho corrigido pela planilha, `adr/0011`),
  `mel_macro_setor` (setor→macro setor quando o cadastro não tem, `adr/0012`),
  `mel_ganhos_fonte_planilha` (FAPs cujo ganho vem da planilha, `adr/0013`). **Não**
  são mais carregados via `dbt seed`: as tabelas `dbo.mel_*`
  são criadas/populadas à mão (DBeaver/SQL). Os `ref()` dos models resolvem para essas
  tabelas; o build roda com `--exclude resource_type:seed`. Ver `adr/0004`.
- **Populadas via planilha + VBA** (direto no SQL Server): `mel_meta_aderencia` (por
  bimestre), `mel_carga_horaria` (mensal), `mel_custo_funcionario` (mensal). O negócio
  mantém via planilha/VBA; dbt só as declara como `sources` e lê.
- **Gerada por script a partir de planilha do Qlik**: `mel_carga_horaria_macro`
  (mensal, estabelecimento + macro setor), SQL gerado por
  `dags/melhorias/scripts/carga_horaria_macro.py` e executado à mão. Ver `adr/0006`.
  Idem `mel_volume_real_hist` (volume real 2021-2025 das planilhas `BASE_LANCAMENTO`),
  gerado por `dags/melhorias/scripts/volume_real_hist.py`. Ver `adr/0007`. E
  `mel_ganhos_hist` (ganho das FAPs aprovadas ausentes de `mel_ganhos` e das FAPs de
  `mel_ganhos_fonte_planilha`), gerado por `dags/melhorias/scripts/ganhos_hist.py`. Ver
  `adr/0008` e `adr/0013`.

A primeira entrega (decisão: tudo de uma vez — 3 fatos + dims) **depende** das
aux populadas; o `dbt build` só fecha com as tabelas auxiliares e as sources ingeridas.
