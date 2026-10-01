## Váriaveis
```qlik
//############### Caminhos arquivos #####################
//SET vPathFile   	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/$1.xls?;
SET vPathFile   	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;
SET vPathFato   	=lib://QVD - QlikView - Prd/Engenharia/Portal_Engenharia_NE/$1.qvd;
SET vPathFileOPE    =lib://QVD - QlikSense - Prd/Engenharia_NE/OPE/$1.qvd;

//SET vPathFileMeta 		=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/metas/$1.xlsx;
//SET vPathFileMelhorias 	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileMeta 		=lib://Arquivos - ENG SOB/Melhorias/metas/$1.xlsx;
SET vPathFileMelhorias 	=lib://Arquivos - ENG SOB/Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileQualidadeIndicadores 	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;

//CONFIG
//############### configurações para os graficos #####################
SET vConsumo = 'Consumo';
SET vTC = 'Tempo Ciclo';
SET vTrocaMP = 'Troca de Matéria Prima';
SET vNumFormat = '#.##0,00';
SET vQtdeDiasPegarMelhorias = 365;
LET vAnoAtual = text(Year(Today() - 4));



Tbl_Config:
LOAD
    Key,
    Value
FROM [$(vPathFile(script.aderencia.config))]
(ooxml, embedded labels, table is Planilha1);



LET vBimestre = Lookup('Value', 'Key', 'Bimestre');
LET vAnoAtual = Text(Lookup('Value', 'Key', 'Ano para puxar os dados'));


// LET vAnoAtual = Text(2026);
// Let vBimestre = '$(vAnoAtual)' & '_Bimestre_1'; //Lookup('Value', 'Key', 'Bimestre');

Drop Table Tbl_Config;

```


## Load Meta (table mel_meta_aderencia)
```qlik
tbl_bimestre:
load * Inline [
  "Mês", Bimestre
  1,jan-fev
  2,jan-fev
  3,mar-abr
  4,mar-abr
  5,mai-jun
  6,mai-jun
  7,jul-ago
  8,jul-ago
  9,set-out
  10,set-out
  11,nov-dez
  12,nov-dez
];

tbl_bimestre_inicio:
load * Inline [
	ID_Bimestre, Bimestre, range_bimestre,inicio_bimestre
	1, $(vAnoAtual)_Bimestre_1, jan-fev/$(vAnoAtual), 01/01/$(vAnoAtual)
	2, $(vAnoAtual)_Bimestre_2, mar-abr/$(vAnoAtual), 01/03/$(vAnoAtual)
	3, $(vAnoAtual)_Bimestre_3, mai-jun/$(vAnoAtual), 01/05/$(vAnoAtual)
	4, $(vAnoAtual)_Bimestre_4, jul-ago/$(vAnoAtual), 01/07/$(vAnoAtual)
	5, $(vAnoAtual)_Bimestre_5, set-out/$(vAnoAtual), 01/09/$(vAnoAtual)
	6, $(vAnoAtual)_Bimestre_6, nov-dez/$(vAnoAtual), 01/11/$(vAnoAtual)
];

left join
Load
	ID_Bimestre,
    Date(if(ID_Bimestre=6,AddYears(fim_bimestre,1)-1,fim_bimestre-1)) as fim_bimestre
inline [
	ID_Bimestre, fim_bimestre,
    1, 01/03/$(vAnoAtual)
	2, 01/05/$(vAnoAtual)
	3, 01/07/$(vAnoAtual)
	4, 01/09/$(vAnoAtual)
	5, 01/11/$(vAnoAtual)
	6, 01/01/$(vAnoAtual)
];

Let vRangeBimestreAtual =  Text(Lookup('range_bimestre', 'Bimestre', '$(vBimestre)'));

Meta:
LOAD
    bimestre & '|' & CODIGO as %ChaveCodigoBimestre,
    bimestre,
    Date("inicio bimestre") as "inicio bimestre",
    Date("fim bimestre") as "fim bimestre",
    "Grupo Cargo",
    "Gerente Meta",
    "Atende somente 1 Gerente?",
    "Gerente C. Custo",
    "Descrição Situação",
    "Categoria Situação",
    "Setor PNOPE",
    Qtde,
    CODIGO,
    Capitalize(NOME) as NOME,
    LOCAL,
    LOTACAO,
    SETOR,
    "C CUSTO",
    CARGO,
    "TURNO LOTAÇÃO",
    "TURNO HISTORICO",
    SITUACAO,
    MDO,
    DT_ADM,
    DT.NASCIMENTO,
    SEXO,
    if("Grupo Cargo" <> 'Não Elegível' And "Categoria Situação" = 'Considera', 'Elegível', 'Não Elegível') as "Elegível"
//     "EM FERIAS",
//     INI_FERIAS,
//     RET_FERIAS,
//     "DIAS FERIAS",
//     INI_FERIAS2,
//     RET_FERIAS2,
//     "DIAS FERIAS 2",
//     SALDO_BH,
//     DIAS_FERIAS_VENC,
//     DIAS_FERIAS_PROP,
//     GERENTE,
//     "TEMP OPE",
//     "qtde dias contratado",
//     "data desligamento",
//     "qtde dias trabalhados antes do desligamento",
//     "Cargo anterior",
//     "Qtde dias promovido",
//     "data promoção"
FROM [$(vPathFileMeta(*_meta_*$(vAnoAtual)*))]
(ooxml, embedded labels, table is Relatorio)
Where not IsNull(CODIGO);

// // Vamos verificar se existe o QVD Tarefas
// if not isnull(QvdCreateTime('[$(vPathFato(f_meta_melhoria_$(vAnoAtual)))]')) then
//     // caso o QVD exista, vamos então concatenar os dados que ja existem mas ignorando
//     // os registros que estão em nosso load da tabela, ou seja, somente os ids que
//     // não existirem em nosso QVD que serão carregados.
// 	Concatenate
// 	LOAD
//       *
//     FROM [$(vPathFato(f_meta_melhoria_$(vAnoAtual)))](qvd);
//     //Where not Exists(%ChaveCodigoBimestre) And bimestre <> '$(vRangeBimestreAtual)';

// End If;


// Store Meta into [$(vPathFato(f_meta_melhoria_$(vAnoAtual)))](qvd);

// Drop Table Meta;

//  exit Script;
```


## Load Assinatura (table mel_aprovacao)
```qlik
//############### Caminhos arquivos #####################
//SET vPathFile   	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/$1.xls?;
SET vPathFile   	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;
SET vPathFato   	=lib://QVD - QlikView - Prd/Engenharia/Portal_Engenharia_NE/$1.qvd;
SET vPathFileOPE    =lib://QVD - QlikSense - Prd/Engenharia_NE/OPE/$1.qvd;

//SET vPathFileMeta 		=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/metas/$1.xlsx;
//SET vPathFileMelhorias 	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileMeta 		=lib://Arquivos - ENG SOB/Melhorias/metas/$1.xlsx;
SET vPathFileMelhorias 	=lib://Arquivos - ENG SOB/Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileQualidadeIndicadores 	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;

//CONFIG
//############### configurações para os graficos #####################
SET vConsumo = 'Consumo';
SET vTC = 'Tempo Ciclo';
SET vTrocaMP = 'Troca de Matéria Prima';
SET vNumFormat = '#.##0,00';
SET vQtdeDiasPegarMelhorias = 365;
LET vAnoAtual = text(Year(Today() - 4));



Tbl_Config:
LOAD
    Key,
    Value
FROM [$(vPathFile(script.aderencia.config))]
(ooxml, embedded labels, table is Planilha1);



LET vBimestre = Lookup('Value', 'Key', 'Bimestre');
LET vAnoAtual = Text(Lookup('Value', 'Key', 'Ano para puxar os dados'));


// LET vAnoAtual = Text(2026);
// Let vBimestre = '$(vAnoAtual)' & '_Bimestre_1'; //Lookup('Value', 'Key', 'Bimestre');

Drop Table Tbl_Config;

```

## Load Assinatura (table mel_aprovacao)
```qlik
Base_Aderencia_tmp:
LOAD
    ID,
    id_solicitacao_assinatura,
    tipo_melhoria,
    filial,
    gerente,
    fabrica,
    setor,
    nome_solicitante,
    Text(numero_fap2) as [Nº F.A.P],
    dt_fap,
    cod_prod,
    preco_mp,
    consumo_anterior,
    consumo_atual,
    padrao_anterior,
    padrao_atual,
    efetivo_anterior,
    efetivo_atual,
    tc_anterior,
    tc_atual,
    mix,
    volume_mes_1,
    volume_mes_2,
    volume_mes_3,
    volume_mes_4,
    %_ganho,
    custo_par_anterior,
    custo_par_atual,
    origem_melhoria,
    macro_setor,
    replicavel,
    nome_setor_replicavel,
    nome_especialista,
    nome_aprovador_setor,
    desc_melhoria,
    is_lacamento_manual,
    investimento,
    ganho_previsto,
    cracha_idealizador,
    nome_idealizador,
    cc_idealizador,
    descricao_proc_atual_outras_m,
    descricao_proc_prop_outras_m,
    qtde_mo_atual_outras_m,
    qtde_mo_proposto_outras_m,
    dt_fap_informada_por,
    salario_MOD,
    carga_horaria_mes,
    peso_ponderado_componente,
    Criado,
    "Criado por",
    tipo_alteracao,
    tipo_fap,
    Modificado,
    "Modificado por",
    "Gerente Idealizador",
    "É uma replicação?",
    "volume foi editado",
    Cargo as "Cargo do app",
    "Tipo de Item",
    Caminho,
    "Gerente idalizador painel",
    Status,
    if(
    	Status = 'Aprovado' And IsNull(dt_fap) And "Precisa de FAP?" = 'Sim',
        'Pendente data da fap',
        if(
        	Status = 0,
            'Reprovado',
            Status
        )
    ) as "status.2 Base_Aderencia",
    "Matricula Idealizador",
    "Nome do Idealizador",
    "CC da Meta",
    "Cargo da meta",
    "Ger. Ideal. Na data Meta",
    "Grupo Cargo na data Meta",
    "Descrição Situação",
    "Categoria Situação",
    "Precisa de FAP?",
    "Data Aprovação Espec.",
    "Data FAP",
    "Data para Meta",
    "Resultado da FAP",
    "Valor Total",
    Aglutinação,
    "Tempo Ciclo",
    Consumo,
    "Troca de Matéria Prima",
    "Logística interna e Outros",
    "Considera para a Contagem",
    "Qtde Pessoas com melhorias",
    "Qtde de Melhorias",
    Ano_Mes,
    Bimestre as "Ano bimestre mês",
    Origem as "Origem da aderencia",
    "Verificação se há duplicados"
    //Month("Data para Meta") as "Numero do mês do bimestre"
    //if ( "Precisa de FAP?" = 'Sim'; dt_fap,  ),
FROM [$(vPathFile(Base_Melhorias_Aderencia*))]
(ooxml, embedded labels, table is BD_Melhorias)
where
	1 = 1
    and Not IsNull(ID)
    and Bimestre = '$(vBimestre)';
//     and cracha_idealizador = '13152776';
// 	Not IsNull(ID) And
// 	Year(Modificado) = $(vAnoAtual) And
//     (((Num(Modificado) >= Today() - $(vQtdeDiasPegarMelhorias)) And IsNull(Bimestre)) Or Bimestre = '$(vBimestre)');
//where Not IsNull(ID) And (IsNull(Bimestre) Or Bimestre = '$(vBimestre)') And Year(Modificado) = $(vAnoAtual);
//where Not IsNull(ID) And Bimestre = '$(vBimestre)' And Year(Modificado) = $(vAnoAtual);
//where Not IsNull(ID) And Year(Modificado) = $(vAnoAtual);

//Pegamos o ano da meta
//Let vYearMeta = Year(Peek('Data para Meta', 1, 'Base_Aderencia'));

Left Join
Load
  "ID assinatura" as id_solicitacao_assinatura,
  "status assinatura" as "status Assinatura->Base_Aderencia",
  "dt_aprovacao_especialista assinatura"
Resident Assinatura;

// Left Join
// LOAD
//     "Número da fap" as [Nº F.A.P],
//     "É uma replicação?" as Ajuste
// FROM [lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/Melhorias-Inacio.xlsx]
// (ooxml, embedded labels, table is Sheet1);



// tmp:
// Load
//  Min(Modificado) as Min_Modificado
// Resident Base_Aderencia_tmp
// Where "Ano bimestre mês" = '$(vBimestre)'
// ;

// Let vMinModificadoAderencia = Peek('Min_Modificado');

// drop Table tmp;

Base_Aderencia:
Load
	*,
    Month(
        if(
            isnull("dt_aprovacao_especialista assinatura"),
            if(
                //Em andamento, Levamos a melhoria para o mês atual pq ela ainda pode ser aprovada.
                (Month(Criado)+Year(Criado)) < Month(Today())+Year(Today()),
                Today(),
                Date(Floor(Num(Criado)),'DD/MM/YYYY')
            ),
        	"dt_aprovacao_especialista assinatura"
        )
	) as "Numero do mês do bimestre"
//     If(
//     	isnull(Ajuste)
//     	,"É uma replicação?"
//         , Ajuste
//     ) as "É uma replicação?2"
Resident Base_Aderencia_tmp;

Drop Table Base_Aderencia_tmp;

// Drop Fields Ajuste, "É uma replicação?" From Base_Aderencia;
// Rename Field "É uma replicação?2" to "É uma replicação?";

Left Join
Load
  "Mês" as "Numero do mês do bimestre",
  Bimestre & '/' & '$(vAnoAtual)' as "Mês-Mês/Ano bimestre",
  Num("Mês" & '$(vAnoAtual)') as "Num MêsAno bimestre"
Resident tbl_bimestre;


// Vamos verificar se existe o QVD Tarefas
If not isnull(QvdCreateTime('[$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))]')) then
    // caso o QVD exista, vamos então concatenar os dados que ja existem mas ignorando
    // os registros que estão em nosso load da tabela, ou seja, somente os ids que
    // não existirem em nosso QVD que serão carregados.
	Concatenate(Base_Aderencia)
    Load
        *
    FROM [$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))](qvd)
    //Where not Exists(ID) And Modificado < Num('$(vMinModificadoAderencia)');
    //Where not Exists(ID) And Modificado < Today() - $(vQtdeDiasPegarMelhorias);
    Where
    	1 = 1
//         And not IsNull("Ano bimestre mês")
        And "Ano bimestre mês" like '$(vAnoAtual)_Bimestre_*'
        And "Ano bimestre mês" <> '$(vBimestre)'
        And "Data Aprovação Espec." >='01/01/$(vAnoAtual)'
//         and not Exists(ID)
//         and not Match([Nº F.A.P],'31072025120412','31072025120420','241102025081804','241102025081806','24032025021402','193102025022116','241062025022811','186032025061001','193102025070801','34072025061701',
//    '241102025081807','241102025082101','133112025062302','13311202561801')
    ; //And "Ano bimestre mês" <> '$(vBimestre)' And Not IsNull("Ano bimestre mês");


End If;

drop Fields "dt_aprovacao_especialista assinatura" From Base_Aderencia;

Store Meta into [$(vPathFato(f_meta_melhoria_$(vAnoAtual)))](qvd);

Store Assinatura into [$(vPathFato(f_assinatura_melhoria_unica))](qvd);

Store Base_Aderencia into [$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))](qvd);

Rename Table Base_Aderencia to Base_Aderencia_chk;

// Drop Tables Base_Aderencia_tmp;

// exit Script;

// Melhorias em andamento
Base_Aderencia_tmp:
LOAD
    ID,
    id_solicitacao_assinatura,
    tipo_melhoria,
    filial,
    gerente,
    fabrica,
    setor,
    nome_solicitante,
    Text(numero_fap2) as [Nº F.A.P],
    dt_fap,
    cod_prod,
    preco_mp,
    consumo_anterior,
    consumo_atual,
    padrao_anterior,
    padrao_atual,
    efetivo_anterior,
    efetivo_atual,
    tc_anterior,
    tc_atual,
    mix,
    volume_mes_1,
    volume_mes_2,
    volume_mes_3,
    volume_mes_4,
    %_ganho,
    custo_par_anterior,
    custo_par_atual,
    origem_melhoria,
    macro_setor,
    replicavel,
    nome_setor_replicavel,
    nome_especialista,
    nome_aprovador_setor,
    desc_melhoria,
    is_lacamento_manual,
    investimento,
    ganho_previsto,
    cracha_idealizador,
    nome_idealizador,
    cc_idealizador,
    descricao_proc_atual_outras_m,
    descricao_proc_prop_outras_m,
    qtde_mo_atual_outras_m,
    qtde_mo_proposto_outras_m,
    dt_fap_informada_por,
    salario_MOD,
    carga_horaria_mes,
    peso_ponderado_componente,
    Criado,
    "Criado por",
    tipo_alteracao,
    tipo_fap,
    Modificado,
    "Modificado por",
    "Gerente Idealizador",
    "É uma replicação?",
    "volume foi editado",
    Cargo as "Cargo do app",
    "Tipo de Item",
    Caminho,
    "Gerente idalizador painel",
    Status,
    if(
    	Status = 'Aprovado' And IsNull(dt_fap) And "Precisa de FAP?" = 'Sim',
        'Pendente data da fap',
        if(
        	Status = 0,
            'Reprovado',
            Status
        )
    ) as "status.2 Base_Aderencia",
    "Matricula Idealizador",
    "Nome do Idealizador",
    "CC da Meta",
    "Cargo da meta",
    "Ger. Ideal. Na data Meta",
    "Grupo Cargo na data Meta",
    "Descrição Situação",
    "Categoria Situação",
    "Precisa de FAP?",
    "Data Aprovação Espec.",
    "Data FAP",
    "Data para Meta",
    "Resultado da FAP",
    "Valor Total",
    Aglutinação,
    "Tempo Ciclo",
    Consumo,
    "Troca de Matéria Prima",
    "Logística interna e Outros",
    "Considera para a Contagem",
    "Qtde Pessoas com melhorias",
    "Qtde de Melhorias",
    Ano_Mes,
    Bimestre as "Ano bimestre mês",
    Origem as "Origem da aderencia",
    "Verificação se há duplicados"
    //Month("Data para Meta") as "Numero do mês do bimestre"
    //if ( "Precisa de FAP?" = 'Sim'; dt_fap,  ),
FROM [$(vPathFile(Base_Melhorias_Aderencia*))]
(ooxml, embedded labels, table is BD_Melhorias)
where
	1 = 1
	And Not IsNull(ID)
    And not Bimestre like '$(vAnoAtual)_Bimestre_*';
//where Not IsNull(ID) And (IsNull(Bimestre) Or Bimestre = '$(vBimestre)') And Year(Modificado) = $(vAnoAtual);
//where Not IsNull(ID) And Bimestre = '$(vBimestre)' And Year(Modificado) = $(vAnoAtual);
//where Not IsNull(ID) And Year(Modificado) = $(vAnoAtual);

//Pegamos o ano da meta
//Let vYearMeta = Year(Peek('Data para Meta', 1, 'Base_Aderencia'));

Left Join
Load
  "ID assinatura" as id_solicitacao_assinatura,
  "status assinatura" as "status Assinatura->Base_Aderencia",
  "dt_aprovacao_especialista assinatura"
Resident Assinatura;


// tmp:
// Load
//  Min(Modificado) as Min_Modificado
// Resident Base_Aderencia_tmp
// Where IsNull("Ano bimestre mês")
// ;

// Let vMinModificadoAderencia = Peek('Min_Modificado');

// drop Table tmp;

Base_Aderencia:
Load
	*,
    Month(
    	if(
            isnull("dt_aprovacao_especialista assinatura"),
            if(
                //Em andamento, Levamos a melhoria para o mês atual pq ela ainda pode ser aprovada.
                (Month(Criado)+Year(Criado)) < Month(Today())+Year(Today()),
                Today(),
                Date(Floor(Num(Criado)),'DD/MM/YYYY')
            ),
        	"dt_aprovacao_especialista assinatura"
        )
	) as "Numero do mês do bimestre"
Resident Base_Aderencia_tmp;

Left Join(Base_Aderencia)
Load
  "Mês" as "Numero do mês do bimestre",
  Bimestre & '/' & '$(vAnoAtual)' as "Mês-Mês/Ano bimestre",
  Num("Mês" & '$(vAnoAtual)') as "Num MêsAno bimestre"
Resident tbl_bimestre;

// // Vamos verificar se existe o QVD Tarefas
// if not isnull(QvdCreateTime('[$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))]')) then
//     // caso o QVD exista, vamos então concatenar os dados que ja existem mas ignorando
//     // os registros que estão em nosso load da tabela, ou seja, somente os ids que
//     // não existirem em nosso QVD que serão carregados.
// 	Concatenate(Base_Aderencia)
//     Load
//         *
//     FROM [$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))](qvd)
//     //Where not Exists(ID) And Modificado < Num('$(vMinModificadoAderencia)');
//     //Where not Exists(ID) And Modificado < Today() - $(vQtdeDiasPegarMelhorias);
//     Where not Exists(ID) And "Ano bimestre mês" <> '$(vBimestre)' And Not IsNull("Ano bimestre mês");


// End If;


drop Fields "dt_aprovacao_especialista assinatura" From Base_Aderencia;

// Store Meta into [$(vPathFato(f_meta_melhoria_$(vAnoAtual)))](qvd);

// Store Assinatura into [$(vPathFato(f_assinatura_melhoria_$(vAnoAtual)))](qvd);

Store Base_Aderencia into [$(vPathFato(f_base_aderencia_melhoria_em_andamento))](qvd);

Drop Table Base_Aderencia, tbl_bimestre, Assinatura, Meta, Base_Aderencia_tmp, tbl_bimestre_inicio;

// exit Script;
```

## Load tempo ciclo (table mel_ganhos)
```qlik
//############### Caminhos arquivos #####################
//SET vPathFile   	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/$1.xls?;
SET vPathFile   	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;
SET vPathFato   	=lib://QVD - QlikView - Prd/Engenharia/Portal_Engenharia_NE/$1.qvd;
SET vPathFileOPE    =lib://QVD - QlikSense - Prd/Engenharia_NE/OPE/$1.qvd;

//SET vPathFileMeta 		=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/metas/$1.xlsx;
//SET vPathFileMelhorias 	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileMeta 		=lib://Arquivos - ENG SOB/Melhorias/metas/$1.xlsx;
SET vPathFileMelhorias 	=lib://Arquivos - ENG SOB/Melhorias/bases_app_melhorias/$1.xlsx;
SET vPathFileQualidadeIndicadores 	=lib://Arquivos - ENG SOB/Melhorias/$1.xls?;

//CONFIG
//############### configurações para os graficos #####################
SET vConsumo = 'Consumo';
SET vTC = 'Tempo Ciclo';
SET vTrocaMP = 'Troca de Matéria Prima';
SET vNumFormat = '#.##0,00';
SET vQtdeDiasPegarMelhorias = 365;
LET vAnoAtual = text(Year(Today() - 4));



Tbl_Config:
LOAD
    Key,
    Value
FROM [$(vPathFile(script.aderencia.config))]
(ooxml, embedded labels, table is Planilha1);



LET vBimestre = Lookup('Value', 'Key', 'Bimestre');
LET vAnoAtual = Text(Lookup('Value', 'Key', 'Ano para puxar os dados'));


// LET vAnoAtual = Text(2026);
// Let vBimestre = '$(vAnoAtual)' & '_Bimestre_1'; //Lookup('Value', 'Key', 'Bimestre');

Drop Table Tbl_Config;

```
