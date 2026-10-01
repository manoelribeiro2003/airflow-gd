```dax
% OEE = 1 - [% Disponibilidade] - [% Setup] - [% Perfomance] - [% Qualidade]
```

```dax
% Disponibilidade = 
VAR Tempo_Disp = CALCULATE(SUM(fDisponibilidade[tempo_parada]), fDisponibilidade[des_familia]<>"Setup")
VAR Tempo_Util = [Soma Segundos Úteis]

RETURN 
DIVIDE(Tempo_Disp, Tempo_Util, 0)
```

```dax
% Perfomance = 
VAR Perf = ([Soma de Ganho Performance] + [Soma de Perda Performance] + [Soma de Perdas QV/MI])
VAR Temp_Util = [Soma Segundos Úteis]

RETURN 
DIVIDE(Perf, Temp_Util, 0)

#===========================================================
Soma de Ganho Performance = SUM(fPerformace_Ciclos[soma_ganho_ciclo])

Soma de Perda Performance = SUM(fPerformace_Ciclos[soma_perda_ciclo])

Soma de Perdas QV/MI = SUM(fPerformace_Perdas[tempo_perda])

Soma Segundos Úteis = SUM('fTempo_Útil'[tempo_util])

```

```dax
% Setup = 
VAR Tempo_Setup = CALCULATE(SUM(fDisponibilidade[tempo_parada]), fDisponibilidade[des_familia]="Setup")
VAR Tempo_Util = [Soma Segundos Úteis]

RETURN
DIVIDE(Tempo_Setup, Tempo_Util, 0)
```

```dax
% Qualidade = 
VAR Tempo_Qualidade = SUM(fQualidade[tempo_apontamento])
VAR Tempo_Util = [Soma Segundos Úteis]

RETURN 
DIVIDE(Tempo_Qualidade, Tempo_Util, 0)
```
