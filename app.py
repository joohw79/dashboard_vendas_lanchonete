"""Dashboard de Análise de Vendas para Pequenos Comércios.

Executar: streamlit run app.py
"""
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import insights as ins
from tratamento import DIAS, carregar, indicadores, tratar

st.set_page_config(page_title="Dashboard de Vendas", page_icon="🍔", layout="wide")

# ---------- Identidade visual (tema lanchonete: creme, ketchup e mostarda) ----------
KETCHUP, AZUL, MOSTARDA, VERDE, ROXO = "#C8361B", "#2563A8", "#B8860B", "#2E8B57", "#8A4B9A"
TINTA, TINTA_SUAVE, GRADE, CINZA, AREIA = "#2B2118", "#7A6A5A", "#E8DCC9", "#9A8F82", "#D9C7A8"
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
  [data-testid="stSidebar"] {{border-right: 1px solid {GRADE};}}
  .rodape {{color: {TINTA_SUAVE}; font-size: .8rem; text-align: center; margin-top: 28px;}}
  .cap {{background: #fff; border: 1px solid {GRADE}; border-radius: 16px; padding: 18px 20px;
         box-shadow: 0 2px 8px rgba(43,33,24,.05);}}
  .cap .tag {{font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: {KETCHUP};}}
  .cap h3 {{margin: 2px 0 10px 0; font-size: 1.2rem; font-weight: 700; color: {TINTA}; padding: 0;}}
  .cap ul {{margin: 0 0 12px 0; padding-left: 1.1rem; color: {TINTA}; line-height: 1.5;}}
  .cap li {{margin-bottom: 6px;}}
  .dica {{background: #FFF3D6; border-left: 5px solid {MOSTARDA}; border-radius: 10px;
          padding: 10px 14px; color: {TINTA}; font-size: .92rem; line-height: 1.45;}}
  .resumo {{background: {TINTA}; color: #FBF6EE; border-radius: 16px; padding: 18px 22px; margin-bottom: 18px;}}
  .resumo h3 {{color: #FBF6EE; margin: 0 0 8px 0; font-size: 1.1rem; padding: 0;}}
  .resumo ol {{margin: 0; padding-left: 1.2rem; line-height: 1.6;}}
  .resumo b {{color: #F6C453;}}
  .vazio {{color: {TINTA_SUAVE}; font-size: .9rem;}}
</style>
""", unsafe_allow_html=True)


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estilo(fig, titulo, legenda=False, altura=None):
    """Visual minimalista: fundo transparente, grade suave e títulos discretos."""
    fig.update_layout(
        title=dict(text=titulo, x=0, font=dict(size=15, color=TINTA)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA_SUAVE, size=12), margin=dict(l=8, r=8, t=46, b=8),
        showlegend=legenda, legend=dict(orientation="h", y=-0.12, x=0),
        hoverlabel=dict(bgcolor="#fff", font_color=TINTA, bordercolor=GRADE),
        height=altura,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRADE, title=None)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, title=None)
    return fig


def mostrar(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def barras_h(dados, x, y, cor, titulo, altura=None, texto=None):
    f = px.bar(dados, x=x, y=y, orientation="h", color_discrete_sequence=[cor], text=texto)
    f.update_traces(marker_cornerradius=6, textposition="outside", cliponaxis=False)
    return estilo(f, titulo, altura=altura)


def cartao(cap: dict):
    """Capítulo de storytelling: título, achados e dica de ação."""
    if not cap["pontos"]:
        corpo = '<div class="vazio">Dados insuficientes no período/filtros selecionados para este bloco.</div>'
    else:
        itens = "".join(f"<li>{p}</li>" for p in cap["pontos"])
        corpo = f"<ul>{itens}</ul>"
        if cap["dica"]:
            corpo += f'<div class="dica">💡 <b>Dica:</b> {html.escape(cap["dica"])}</div>'
    st.markdown(f'<div class="cap"><span class="tag">{cap["tag"]}</span><h3>{cap["titulo"]}</h3>{corpo}</div>',
                unsafe_allow_html=True)


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

m = ins.metricas(df)
caps = ins.capitulos(m)
abc = m["abc"]

aba0, aba1, aba2, aba3, aba4 = st.tabs(
    ["Resumo e decisões", "Vendas no tempo", "Cardápio", "Pagamentos", "Qualidade dos dados"])

# ====== RESUMO E DECISÕES (storytelling) ======
with aba0:
    prios = ins.prioridades(m)
    if prios:
        itens = "".join(f"<li>{p}</li>" for p in prios)
        st.markdown(f'<div class="resumo"><h3>Por onde começar</h3><ol>{itens}</ol></div>', unsafe_allow_html=True)

    # 1) Quando: mapa de calor dia x hora
    esq, dir_ = st.columns([5, 7], gap="large")
    with esq:
        cartao(caps[0])
    with dir_:
        mapa = (df.groupby(["Dia_Semana", "Hora"])["ID_Pedido"].nunique()
                  .unstack(fill_value=0).reindex(DIAS).fillna(0))
        f = go.Figure(go.Heatmap(
            z=mapa.values, x=[f"{int(h)}h" for h in mapa.columns], y=list(mapa.index),
            colorscale=[[0, "#FBF1E3"], [1, KETCHUP]], xgap=3, ygap=3,
            hovertemplate="%{y} às %{x}<br>%{z} pedidos<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, title="")))
        f.update_yaxes(autorange="reversed", showgrid=False)
        mostrar(estilo(f, "Mapa de movimento: pedidos por dia e horário", altura=380))

    st.write("")
    # 2) O que vende: curva ABC
    esq, dir_ = st.columns([5, 7], gap="large")
    with esq:
        cartao(caps[1])
    with dir_:
        top = abc.head(10).copy()
        resto = abc.iloc[10:]
        if len(resto):
            top.loc[f"Demais ({len(resto)} itens)"] = [resto["faturamento"].sum(),
                                                       resto["participacao"].sum(), False]
        top = top.reset_index().rename(columns={"index": "Produto"})
        top["Classe"] = top["classe_a"].map({True: "Itens que somam 80% do faturamento", False: "Demais itens"})
        top["rotulo"] = top["participacao"].map(lambda v: f"{v:.1f}%".replace(".", ","))
        f = px.bar(top.iloc[::-1], x="participacao", y="Produto", orientation="h", color="Classe", text="rotulo",
                   color_discrete_map={"Itens que somam 80% do faturamento": KETCHUP, "Demais itens": AREIA})
        f.update_traces(marker_cornerradius=6, textposition="outside", cliponaxis=False,
                        hovertemplate="%{y}<br>%{x:.1f}% do faturamento<extra></extra>")
        f.update_xaxes(visible=False, range=[0, float(top["participacao"].max()) * 1.2])
        f.update_layout(legend_title_text="")
        mostrar(estilo(f, "Quem sustenta o faturamento (participação por item)", legenda=True, altura=400))

    st.write("")
    # 3) Como compra
    esq, dir_ = st.columns([5, 7], gap="large")
    with esq:
        cartao(caps[2])
    with dir_:
        if "ped" in m:
            ped = m["ped"].copy()
            ped["faixa"] = ped["itens"].clip(upper=4).map({1: "1 item", 2: "2 itens", 3: "3 itens", 4: "4 ou mais"})
            g = ped.groupby("faixa").agg(pedidos=("valor", "size"), ticket=("valor", "mean"))
            g = g.reindex(["1 item", "2 itens", "3 itens", "4 ou mais"]).dropna().reset_index()
            g["pct"] = g["pedidos"] / g["pedidos"].sum() * 100
            g["rotulo"] = [f"{p:.0f}% · ticket {brl(t)}" for p, t in zip(g["pct"], g["ticket"])]
            f = px.bar(g, x="faixa", y="pct", color_discrete_sequence=[MOSTARDA], text="rotulo")
            f.update_traces(marker_cornerradius=6, textposition="outside", cliponaxis=False,
                            hovertemplate="%{x}<br>%{y:.1f}% dos pedidos<extra></extra>")
            f.update_yaxes(visible=False)
            mostrar(estilo(f, "Pedidos por número de itens (e ticket médio de cada grupo)", altura=270))
        if m.get("pares"):
            pares = pd.DataFrame([(f"{a} + {b}", n) for (a, b), n in m["pares"]], columns=["Par", "Pedidos"])
            mostrar(barras_h(pares.iloc[::-1], "Pedidos", "Par", KETCHUP, "Combinações mais pedidas juntas",
                             altura=300, texto="Pedidos"))

    st.write("")
    # 4) Evolução
    esq, dir_ = st.columns([5, 7], gap="large")
    with esq:
        cartao(caps[3])
    with dir_:
        dia = df.groupby("Data", as_index=False)["Valor_Total"].sum()
        dia["media7"] = dia["Valor_Total"].rolling(7, min_periods=4).mean()
        f = go.Figure()
        f.add_scatter(x=dia["Data"], y=dia["Valor_Total"], name="Dia", mode="lines",
                      line=dict(color=KETCHUP, width=1), opacity=0.3,
                      hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>")
        f.add_scatter(x=dia["Data"], y=dia["media7"], name="Média de 7 dias", mode="lines",
                      line=dict(color=KETCHUP, width=3),
                      hovertemplate="%{x|%d/%m/%Y}<br>média R$ %{y:,.2f}<extra></extra>")
        mostrar(estilo(f, "Faturamento diário e tendência (média móvel de 7 dias)", legenda=True, altura=330))

# ====== VENDAS NO TEMPO ======
with aba1:
    col_a, col_b = st.columns(2)
    sem = df.groupby(["Data", "Dia_Semana"])["Valor_Total"].sum().groupby("Dia_Semana").mean().reindex(DIAS).reset_index()
    f1 = px.bar(sem, x="Dia_Semana", y="Valor_Total", color_discrete_sequence=[KETCHUP])
    f1.update_traces(marker_cornerradius=6, hovertemplate="%{x}<br>média R$ %{y:,.2f} por dia<extra></extra>")
    with col_a:
        mostrar(estilo(f1, "Faturamento médio por dia da semana"))
    hora = df.groupby("Hora")["ID_Pedido"].nunique().reset_index(name="Pedidos")
    f2 = px.bar(hora, x="Hora", y="Pedidos", color_discrete_sequence=[MOSTARDA])
    f2.update_traces(marker_cornerradius=6, hovertemplate="%{x}h<br>%{y} pedidos<extra></extra>")
    f2.update_xaxes(dtick=1)
    with col_b:
        mostrar(estilo(f2, "Pedidos por horário"))
    mes = df.groupby("Mes", as_index=False)["Valor_Total"].sum()
    if len(mes) > 1:
        mes["Mes"] = mes["Mes"].map(ins.mes_pt)
        f3 = px.bar(mes, x="Mes", y="Valor_Total", color_discrete_sequence=[KETCHUP])
        f3.update_traces(marker_cornerradius=6, width=0.45, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        f3.update_xaxes(type="category")
        mostrar(estilo(f3, "Faturamento por mês", altura=300))

# ====== CARDÁPIO ======
with aba2:
    prod = (df.groupby("Produto", as_index=False)
              .agg(Quantidade=("Quantidade", "sum"), Faturamento=("Valor_Total", "sum"))
              .sort_values("Faturamento", ascending=False))
    prod["Participação (%)"] = (prod["Faturamento"] / prod["Faturamento"].sum() * 100).round(1)
    col_a, col_b = st.columns(2)
    top = prod.sort_values("Quantidade").tail(10)
    f4 = px.bar(top, x="Quantidade", y="Produto", orientation="h", color_discrete_sequence=[KETCHUP])
    f4.update_traces(marker_cornerradius=6, hovertemplate="%{y}<br>%{x} unidades<extra></extra>")
    with col_a:
        mostrar(estilo(f4, "Top 10 mais vendidos (unidades)"))
    low = prod.sort_values("Quantidade").head(5)
    f5 = px.bar(low, x="Quantidade", y="Produto", orientation="h", color_discrete_sequence=[AREIA])
    f5.update_traces(marker_cornerradius=6, hovertemplate="%{y}<br>%{x} unidades<extra></extra>")
    with col_b:
        mostrar(estilo(f5, "5 menos vendidos (unidades)"))
    cat = df.groupby("Categoria", as_index=False)["Valor_Total"].sum()
    f6 = px.pie(cat, names="Categoria", values="Valor_Total", hole=0.58,
                color="Categoria", color_discrete_map=COR_CATEGORIA)
    f6.update_traces(textinfo="label+percent", insidetextorientation="horizontal",
                     marker=dict(line=dict(color="#FBF6EE", width=3)),
                     hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>")
    mostrar(estilo(f6, "Participação das categorias no faturamento", legenda=True))
    st.dataframe(
        prod, width="stretch", hide_index=True,
        column_config={
            "Faturamento": st.column_config.NumberColumn(format="R$ %.2f"),
            "Participação (%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0,
                                                                max_value=float(prod["Participação (%)"].max())),
        })

# ====== PAGAMENTOS ======
with aba3:
    pg = df.groupby("Forma_Pagamento", as_index=False)["Valor_Total"].sum()
    f7 = px.pie(pg, names="Forma_Pagamento", values="Valor_Total", hole=0.58,
                color="Forma_Pagamento", color_discrete_map=COR_PAGAMENTO)
    f7.update_traces(textinfo="label+percent", insidetextorientation="horizontal",
                     marker=dict(line=dict(color="#FBF6EE", width=3)),
                     hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>")
    mostrar(estilo(f7, "Faturamento por forma de pagamento", legenda=True))

# ====== QUALIDADE DOS DADOS ======
with aba4:
    st.write("Resumo do tratamento aplicado à planilha enviada:")
    st.table(pd.DataFrame(relatorio.items(), columns=["Verificação", "Quantidade"]).astype(str))
    st.caption("Linhas duplicadas e inválidas são removidas; valor total ausente é recalculado "
               "(quantidade × valor unitário); pagamento ausente vira “Não informado”.")

st.markdown('<div class="rodape">Atividade Extensionista II · CST em Ciência de Dados · UNINTER</div>',
            unsafe_allow_html=True)
