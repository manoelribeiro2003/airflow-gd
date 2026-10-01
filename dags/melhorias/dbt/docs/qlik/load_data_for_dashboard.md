
## Main
```qlik
SET ThousandSep='.';
SET DecimalSep=',';
SET MoneyThousandSep='.';
SET MoneyDecimalSep=',';
SET MoneyFormat='R$#.##0,00;-R$#.##0,00';
SET TimeFormat='hh:mm:ss';
SET DateFormat='DD/MM/YYYY';
SET TimestampFormat='DD/MM/YYYY hh:mm:ss[.fff]';
SET FirstWeekDay=6;
SET BrokenWeeks=1;
SET ReferenceDay=0;
SET FirstMonthOfYear=1;
SET CollationLocale='pt-BR';
SET CreateSearchIndexOnReload=1;
SET MonthNames='jan;fev;mar;abr;mai;jun;jul;ago;set;out;nov;dez';
SET LongMonthNames='janeiro;fevereiro;março;abril;maio;junho;julho;agosto;setembro;outubro;novembro;dezembro';
SET DayNames='seg;ter;qua;qui;sex;sáb;dom';
SET LongDayNames='segunda-feira;terça-feira;quarta-feira;quinta-feira;sexta-feira;sábado;domingo';
SET NumericalAbbreviation='3:k;6:M;9:G;12:T;15:P;18:E;21:Z;24:Y;-3:m;-6:μ;-9:n;-12:p;-15:f;-18:a;-21:z;-24:y';

SEARCH EXCLUDE * ;
```

## Variaveis
```qlik
//SERVER
//############### Caminhos arquivos #####################
//SET vPathFile   	=lib://Arquivos - Engenharia/Portal_Engenharia_NE/Indicador de Melhorias/$1.xlsx;
SET vPathFile   	=lib://Arquivos - ENG SOB/Melhorias/$1.xlsx;
SET vPathFileOPE    =lib://QVD - QlikSense - Prd/Engenharia_NE/OPE/$1.qvd;
SET vPathFato   	=lib://QVD - QlikView - Prd/Engenharia/Portal_Engenharia_NE/$1.qvd;


//CONFIG
//############### configurações para os graficos #####################
SET vConsumo = 'Consumo';
SET vTC = 'Tempo Ciclo';
SET vTrocaMP = 'Troca de Matéria Prima';
SET vNumFormat = '#.##0,00';


//############### configurações para script #####################
Tbl_Config:
LOAD
    Key,
    Value
FROM [$(vPathFile(script.aderencia.config))]
(ooxml, embedded labels, table is Planilha1);

Let vBimestre = Lookup('Value', 'Key', 'Bimestre');
Let vAnoAtual = Text(Lookup('Value', 'Key', 'Ano para puxar os dados'));
Let vMetaAderencia = Lookup('Value', 'Key', 'Meta aderencia');

Drop Table Tbl_Config;
```

## Load aderencia simples
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

[tipo de melhoria]:
LOAD
    [Tipo de Melhoria],
    [Categoria das melhorias]
FROM [$(vPathFile(categoria_das_melhorias))]
(ooxml, embedded labels, table is [tipo de melhoria]);

Assinatura:
LOAD
    *,
    "ID assinatura" as id_solicitacao_assinatura,
    FileName() as nome_arquivo_assinatura
FROM [$(vPathFato(f_assinatura_melhoria_unica))](qvd)

// where
//   Match(
//   "numero_fap assinatura"
//   ,'143102025112801'
//   ,'143102025112503'
//   ,'143102025112502'
//   ,'143102025112501'
// )
;

Drop Field "ID assinatura" From Assinatura;

Base_Aderencia_tmp:
LOAD
    ID
    ,id_solicitacao_assinatura
    ,tipo_melhoria
    ,filial
    ,gerente
    ,fabrica
    ,setor
    ,nome_solicitante
    ,[Nº F.A.P]
    ,dt_fap
    ,cod_prod
    ,preco_mp
    ,consumo_anterior
    ,consumo_atual
    ,padrao_anterior
    ,padrao_atual
    ,efetivo_anterior
    ,efetivo_atual
    ,tc_anterior
    ,tc_atual
    ,mix
    ,volume_mes_1
    ,volume_mes_2
    ,volume_mes_3
    ,volume_mes_4
    ,%_ganho
    ,custo_par_anterior
    ,custo_par_atual
    ,origem_melhoria
    ,macro_setor
    ,replicavel
    ,nome_setor_replicavel
    ,nome_especialista
    ,nome_aprovador_setor
    ,desc_melhoria
    ,is_lacamento_manual
    ,investimento
    ,ganho_previsto
    ,cracha_idealizador
    ,nome_idealizador
    ,cc_idealizador
    ,descricao_proc_atual_outras_m
    ,descricao_proc_prop_outras_m
    ,qtde_mo_atual_outras_m
    ,qtde_mo_proposto_outras_m
    ,dt_fap_informada_por
    ,salario_MOD
    ,carga_horaria_mes
    ,peso_ponderado_componente
    ,Criado
    ,"Criado por"
    ,tipo_alteracao
    ,tipo_fap
    ,Modificado
    ,"Modificado por"
    ,"Gerente Idealizador"
    ,"É uma replicação?"
    ,"volume foi editado"
//     Cargo as "Cargo do app",
//     "Tipo de Item",
//     Caminho,
    ,"Gerente idalizador painel"
    ,Status
//     if(
//     	Status = 'Aprovado' And IsNull(dt_fap) And "Precisa de FAP?" = 'Sim',
//         'Pendente data da fap',
//         if(
//         	Status = 0,
//             'Reprovado',
//             Status
//         )
//     ) as "status.2 Base_Aderencia",
//     "Matricula Idealizador",
//     "Nome do Idealizador",
//     "CC da Meta",
//     "Cargo da meta",
//     "Ger. Ideal. Na data Meta",
//     "Grupo Cargo na data Meta",
//     "Descrição Situação",
//     "Categoria Situação",
//     "Precisa de FAP?",
//     "Data Aprovação Espec.",
    ,"Data FAP"
    ,"Data para Meta"
    ,"Resultado da FAP"
//     "Valor Total",
//     Aglutinação,
//     "Tempo Ciclo",
//     Consumo,
//     "Troca de Matéria Prima",
//     "Logística interna e Outros",
    ,"Considera para a Contagem"
    ,"Qtde Pessoas com melhorias"
    ,"Qtde de Melhorias"
//     Ano_Mes,
//     Bimestre as "Ano bimestre mês",
//     Origem as "Origem da aderencia",
//     "Verificação se há duplicados"
    //Month("Data para Meta") as "Numero do mês do bimestre"
    //if ( "Precisa de FAP?" = 'Sim'; dt_fap,  ),
    ,"Mês-Mês/Ano bimestre"
    ,"Num MêsAno bimestre"
    ,FileName() 								as nome_arquivo_base_aderencia
    ,date("Data para Meta") + 30 				as dt_fap_anterior_base_aderencia
    ,Month(date("Data para Meta") + 30) 		as mes_anterior_base_aderencia
FROM [$(vPathFato(f_base_aderencia_melhoria_*))](qvd) /* ???? == ano */
// where cracha_idealizador = '13152776' and "Data para Meta" > '01/05/2025'
;

//Where "Mês-Mês/Ano bimestre" = 'mai-jun/2022' and not IsNull(dt_fap);

Left Join
Load
  "Mês" 								as mes_anterior_base_aderencia,
  Bimestre & '/' & '$(vAnoAtual)' 		as "Mês-Mês/Ano bimestre mes_anterior"
Resident tbl_bimestre;

// exit Script;

Base_Aderencia:
LOAD
    *
    ,Text("cc_idealizador") 															As "cc_idealizador2"
    ,"Mês-Mês/Ano bimestre" & '|' & cracha_idealizador 									As %ChaveCodigoBimestre
    ,"Mês-Mês/Ano bimestre mes_anterior" & '|' & [nome_idealizador] & '|' & [Nº F.A.P] 	As %ChaveBimestreNomeIdealizador
    ,[Data para Meta]																	As [DataLink Aderencia]
Resident Base_Aderencia_tmp
// where
//   Match(
//   "Nº F.A.P"
//   ,'143102025112801'
//   ,'143102025112503'
//   ,'143102025112502'
//   ,'143102025112501'
// )
// order by ID
;

Drop Tables Base_Aderencia_tmp;


// Left Join
// Load
// 	[Tipo de Melhoria] as tipo_melhoria,
//     [Precisa de FAP?] as [Precisa de FAP? 2]
// Resident [tipo de melhoria];
//
// Atualizacao_aderencia:
// LOAD
//     FileTime() As [Data atualização aderencia]
// FROM [$(vPathFato(f_base_aderencia_melhoria_$(vAnoAtual)))](qvd);

// [dNumeroFAP]:
// Load Distinct
// 	[Nº F.A.P],
//     [Nº F.A.P] as "dNumero da fap"
// Resident Base_Aderencia;

[dNumeroFAP]:
Load Distinct
	id_solicitacao_assinatura,
    Text("numero_fap assinatura") as [Nº F.A.P]
Resident Assinatura;

// Left Join
// Load
// 	id_solicitacao_assinatura,
//     [Precisa de FAP? 2] As [Precisa de FAP?]
// Resident Base_Aderencia;

// Drop Field "Precisa de FAP?" From Base_Aderencia;

Left Join(dNumeroFAP)
Load
	id_solicitacao_assinatura,
    Text("numero_fap assinatura") 								as "dNumero da fap",
    //"numero_fap assinatura" as [Nº F.A.P],
    "status_aprov_especialista assinatura" 						as "status_aprov_especialista dNumeroFAP",
    "dt_aprovacao_especialista_original assinatura"				as "dt_aprovacao_especialista_original dNumeroFAP",
    "nome_quem_aprovou_setor assinatura"						as "nome_quem_aprovou_setor dNumeroFAP",
    "status_aprov_setor assinatura"								as "status_aprov_setor dNumeroFAP",
    "dt_aprovacao_setor assinatura"								as "dt_aprovacao_setor dNumeroFAP",
    "status assinatura"											as "status dNumeroFAP"
Resident Assinatura;


Left Join(dNumeroFAP)
Load
	id_solicitacao_assinatura,
    Sum("Qtde de Melhorias")			as "Qtde melhoria dNumeroFAP",
	Count(ID) 							as "Qtde linhas dNumeroFAP"
Resident Base_Aderencia
Group By id_solicitacao_assinatura;

Left Join(dNumeroFAP)
Load
	id_solicitacao_assinatura,
    "Resultado da FAP" As "Resultado da FAP dNumeroFAP"//,
//     dt_fap,
//     "Precisa de FAP?"
Resident Base_Aderencia;

Drop Field id_solicitacao_assinatura From dNumeroFAP;

// dNumeroFAP_tmp:
// Load
// 	*,
// 	if(
//     	"status dNumeroFAP" = 'Aprovado' And IsNull(dt_fap) And "Precisa de FAP?" = 'Sim',
//         'Pendente data da fap',
//         "status dNumeroFAP"
//     ) as "status dNumeroFAP.2"
// Resident dNumeroFAP;

// Drop Table dNumeroFAP;
// Rename Table dNumeroFAP_tmp to dNumeroFAP;

// Drop Fields dt_fap, "Precisa de FAP?", "status dNumeroFAP" From dNumeroFAP;
// Rename Field "status dNumeroFAP.2" to "status dNumeroFAP";

Meta_:
LOAD
    bimestre & '-' & "Gerente Meta" 	as %chaveBimestreGerente,
    %ChaveCodigoBimestre,
    "Grupo Cargo" as "Todos os Grupo Cargo meta",
    "Gerente Meta" as "Todos Gerente Meta tabela meta",
    "Atende somente 1 Gerente?",
    "Gerente C. Custo",
    "Descrição Situação" as "Descrição Situação meta",
    "Categoria Situação" as "Categoria Situação meta",
    "Setor PNOPE",
    bimestre as bimestre_meta,
    "inicio bimestre",
    "fim bimestre",
    Qtde,
    CODIGO,
    NOME,
    LOCAL,
    LOTACAO,
    SETOR,
    "C CUSTO",
    If(wildmatch(Text([C CUSTO]), '2048*', '2049*', '2148*', '2149*', '4048*', '4049*'),Text([C CUSTO]), Null()) As CCusto_Eng,
    CARGO,
    "TURNO LOTAÇÃO",
    "TURNO HISTORICO",
    SITUACAO,
    MDO,
    DT_ADM,
    DT.NASCIMENTO,
    SEXO,
    "Elegível",
	if("Grupo Cargo" = 'Não Elegível' Or "Categoria Situação" <> 'Considera',Null(),"Grupo Cargo") as "Grupo Cargo meta",
    //"Grupo Cargo" as "Grupo Cargo meta",
    if(
    	"Grupo Cargo" = 'Não Elegível' Or "Categoria Situação" <> 'Considera',
        "Gerente Meta",
        if(
        	Match("Gerente Meta", 'Rossi', 'Sul'),
            "Gerente Meta",
            "Gerente Meta"
        )
    ) as "Gerente Meta tabela meta"
	//"Gerente Meta" as "Gerente Meta tabela meta"
FROM [$(vPathFato(f_meta_melhoria_*))](qvd);

left join
Load
	%ChaveCodigoBimestre,
    Sum([Qtde Pessoas com melhorias]) 				As [Realizado meta],
    Sum([Qtde de Melhorias]) 						As [Qtde Melhorias Meta]
Resident Base_Aderencia
Group By %ChaveCodigoBimestre;

//05/03/2024 modificado
[Meta]:
load
	*,
    if(
    [Gerente Meta tabela meta] = 'Andre Miorelli', 'Andre - F4',
    if ([Gerente Meta tabela meta] = 'Beatriz' And [inicio bimestre] < '01/05/2025', 'Valsenir F6',
    if ([Gerente Meta tabela meta] = 'Beatriz F5' And [inicio bimestre] < '01/05/2025', 'Ademir Tênis',
    if ([Gerente Meta tabela meta] = 'Liberio' And [inicio bimestre] < '01/05/2023', 'Andre - F3',
    if ([Gerente Meta tabela meta] = 'Douglas Monteiro', 'Andre - F4',
    if ([Gerente Meta tabela meta] = 'Ademir', 'Ademir - F1',
    if ([Gerente Meta tabela meta] = 'Odair', 'Ademir - F5',
    if ([Gerente Meta tabela meta] = 'Ademar', 'Tiago',
    if ([Gerente Meta tabela meta] = 'Adair', 'Liberio',
    if ([Gerente Meta tabela meta] = 'Andre Luis', 'Ana Livia',
    if ([Gerente Meta tabela meta] = 'E-Commerce' Or [Gerente Meta tabela meta] = 'Gerência PPCP', 'Martinho',
    [Gerente Meta tabela meta]
    ))))))))))) as [Gerente Meta Ajustado]
resident Meta_;

left Join

load
	Gerente as [Gerente Meta Ajustado],
    [Area Gerente]
FROM [$(vPathFile(gerentes))]
(ooxml, embedded labels, table is [Gerentes]);


drop table Meta_;

// Load
// 	%ChaveCodigoBimestre,
//     [Nº F.A.P] as f
// Resident Base_Aderencia Where %ChaveCodigoBimestre like '*13914110';

```

## dCalendario
```qlik
[maior_menor_data_link_table]:
LOAD
    MIN([Data para Meta])                                                AS [Menor Data Link],
    MAX([Data para Meta])                                                AS [Maior Data Link]
RESIDENT Base_Aderencia
where [Data para Meta] > '01/01/2020'
;

LET vMenorDataLink = PEEK('Menor Data Link');
LET vMaiorDataLink = PEEK('Maior Data Link');
LET vDifDataLink   = vMaiorDataLink - vMenorDataLink + 1;

DROP TABLE [maior_menor_data_link_table];

// ----------------------------------------------------------------------------------------------------------
[temp_intervalo_data_numerica]:
LOAD
    '$(vMenorDataLink)' + RECNO() - 1                                AS [Data AnoMêsDia]
AUTOGENERATE($(vDifDataLink));


// ----------------------------------------------------------------------------------------------------------
// Quando incluir um novo campo na tabela abaixo, verificar as dimensões/medidas que desconsiderarm os campos
// desta tabela, pois deverá ser incluído o novo campo também.
// ----------------------------------------------------------------------------------------------------------
// Os FLAGs de dia e mes, são com base no dia anterior a carga.
// ----------------------------------------------------------------------------------------------------------



[dCalendarioAderencia]:
LOAD
    [Data AnoMêsDia]                                                	AS [DataLink Aderencia],
//    MONTHSTART([Data AnoMêsDia])                                    	AS [Primeiro Dia Mês Atual],
//    ADDMONTHS(MONTHSTART([Data AnoMêsDia]),-1)                        AS [Primeiro Dia Mês Anterior],
    YEAR([Data AnoMêsDia])                                          	AS [Ano Aderencia],
    //(MONTH([Data AnoMêsDia])                         					AS [Mes],
    date([Data AnoMêsDia],'MM')                         				AS [Mes Aderencia],
    DAY([Data AnoMêsDia])                                            	AS [Dia Aderencia],
//    Date([Data AnoMêsDia],'DD/MMM')                                   AS [Dia/Mês],
//    DATE(MONTHSTART([Data AnoMêsDia]),'MMM/YYYY')                     AS [Período],
    Capitalize(MONTH([Data AnoMêsDia])) & '/' & YEAR([Data AnoMêsDia])  AS [Mês/Ano Aderencia],
    num(Day([Data AnoMêsDia]),'00') & '/' & Capitalize(MONTH([Data AnoMêsDia]))   AS [Dia/Mês Aderencia],
    Peek('Bimestre',Month([Data AnoMêsDia]),'tbl_bimestre') &'/'& YEAR([Data AnoMêsDia])			As [Bimestre Aderencia]
//     MID([Data AnoMêsDia],6,2) & YEAR([Data AnoMêsDia])                AS [MêsAno],
//    YEAR([Data AnoMêsDia]) & MID([Data AnoMêsDia],6,2)                AS [AnoMês],
//    IF(MONTH([Data AnoMêsDia]) <= 6,'1° Semestre','2° Semestre')    AS [Semestre],
//    WEEK([Data AnoMêsDia])                                            AS [Semana],
//     WEEKDAY([Data AnoMêsDia])                                         AS [Dia Semana],
//     IF(MONTHSTART([Data AnoMêsDia]) = MONTHSTART(TODAY()),
//        NETWORKDAYS(MONTHSTART([Data AnoMêsDia]), TODAY(), $(vFeriados)),
//        NETWORKDAYS(MONTHSTART([Data AnoMêsDia]), MONTHSEND(1,[Data AnoMêsDia]), $(vFeriados)))
//                                                                     AS [Dias Úteis],
//     NETWORKDAYS(MONTHSTART([Data AnoMêsDia]), MONTHSEND(1,[Data AnoMêsDia]), $(vFeriados))
//                                                                     AS [Dias Úteis Mês],
//     IF(DATE([Data AnoMêsDia]) = DATE(TODAY() -3),1,0)                AS [Flag Dia Antepenúltimo],
//     IF(DATE([Data AnoMêsDia]) = DATE(TODAY() -2),1,0)                AS [Flag Dia Anterior],
//      IF(DATE([Data AnoMêsDia]) = DATE(TODAY() -1),1,0)                AS [Flag Dia Atual]
//     IF(DATE([Data AnoMêsDia]) = TODAY(),1,0)                        AS [Flag Dia Sistema],
//     IF(MONTHSTART([Data AnoMêsDia]) = ADDMONTHS(MONTHSTART(TODAY() -1),-1),1,0)
//                                                                     AS [Flag Mês Anterior],
//     IF(MONTHSTART([Data AnoMêsDia]) = MONTHSTART(TODAY() -1),1,0)    AS [Flag Mês Atual],
//     IF  (MONTHSTART(TODAY()) <> MONTHSTART([Data AnoMêsDia])
//     AND CEIL((ADDMONTHS(MONTHSTART(TODAY()),-1) - MONTHSTART([Data AnoMêsDia])) /30) <= 12,
//         1,0)                                                        AS [Flag 12 Meses]
//     IF(MONTHSTART([Data AnoMêsDia]) <= ADDMONTHS(MONTHSTART(TODAY()),-13),0,1)
//                                                                     AS [Flag Últimos 13 Meses]
//     IF(num([Data Report]) < num([Data FAP])+ 30
//        and [Data Report] >= num([Data FAP]),1,0)                       AS [Flag Mes 1]
RESIDENT [temp_intervalo_data_numerica]
ORDER BY [Data AnoMêsDia];

DROP TABLE [temp_intervalo_data_numerica];
```

## base melhoria (table mel_ganhos)
```qlik
base_melhoria_temp:
LOAD
    [Estab.] &'|'& [Setor Macro] &'|'& text(Date([Data da FAP],'MMM/YYYY'))			As %ChaveEstabSetorMacroPeiodoCH,
    [Estab.] &'|'& text(Date([Data da FAP],'MMM/YYYY'))								As %ChaveEstabPeiodoSalario,
    [Tipo de Melhoria],
    Estab.,
    Setor,
    Processista,
    Text([Nº F.A.P]) as [Nº F.A.P],
    [Data da FAP],
    Código as Código,
    [Preço M.P.],
    Cons_Anterior,
    Cons_Atual,
    [Padrão Anterior],
    [Padrão Atual],
    [Efetivo Anterior],
    [Efetivo Atual],
    [T.C. Anterior],
    [T.C. Atual],
    MIX,
    [1º Mês],
    [2º Mês],
    [3º Mês],
    [4º Mês],
    Usuário,
    [Dia / Hora Inicio],
    [Dia / Hora Fim],
    Observação,
    [% Ganho],
    [Custo Par Anterior],
    [Custo Par Atual],
    Mês,
    Origem,
    [Setor Macro] as area_melhoria,
    [Idealizador],
    num([Ganho mês R$]) as [Ganho mês R$],
    [Qtde MO],
    [Melhoria replicavel],
    [Nome setor replicável],
    [Pessoas Mês],
    [Pessoas Quadrimestre],
    [R$ Mês] as [R$ Mês TC],
    [R$ Quadrimestre] as [R$ Quadrimestre TC],
    [Ganho MP Mês] as [R$ Mês MP],
    [Ganho MP Quadrimestre] as [R$ Quadrimestre MP],
    [Gerente idealizador],
    [É replicação],
    [Mês anterior],
    Engenharia,
    [Cargo elegivel],
    Cargo,
    [Categoria dos cargos],
    Ceil(Month([Data da FAP])/2) 		as %id_periodo,
    FileName() 							as nome_arquivo_base_melhoria,
    //text(Date([Data da FAP],'MMM/YYYY')) as [mes ano],
//     Lookup('h/mês/Func', 'Area', [Setor Macro], 'carga horaria') as [ch mes],
//     Lookup('Salário', 'mes ano', text(Date([Data da FAP],'MM/YYYY')), 'salario') as [salario],
    if(Match([Tipo de Melhoria], '$(vConsumo)', '$(vTrocaMP)') = 0, ([T.C. Anterior] - [T.C. Atual]) * (MIX / 100) * [1º Mês] / 60, 0) as [hrs ganhas 1],
    if(Match([Tipo de Melhoria], '$(vConsumo)', '$(vTrocaMP)') = 0, ([T.C. Anterior] - [T.C. Atual]) * (MIX / 100) * [2º Mês] / 60, 0) as [hrs ganhas 2],
    if(Match([Tipo de Melhoria], '$(vConsumo)', '$(vTrocaMP)') = 0, ([T.C. Anterior] - [T.C. Atual]) * (MIX / 100) * [3º Mês] / 60, 0) as [hrs ganhas 3],
    if(Match([Tipo de Melhoria], '$(vConsumo)', '$(vTrocaMP)') = 0, ([T.C. Anterior] - [T.C. Atual]) * (MIX / 100) * [4º Mês] / 60, 0) as [hrs ganhas 4],
    if([Tipo de Melhoria] = '$(vConsumo)' and not Setor like 'Ting*', (Cons_Anterior - Cons_Atual) * (MIX / 100) * [Preço M.P.] * [1º Mês], 0) as [g consumo 1],
    if([Tipo de Melhoria] = '$(vConsumo)' and not Setor like 'Ting*', (Cons_Anterior - Cons_Atual) * (MIX / 100) * [Preço M.P.] * [2º Mês], 0) as [g consumo 2],
    if([Tipo de Melhoria] = '$(vConsumo)' and not Setor like 'Ting*', (Cons_Anterior - Cons_Atual) * (MIX / 100) * [Preço M.P.] * [3º Mês], 0) as [g consumo 3],
    if([Tipo de Melhoria] = '$(vConsumo)' and not Setor like 'Ting*', (Cons_Anterior - Cons_Atual) * (MIX / 100) * [Preço M.P.] * [4º Mês], 0) as [g consumo 4],
    if([Tipo de Melhoria] = '$(vTrocaMP)' or Setor like 'Ting*', ([Custo Par Anterior] - [Custo Par Atual]) * (MIX / 100) * [1º Mês], 0) as [ganho troca MP 1],
    if([Tipo de Melhoria] = '$(vTrocaMP)' or Setor like 'Ting*', ([Custo Par Anterior] - [Custo Par Atual]) * (MIX / 100) * [2º Mês], 0) as [ganho troca MP 2],
    if([Tipo de Melhoria] = '$(vTrocaMP)' or Setor like 'Ting*', ([Custo Par Anterior] - [Custo Par Atual]) * (MIX / 100) * [3º Mês], 0) as [ganho troca MP 3],
    if([Tipo de Melhoria] = '$(vTrocaMP)' or Setor like 'Ting*', ([Custo Par Anterior] - [Custo Par Atual]) * (MIX / 100) * [4º Mês], 0) as [ganho troca MP 4]
FROM [$(vPathFato(f_base_melhorias_TC_*))] (qvd)
WHERE [Data da FAP] > '01/01/2020';

//############### Carrega a carga horária de trabalho #####################
Left Join(base_melhoria_temp)
// [tbl_carga_horarioa]:
LOAD
    estabelecimento &'|'& Area &'|'& [mes ano] 	AS %ChaveEstabSetorMacroPeiodoCH,
    Ch											As [CH dia],
    dias										As [Qtde dias trabalhados no mês],
    [h/mês/Func]								As [Hrs trabalhadas mês]
FROM [$(vPathFile(carga_horaria))]
(ooxml, embedded labels, table is [carga horaria]);

//############### Carrega os salarios #####################
Left Join(base_melhoria_temp)
//[tbl_salario]:
LOAD
	estabelecimento &'|'& [mes ano]									As %ChaveEstabPeiodoSalario,
    Num(Custo) as "Custo funcionario"
FROM [$(vPathFile(custo_funcionario))]
(ooxml, embedded labels, table is [Custo funcionario]);


// Left Join(base_melhoria_temp)
// Load
// 	id as %id_periodo,
//     bimestre as bimeste_sem_ano
// Resident Periodo;

//############### Monta a base de melhorias #####################
base_melhoria:
Load
// 	%ChaveEstabSetorMacroPeiodoCH,
//     %ChaveEstabPeiodoSalario,
    [Estab.] & '|' & Setor & '|' & Código & '|' & Text(Date([Data da FAP],'DD/MM/YYYY')) & '|' & Text(Date([Data da FAP] + 30,'DD/MM/YYYY')) as %ChaveVolume,
    [Estab.]  &'|'& Setor &'|'& Date([Data da FAP],'YYYY/MM')					AS %ChaveEstabSetorPeriodo,
    [Estab.]  &'|'& area_melhoria &'|'& Date([Data da FAP],'YYYY/MM')			AS %ChaveEstabSetorMacroPeriodo,
    [Estab.] &'|'& Setor &'|'& Processista 										As %ChaveEstabSetorProcessista,
//     [Estab.] &'|'& [Setor Ganhos] &'|'& Date([Data da FAP],'YYYY/MM')	As %ChaveEstabSetorGanhoMesAno,
	[Estab.] &'|'& Setor 														As %ChaveEstabSetor,
//     [Local Produção],
    [Tipo de Melhoria],
    Estab. as Filial,
    //Gerente,
    Setor,
    Processista 																As [Nome analista de processo],
    [Nº F.A.P],
	[Data da FAP],
    if([Mês anterior] = 'Sim', [Data da FAP], Date([Data da FAP] + 30)) 		As [data fim melhoria],
    Código,
    If(Match(Len([Código]),5,7),Mid([Código],1,5), Null()) as [Codigo do produto],
    If(Match(Len([Código]),5,7),[Código], Null()) as [Codigo do componente],
    [Preço M.P.],
    Cons_Anterior,
    Cons_Atual,
    [Padrão Anterior],
    [Padrão Atual],
    [Efetivo Anterior],
    [Efetivo Atual],
    [T.C. Anterior],
    [T.C. Atual],
    MIX,
    Usuário,
    [Dia / Hora Inicio],
    [Dia / Hora Fim],
    Observação,
    [% Ganho],
    [Custo Par Anterior],
    [Custo Par Atual],
    Mês,
    Origem,
    [Idealizador],
    [Ganho mês R$] 														As [ganho mês outras melhorias],
    [Qtde MO],
    [Melhoria replicavel],
    [Nome setor replicável],
    [Pessoas Mês] 														As [ganho pessoas mês TC],
    [Pessoas Quadrimestre] 												As [ganho pessoas quadrimestre TC],
    [area_melhoria],
    [hrs ganhas 1],
    [hrs ganhas 2],
    [hrs ganhas 3],
    [hrs ganhas 4],
    [g consumo 1],
    [g consumo 2],
    [g consumo 3],
    [g consumo 4],
    [ganho troca MP 1],
    [ganho troca MP 2],
    [ganho troca MP 3],
    [ganho troca MP 4],
    [Hrs trabalhadas mês],
    [Gerente idealizador],
    [É replicação],
    if([Mês anterior] = 'Sim','Sim','Não') as [Mês anterior],
    Engenharia,
    [Cargo elegivel],
    Cargo,
    [Categoria dos cargos],
    "Custo funcionario",
    nome_arquivo_base_melhoria,
    //bimeste_sem_ano & '/' & Year([Data da FAP]) as Periodo,
//     bimeste_sem_ano & '/' & Year([Data da FAP]) & '|' & [Gerente idealizador] as %ChaveMeta,
    [1º Mês] 																		As [Volume mês],
    num([1º Mês]) + num([2º Mês]) + num([3º Mês]) + num([4º Mês]) 					As [Volume Quadrimestre],
	num([hrs ganhas 1]) / num([Hrs trabalhadas mês])								As [ganho pessoa 1],
    num([hrs ganhas 2]) / num([Hrs trabalhadas mês]) 								As [ganho pessoa 2],
    num([hrs ganhas 3]) / num([Hrs trabalhadas mês]) 								As [ganho pessoa 3],
    num([hrs ganhas 4]) / num([Hrs trabalhadas mês]) 								As [ganho pessoa 4],

    num([hrs ganhas 1]) / num([Hrs trabalhadas mês]) +
    num([hrs ganhas 2]) / num([Hrs trabalhadas mês]) +
    num([hrs ganhas 3]) / num([Hrs trabalhadas mês]) +
    num([hrs ganhas 4]) / num([Hrs trabalhadas mês]) 								As [ganho pessoas Quadrimestre],

    num([hrs ganhas 1]) / num([Hrs trabalhadas mês]) * "Custo funcionario"			As [ganho em reais 1],
    num([hrs ganhas 2]) / num([Hrs trabalhadas mês]) * "Custo funcionario"			As [ganho em reais 2],
    num([hrs ganhas 3]) / num([Hrs trabalhadas mês]) * "Custo funcionario"			As [ganho em reais 3],
    num([hrs ganhas 4]) / num([Hrs trabalhadas mês]) * "Custo funcionario"			As [ganho em reais 4],

    num([hrs ganhas 1]) / num([Hrs trabalhadas mês]) * "Custo funcionario" +
    num([hrs ganhas 2]) / num([Hrs trabalhadas mês]) * "Custo funcionario" +
    num([hrs ganhas 3]) / num([Hrs trabalhadas mês]) * "Custo funcionario" +
    num([hrs ganhas 4]) / num([Hrs trabalhadas mês]) * "Custo funcionario"			As [ganho em reais Quadrimestre],

    num([g consumo 1]) + num([ganho troca MP 1]) 									As [ganho consumo 1],
    num([g consumo 2]) + num([ganho troca MP 2]) 									As [ganho consumo 2],
    num([g consumo 3]) + num([ganho troca MP 3]) 									As [ganho consumo 3],
    num([g consumo 4]) + num([ganho troca MP 4]) 									As [ganho consumo 4],
    if(IsNull([R$ Mês TC]),0,num([R$ Mês TC])) 										As [ganho em R$ calculado na planilha]

Resident base_melhoria_temp;

//############### Monta a base de melhorias #####################
tbl_Produtos:
Load Distinct
    [Codigo do produto]
Resident base_melhoria Where not IsNull([Codigo do produto]);

tbl_Componentes:
Load Distinct
    [Codigo do componente]
Resident base_melhoria Where not IsNull([Codigo do componente]);


//############### Monta a base de melhorias mês anterior #####################
tbl_melhorias_mes_anterior_tmp:
Load
	[Nº F.A.P]											As "Numero fap mês anterior",
	[Data da FAP]  										As [Data da FAP Mês anterior],
    [Idealizador],
    Month([Data da FAP]) 								As "Mês da melhoria",
    Year([Data da FAP])                    				As [Ano da FAP Mês anterior],
    sum([ganho em reais 1]) + sum([ganho consumo 1]) 	As "Ganho mês anterior",
    sum([ganho pessoa 1]) 								As "Ganho pessoas mês anterior"
Resident base_melhoria
Where [Mês anterior] = 'Sim'
Group By
	[Nº F.A.P],
	[Data da FAP],
    [Idealizador]
;

// Left Join
// Load
// 	[Nº F.A.P] 						As "Numero fap mês anterior",
//     "Resultado da FAP" 				As "Resultado da FAP mês anterior"
// Resident Base_Aderencia;

Left Join
Load
  "Mês" as "Mês da melhoria",
  Bimestre
Resident tbl_bimestre;

tbl_melhorias_mes_anterior:
Load
	*,
    if("Ganho mês anterior" < 0, 'Perda', 'Ganho') 																As "Resultado da FAP mês anterior",
    Bimestre & '/' & Year([Data da FAP Mês anterior]) 															As "Mês-Mês/Ano bimestre Mês anterior",
    Bimestre & '/' & Year([Data da FAP Mês anterior]) & '|' & [Idealizador] & '|' & [Numero fap mês anterior] 	As %ChaveBimestreNomeIdealizador
Resident tbl_melhorias_mes_anterior_tmp;

/*
tbl_melhorias_mes_anterior_temp1:
Load distinct
	//*,
    Bimestre,
    Idealizador,
    [Ano da FAP Mês anterior],
    sum("Ganho mês anterior") as "Ganho mês anterior"
Resident tbl_melhorias_mes_anterior_tmp
Group By    Bimestre,    Idealizador,    [Ano da FAP Mês anterior];

tbl_melhorias_mes_anterior:
Load Bimestre,    Idealizador, "Ganho mês anterior",
    if("Ganho mês anterior" < 0, 'Perda', 'Ganho') 							  	As "Resultado da FAP mês anterior",
    Bimestre & '/' & [Ano da FAP Mês anterior] 										As "Mês-Mês/Ano bimestre Mês anterior",
    Bimestre & '/' & [Ano da FAP Mês anterior] & '|' & [Idealizador] 				As %ChaveBimestreNomeIdealizador
Resident tbl_melhorias_mes_anterior_temp1;

drop Table tbl_melhorias_mes_anterior_temp1;

*/





//############### Drops #####################

drop Fields "Mês da melhoria", Bimestre, [Idealizador] From tbl_melhorias_mes_anterior;

Drop Table base_melhoria_temp, tbl_melhorias_mes_anterior_tmp;//, Periodo;
```
