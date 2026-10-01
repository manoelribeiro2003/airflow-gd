```qlik
Sum(
	{<
   	[Categoria Situação meta]={'Considera'},
    [Grupo Cargo meta]-={'Não Elegível'},
  	[Gerente Meta tabela meta]-={'Sul', 'Rossi'}
  >}
  [Realizado meta] //[Qtde Pessoas com melhorias]
)
```
