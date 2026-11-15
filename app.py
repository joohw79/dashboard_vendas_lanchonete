"""Dashboard de Análise de Vendas para Pequenos Comércios.

Executar: streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from tratamento import DIAS, carregar, indicadores, tratar

st.set_page_config(page_title="Dashboard de Vendas", page_icon="🍔", layout="wide")

# ---------- Identidade visual (tema lanchonete: creme, ketchup e mostarda) ----------
KETCHUP, AZUL, MOSTARDA, VERDE, ROXO = "#C8361B", "#2563A8", "#B8860B", "#2E8B57", "#8A4B9A"
TINTA, TINTA_SUAVE, GRADE, CINZA = "#2B2118", "#7A6A5A", "#E8DCC9", "#9A8F82"
COR_PAGAMENTO = {"Pix": KETCHUP, "Cartão de Crédito": AZUL, "Cartão de Débito": MOSTARDA,
                 "Dinheiro": VERDE, "Não informado": CINZA}
COR_CATEGORIA = {"Lanches": KETCHUP, "Porções": AZUL, "Salgados": MOSTARDA,
                 "Bebidas": VERDE, "Sobremesas": ROXO}

st.markdown(f"""
<style>
  #MainMenu, footer {{visibility: hidden;}}
  .block-container {{padding-top: 1.6rem; max-width: 1200px;}}
  html, body, [class*="css"] {{font-family: "Inter", "Segoe UI", system-ui, sans-serif;}}
  .hero {{background: linear-gradient(120deg, {KETCHUP} 0%, #E4572E 100%); color: #fff;
          border-radius: 18px; padding: 22px 28px; margin-bottom: 18px;}}
  .hero h1 {{font-size: 1.7rem; margin: 0; font-weight: 700; letter-spacing: -0.5px; color: #fff; padding: 0;}}
  .hero p {{margin: 4px 0 0 0; opacity: .9; font-size: .95rem;}}
  [data-testid="stMetric"] {{background: #fff; border: 1px solid {GRADE}; border-left: 5px solid {MOSTARDA};
          border-radius: 14px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(43,33,24,.06);}}
  [data-testid="stMetricLabel"] {{color: {TINTA_SUAVE};}}
  [data-testid="stMetricValue"] {{color: {TINTA}; font-weight: 700; font-size: 1.5rem;}}
  [data-testid="stMetricValue"] > div {{overflow: visible; text-overflow: clip; white-space: nowrap;}}
  button[data-baseweb="tab"] {{font-weight: 600; color: {TINTA_SUAVE};}}
  button[data-baseweb="tab"][aria-selected="true"] {{color: {KETCHUP};}}
  .insight {{background: #FFF3D6; border-left: 5px solid {MOSTARDA}; border-radius: 10px;
          padding: 12px 16px; margin-top: 8px; color: {TINTA};}}
  [data-testid="stSidebar"] {{border-right: 1px solid {GRADE};}}
  .rodape {{color: {TINTA_SUAVE}; font-size: .8rem; text-align: center; margin-top: 28px;}}
</style>
""", unsafe_allow_html=True)


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estilo(fig, titulo, legenda=False):
    """Visual minimalista: fundo transparente, grade suave e títulos discretos."""
    fig.update_layout(
        title=dict(text=titulo, x=0, font=dict(size=16, color=TINTA)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA_SUAVE, size=12), margin=dict(l=8, r=8, t=50, b=8),
        showlegend=legenda, legend=dict(orientation="h", y=-0.12, x=0),
        hoverlabel=dict(bgcolor="#fff", font_color=TINTA, bordercolor=GRADE),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRADE, title=None)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, title=None)
    return fig


st.markdown("""
<div class="hero">
  <h1>🍔 Painel de Vendas</h1>
  <p>Indicadores simples para decidir melhor no dia a dia da lanchonete</p>
</div>
""", unsafe_allow_html=True)

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
st.write("")

aba1, aba2, aba3, aba4 = st.tabs(["Evolução e período", "Produtos", "Pagamentos", "Qualidade dos dados"])

with aba1:
    dia = df.groupby("Data", as_index=False)["Valor_Total"].sum()
    fig = px.line(dia, x="Data", y="Valor_Total", labels={"Valor_Total": "Faturamento (R$)"},
                  color_discrete_sequence=[KETCHUP])
    fig.update_traces(line_width=2.2, hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>")
    st.plotly_chart(estilo(fig, "Faturamento diário"), width="stretch")

    col_a, col_b = st.columns(2)
    sem = df.groupby("Dia_Semana")["Valor_Total"].sum().reindex(DIAS).reset_index()
    f1 = px.bar(sem, x="Dia_Semana", y="Valor_Total", color_discrete_sequence=[KETCHUP])
    f1.update_traces(marker_cornerradius=6, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
    col_a.plotly_chart(estilo(f1, "Faturamento por dia da semana"), width="stretch")

    hora = df.groupby("Hora")["ID_Pedido"].nunique().reset_index(name="Pedidos")
    f2 = px.bar(hora, x="Hora", y="Pedidos", color_discrete_sequence=[MOSTARDA])
    f2.update_traces(marker_cornerradius=6, hovertemplate="%{x}h<br>%{y} pedidos<extra></extra>")
    f2.update_xaxes(dtick=1)
    col_b.plotly_chart(estilo(f2, "Pedidos por horário (movimento)"), width="stretch")

    pico = hora.loc[hora["Pedidos"].idxmax()]
    melhor = sem.loc[sem["Valor_Total"].idxmax()]
    st.markdown(f"""<div class="insight"><b>Insights:</b> maior movimento às <b>{int(pico['Hora'])}h</b>
        ({int(pico['Pedidos'])} pedidos no período); dia de maior faturamento:
        <b>{melhor['Dia_Semana']}</b>.</div>""", unsafe_allow_html=True)

with aba2:
    prod = (df.groupby("Produto", as_index=False)
              .agg(Quantidade=("Quantidade", "sum"), Faturamento=("Valor_Total", "sum"))
              .sort_values("Faturamento", ascending=False))
    prod["Participação (%)"] = (prod["Faturamento"] / prod["Faturamento"].sum() * 100).round(1)
    col_a, col_b = st.columns(2)
    top = prod.sort_values("Quantidade").tail(10)
    f3 = px.bar(top, x="Quantidade", y="Produto", orientation="h", color_discrete_sequence=[KETCHUP])
    f3.update_traces(marker_cornerradius=6, hovertemplate="%{y}<br>%{x} unidades<extra></extra>")
    col_a.plotly_chart(estilo(f3, "Top 10 mais vendidos (unidades)"), width="stretch")
    low = prod.sort_values("Quantidade").head(5)
    f4 = px.bar(low, x="Quantidade", y="Produto", orientation="h", color_discrete_sequence=[MOSTARDA])
    f4.update_traces(marker_cornerradius=6, hovertemplate="%{y}<br>%{x} unidades<extra></extra>")
    col_b.plotly_chart(estilo(f4, "5 menos vendidos (unidades)"), width="stretch")

    cat = df.groupby("Categoria", as_index=False)["Valor_Total"].sum()
    f5 = px.pie(cat, names="Categoria", values="Valor_Total", hole=0.58,
                color="Categoria", color_discrete_map=COR_CATEGORIA)
    f5.update_traces(textinfo="label+percent", insidetextorientation="horizontal", marker=dict(line=dict(color="#FBF6EE", width=3)),
                     hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>")
    st.plotly_chart(estilo(f5, "Participação das categorias no faturamento", legenda=True), width="stretch")
    st.dataframe(prod, width="stretch", hide_index=True)

with aba3:
    pg = df.groupby("Forma_Pagamento", as_index=False)["Valor_Total"].sum()
    f6 = px.pie(pg, names="Forma_Pagamento", values="Valor_Total", hole=0.58,
                color="Forma_Pagamento", color_discrete_map=COR_PAGAMENTO)
    f6.update_traces(textinfo="label+percent", insidetextorientation="horizontal", marker=dict(line=dict(color="#FBF6EE", width=3)),
                     hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>")
    st.plotly_chart(estilo(f6, "Faturamento por forma de pagamento", legenda=True), width="stretch")

with aba4:
    st.write("Resumo do tratamento aplicado à planilha enviada:")
    st.table(pd.DataFrame(relatorio.items(), columns=["Verificação", "Quantidade"]).astype(str))
    st.caption("Linhas duplicadas e inválidas são removidas; valor total ausente é recalculado "
               "(quantidade × valor unitário); pagamento ausente vira “Não informado”.")

st.markdown('<div class="rodape">Atividade Extensionista II · CST em Ciência de Dados · UNINTER</div>',
            unsafe_allow_html=True)
