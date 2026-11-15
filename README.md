# Dashboard de Análise de Vendas para Pequenos Comércios

Projeto da Atividade Extensionista II (CST em Ciência de Dados – UNINTER).
Solução simples de Business Intelligence em Python: importa uma planilha de vendas,
valida e trata os dados, calcula indicadores e apresenta um dashboard interativo.

## Como executar
```
pip install -r requirements.txt
streamlit run app.py
```

## Arquivos
- `app.py` – interface do dashboard (Streamlit + Plotly)
- `tratamento.py` – leitura, validação de inconsistências e cálculo de indicadores
- `insights.py` – análises e textos de storytelling (horários de pico, curva ABC, combos, evolução) com dicas de ação
- `.streamlit/config.toml` – tema visual (creme, ketchup e mostarda)
- `gerar_base_ficticia.py` – gera a base **fictícia** usada para desenvolvimento e testes
- `vendas_lanchonete_ficticia.xlsx` – base fictícia de exemplo

## Colunas esperadas na planilha
`ID_Pedido, Data, Horario (HH:MM), Produto, Categoria, Quantidade, Valor_Unitario, Valor_Total, Forma_Pagamento`

## Resumo e decisões
A primeira aba conta a história dos dados em quatro perguntas (quando vende, o que sustenta o faturamento, como o cliente compra, para onde o negócio caminha). Cada bloco traz os achados calculados da planilha e uma dica de ação. As estimativas são simulações simples e não consideram custos.

## Indicadores
Faturamento, nº de pedidos, ticket médio, itens vendidos, evolução diária, desempenho por dia da
semana e horário, produtos mais/menos vendidos, participação por categoria e por forma de pagamento.

> Os dados do repositório são fictícios. Nenhuma informação real de estabelecimento é publicada.
