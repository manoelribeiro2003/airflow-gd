
```qlik

sum( {< [Mês anterior]-={'Sim'}, [Resultado da FAP dNumeroFAP]={'Ganho'} , [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho em reais 1]) +
sum( {< [Mês anterior]-={'Sim'}, [Resultado da FAP dNumeroFAP]={'Ganho'} , [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho consumo 1]) +
sum( {< [Resultado da FAP dNumeroFAP]={'Ganho'} , [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho mês outras melhorias]) +
sum( {< [Resultado da FAP mês anterior]={'Ganho'} , [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [Ganho mês anterior])

+


sum( {< [Mês anterior]-={'Sim'}, [Resultado da FAP dNumeroFAP]={'Perda'}, [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho em reais 1]) +
sum( {< [Mês anterior]-={'Sim'}, [Resultado da FAP dNumeroFAP]={'Perda'}, [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho consumo 1]) +
sum( {< [Resultado da FAP dNumeroFAP]={'Perda'}, [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [ganho mês outras melhorias]) +
sum( {< [Resultado da FAP mês anterior]={'Perda'}, [status dNumeroFAP]-={'Falha no fluxo','Reprovado','Tempo de aprovação expirado'} >} [Ganho mês anterior])

```
