"""Dashboard de Análise de Vendas para Pequenos Comércios.

Executar: streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from tratamento import DIAS, carregar, indicadores, tratar

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("📊 Dashboard de Análise de Vendas")
st.caption("Solução de BI simples para pequenos comércios – Atividade Extensionista II (UNINTER)")

# ---------- Entrada de dados ----------
with st.sidebar:
    st.header("Dados")
    arq = st.file_uploader("Envie a planilha de vendas (.xlsx ou .csv)", type=["xlsx", "csv"])
    usar_exemplo = st.checkbox("Usar base de exemplo (fictícia)", value=arq is None)

fonte = arq if arq is not None else ("vendas_lanchonete_ficticia.xlsx" if usar_exemplo else None)
if fonte is None:
    st.info("Envie uma planilha ou marque a opção de base de exemplo na barra lateral.")
    st.stop()

try:
    bruto = carregar(fonte)
except (ValueError, FileNotFoundError) as e:
    st.error(f"Não foi possível ler a planilha: {e}")
    st.stop()

base, relatorio = tratar(bruto)
if arq is None:
    st.warning("Exibindo **dados fictícios** de demonstração.")

# ---------- Filtros ----------
with st.sidebar:
    st.header("Filtros")
    dmin, dmax = base["Data"].min().date(), base["Data"].max().date()
    periodo = st.date_input("Período", (dmin, dmax), min_value=dmin, max_value=dmax)
    cats = st.multiselect("Categoria", sorted(base["Categoria"].unique()),
                          default=sorted(base["Categoria"].unique()))
    pgs = st.multiselect("Forma de pagamento", sorted(base["Forma_Pagamento"].unique()),
                         default=sorted(base["Forma_Pagamento"].unique()))

if isinstance(periodo, tuple) and len(periodo) == 2:
    ini, fim = periodo
else:
    ini = fim = periodo[0] if isinstance(periodo, tuple) else periodo
df = base[(base["Data"].dt.date >= ini) & (base["Data"].dt.date <= fim)
          & base["Categoria"].isin(cats) & base["Forma_Pagamento"].isin(pgs)]

if df.empty:
    st.warning("Nenhuma venda encontrada com os filtros selecionados.")
    st.stop()

# ---------- Indicadores ----------
k = indicadores(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturamento", brl(k["faturamento"]))
c2.metric("Pedidos", f'{k["pedidos"]:,}'.replace(",", "."))
c3.metric("Ticket médio", brl(k["ticket_medio"]))
c4.metric("Itens vendidos", f'{k["itens"]:,}'.replace(",", "."))

aba1, aba2, aba3, aba4 = st.tabs(["Evolução e período", "Produtos", "Pagamentos", "Qualidade dos dados"])

with aba1:
    dia = df.groupby("Data", as_index=False)["Valor_Total"].sum()
    st.plotly_chart(px.line(dia, x="Data", y="Valor_Total", title="Faturamento diário",
                            labels={"Valor_Total": "Faturamento (R$)"}), width='stretch')
    col_a, col_b = st.columns(2)
    sem = (df.groupby("Dia_Semana")["Valor_Total"].sum().reindex(DIAS).reset_index())
    col_a.plotly_chart(px.bar(sem, x="Dia_Semana", y="Valor_Total", title="Faturamento por dia da semana",
                              labels={"Valor_Total": "R$", "Dia_Semana": ""}), width='stretch')
    hora = df.groupby("Hora")["ID_Pedido"].nunique().reset_index(name="Pedidos")
    col_b.plotly_chart(px.bar(hora, x="Hora", y="Pedidos", title="Pedidos por horário (movimento)"),
                       width='stretch')
    pico = hora.loc[hora["Pedidos"].idxmax()]
    melhor = sem.loc[sem["Valor_Total"].idxmax()]
    st.info(f"**Insights:** maior movimento às **{int(pico['Hora'])}h** "
            f"({int(pico['Pedidos'])} pedidos no período); dia de maior faturamento: **{melhor['Dia_Semana']}**.")

with aba2:
    prod = (df.groupby("Produto", as_index=False)
              .agg(Quantidade=("Quantidade", "sum"), Faturamento=("Valor_Total", "sum"))
              .sort_values("Faturamento", ascending=False))
    prod["Participação (%)"] = (prod["Faturamento"] / prod["Faturamento"].sum() * 100).round(1)
    col_a, col_b = st.columns(2)
    col_a.plotly_chart(px.bar(prod.sort_values("Quantidade").tail(10), x="Quantidade", y="Produto",
                              orientation="h", title="Top 10 mais vendidos (unidades)"),
                       width='stretch')
    col_b.plotly_chart(px.bar(prod.sort_values("Quantidade").head(5), x="Quantidade", y="Produto",
                              orientation="h", title="5 menos vendidos (unidades)"),
                       width='stretch')
    cat = df.groupby("Categoria", as_index=False)["Valor_Total"].sum()
    st.plotly_chart(px.pie(cat, names="Categoria", values="Valor_Total",
                           title="Participação das categorias no faturamento"), width='stretch')
    st.dataframe(prod, width='stretch', hide_index=True)

with aba3:
    pg = df.groupby("Forma_Pagamento", as_index=False)["Valor_Total"].sum()
    st.plotly_chart(px.pie(pg, names="Forma_Pagamento", values="Valor_Total",
                           title="Faturamento por forma de pagamento"), width='stretch')

with aba4:
    st.write("Resumo do tratamento aplicado à planilha enviada:")
    st.table(pd.DataFrame(relatorio.items(), columns=["Verificação", "Quantidade"]).astype(str))
    st.caption("Linhas duplicadas e inválidas são removidas; valor total ausente é recalculado "
               "(quantidade × valor unitário); pagamento ausente vira “Não informado”.")
