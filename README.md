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
- `gerar_base_ficticia.py` – gera a base **fictícia** usada para desenvolvimento e testes
- `vendas_lanchonete_ficticia.xlsx` – base fictícia de exemplo

## Colunas esperadas na planilha
`ID_Pedido, Data, Horario (HH:MM), Produto, Categoria, Quantidade, Valor_Unitario, Valor_Total, Forma_Pagamento`

## Indicadores
Faturamento, nº de pedidos, ticket médio, itens vendidos, evolução diária, desempenho por dia da
semana e horário, produtos mais/menos vendidos, participação por categoria e por forma de pagamento.

> Os dados do repositório são fictícios. Nenhuma informação real de estabelecimento é publicada.
