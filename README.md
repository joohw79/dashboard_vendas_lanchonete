# Painel de Vendas para Pequenos Comércios

Projeto da Atividade Extensionista II (CST em Ciência de Dados – UNINTER).
Dashboard de análise de vendas para uma lanchonete de bairro (São Paulo – SP): importa uma planilha, valida e trata os dados, calcula indicadores e apresenta gráficos e recomendações de ação.

**Acesse o painel online:** https://joohw79.github.io/dashboard_vendas_lanchonete/

## Como usar
1. Abra o link acima (ou o arquivo `index.html` no navegador). O painel já carrega uma base fictícia de demonstração.
2. Para analisar outra planilha, clique em **Enviar planilha (.xlsx ou .csv)**. O arquivo é lido no próprio navegador e não é enviado a nenhum servidor.
3. Use os filtros de período, categoria e forma de pagamento e navegue pelas abas.

## Colunas esperadas na planilha
`ID_Pedido, Data, Horario (HH:MM), Produto, Categoria, Quantidade, Valor_Unitario, Valor_Total, Forma_Pagamento`

## Estrutura
- `index.html`, `css/`, `js/` – painel em HTML, CSS e JavaScript (`tratamento.js` trata os dados, `insights.js` gera as análises e dicas, `app.js` monta a interface)
- `vendor/` – bibliotecas Plotly.js (gráficos) e SheetJS (leitura de Excel), incluídas localmente
- `dados/exemplo.js` – base fictícia de demonstração embutida
- `versao_python/` – versão alternativa em Python/Streamlit e o gerador da base fictícia (`gerar_base_ficticia.py`)

Para executar a versão Python: `cd versao_python && pip install -r requirements.txt && streamlit run app.py`

> Os dados do repositório são fictícios. Nenhuma informação real de estabelecimento é publicada.
