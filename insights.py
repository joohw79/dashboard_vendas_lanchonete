"""Cálculo de métricas e geração de insights (storytelling) a partir das vendas.

Tudo é calculado sobre os dados filtrados. Os textos descrevem o que os dados
mostram e sugerem ações; não afirmam causas nem prometem resultados.
"""
import html
from collections import Counter
from itertools import combinations

import pandas as pd

from tratamento import DIAS

MIN_PEDIDOS = 30


def pct(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",") + "%"


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def lista(nomes) -> str:
    nomes = [f"<b>{html.escape(str(n))}</b>" for n in nomes]
    if len(nomes) <= 1:
        return "".join(nomes)
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def pedidos_df(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por pedido: itens distintos, valor, se tem bebida e se tem lanche."""
    g = df.groupby("ID_Pedido")
    return pd.DataFrame({
        "itens": g["Produto"].nunique(),
        "valor": g["Valor_Total"].sum(),
        "bebida": g["Categoria"].apply(lambda x: (x == "Bebidas").any()),
        "lanche": g["Categoria"].apply(lambda x: (x == "Lanches").any()),
    })


def curva_abc(df: pd.DataFrame) -> pd.DataFrame:
    p = (df.groupby("Produto")["Valor_Total"].sum().sort_values(ascending=False)
           .rename("faturamento").to_frame())
    p["participacao"] = p["faturamento"] / p["faturamento"].sum() * 100
    acumulado_antes = p["participacao"].cumsum() - p["participacao"]
    p["classe_a"] = acumulado_antes < 80
    return p


def pares_frequentes(df: pd.DataFrame, n: int = 6):
    cont = Counter()
    for _, produtos in df.groupby("ID_Pedido")["Produto"]:
        for a, b in combinations(sorted(set(produtos)), 2):
            cont[(a, b)] += 1
    return cont.most_common(n)


def media_diaria_por_mes(df: pd.DataFrame) -> pd.Series:
    por_dia = df.groupby("Data")["Valor_Total"].sum()
    meses = por_dia.groupby(por_dia.index.to_period("M"))
    media = meses.mean()
    dias = meses.count()
    return media[dias >= 7]


def metricas(df: pd.DataFrame) -> dict:
    m = {"pedidos": df["ID_Pedido"].nunique(), "dias": df["Data"].nunique()}

    # --- horários de pico e de vale (janelas de 3 horas) ---
    h = df.groupby("Hora")["ID_Pedido"].nunique().sort_index()
    if len(h):
        h = h.reindex(range(int(h.index.min()), int(h.index.max()) + 1), fill_value=0)
        m["por_hora"] = h
        if len(h) >= 7:
            jan = h.rolling(3).sum().dropna()
            hmin, hmax = h.index.min(), h.index.max()
            pico_fim = int(jan.idxmax())
            interior = jan[(jan.index - 2 >= hmin + 1) & (jan.index <= hmax - 1)]
            m["pico"] = (pico_fim - 2, pico_fim + 1, jan.max() / m["pedidos"] * 100)
            if len(interior):
                vale_fim = int(interior.idxmin())
                m["vale"] = (vale_fim - 2, vale_fim + 1, interior.min() / m["pedidos"] * 100)

    # --- dias da semana (média por dia) ---
    diario = df.groupby("Data")["Valor_Total"].sum()
    if m["dias"] >= 14:
        dd = diario.groupby(diario.index.dayofweek).mean()
        if len(dd) >= 5:
            m["dia_forte"] = (DIAS[int(dd.idxmax())], dd.max())
            m["dia_fraco"] = (DIAS[int(dd.idxmin())], dd.min())
            m["razao_dias"] = dd.max() / dd.min() if dd.min() > 0 else None

    # --- curva ABC ---
    abc = curva_abc(df)
    m["abc"] = abc
    m["n_a"], m["n_itens"] = int(abc["classe_a"].sum()), len(abc)
    cauda = abc[(~abc["classe_a"]) & (abc["participacao"] < 2)]
    m["cauda"] = cauda
    m["cauda_total"] = cauda["participacao"].sum()

    # --- como o cliente compra ---
    if m["pedidos"] >= MIN_PEDIDOS:
        ped = pedidos_df(df)
        m["ped"] = ped
        m["share_1item"] = (ped["itens"] == 1).mean() * 100
        um, varios = ped[ped["itens"] == 1], ped[ped["itens"] >= 2]
        if len(um) and len(varios):
            m["ticket_1"], m["ticket_2mais"] = um["valor"].mean(), varios["valor"].mean()
        lanche = ped[ped["lanche"]]
        bebidas = df[df["Categoria"] == "Bebidas"]
        if len(lanche) >= MIN_PEDIDOS and len(bebidas):
            sem = int((~lanche["bebida"]).sum())
            m["lanche_sem_bebida"] = sem
            m["share_lanche_sem_bebida"] = sem / len(lanche) * 100
            m["preco_bebida"] = bebidas["Valor_Total"].sum() / bebidas["Quantidade"].sum()
            m["sim_10"] = 0.10 * sem * m["preco_bebida"]
        m["pares"] = pares_frequentes(df)

    # --- evolução ---
    mm = media_diaria_por_mes(df)
    if len(mm) >= 2:
        m["mes_ini"], m["mes_fim"] = (str(mm.index[0]), mm.iloc[0]), (str(mm.index[-1]), mm.iloc[-1])
        m["cresc"] = (mm.iloc[-1] / mm.iloc[0] - 1) * 100
    inicio = diario[diario.index.day.isin(range(5, 11))]
    resto = diario[~diario.index.day.isin(range(5, 11))]
    if len(inicio) >= 6 and len(resto) >= 14 and resto.mean() > 0:
        m["inicio_mes"] = (inicio.mean() / resto.mean() - 1) * 100
    return m


def mes_pt(periodo: str) -> str:
    nomes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    ano, mes = periodo.split("-")
    return f"{nomes[int(mes) - 1]}/{ano}"


def capitulos(m: dict) -> list[dict]:
    caps = []

    # 1) Quando
    pts, dica = [], []
    if "pico" in m:
        s, e, p = m["pico"]
        pts.append(f"<b>{pct(p, 0)}</b> dos pedidos se concentram entre <b>{s}h e {e}h</b>, a janela de maior movimento.")
        dica.append(f"reforce equipe e estoque entre {s}h e {e}h, quando o movimento é maior")
    if "vale" in m:
        s, e, p = m["vale"]
        pts.append(f"Entre <b>{s}h e {e}h</b> ficam só <b>{pct(p, 0)}</b> dos pedidos: é a faixa mais ociosa.")
        dica.append(f"teste uma oferta leve entre {s}h e {e}h (combo ou café com salgado) para ocupar a capacidade ociosa")
    if "dia_forte" in m and m.get("razao_dias"):
        pts.append(f"<b>{m['dia_forte'][0]}</b> é o dia mais forte (média de {brl(m['dia_forte'][1])} por dia), "
                   f"cerca de <b>{str(round(m['razao_dias'], 1)).replace('.', ',')}×</b> o de <b>{m['dia_fraco'][0].lower()}</b>.")
        dica.append(f"planeje compras e escala pelo calendário e use {m['dia_fraco'][0].lower()} para divulgar promoções")
    caps.append({"tag": "Quando vender", "titulo": "Quando a lanchonete mais vende?", "pontos": pts,
                 "dica": "; ".join(dica).capitalize() + "." if dica else ""})

    # 2) O que vende
    pts, dica = [], []
    abc = m["abc"]
    if m["n_itens"] >= 5:
        lideres = list(abc.index[:3])
        pts.append(f"<b>{m['n_a']} de {m['n_itens']}</b> itens geram 80% do faturamento. Lideram: {lista(lideres)}.")
        dica.append("proteja estoque e qualidade dos itens líderes, que sustentam o caixa")
        if len(m["cauda"]):
            nomes = list(m["cauda"].sort_values("participacao").index[:4])
            pts.append(f"<b>{len(m['cauda'])}</b> itens têm menos de 2% do faturamento cada (somam {pct(m['cauda_total'])}): {lista(nomes)}.")
            dica.append("avalie combinar, reposicionar ou retirar os itens de baixa participação, olhando também a margem de cada um (não disponível nesta planilha)")
    caps.append({"tag": "O que vende", "titulo": "O que sustenta o faturamento?", "pontos": pts,
                 "dica": "; ".join(dica).capitalize() + "." if dica else ""})

    # 3) Como compra
    pts, dica = [], []
    if "share_1item" in m:
        if "ticket_1" in m:
            pts.append(f"<b>{pct(m['share_1item'], 0)}</b> dos pedidos têm um único item (ticket médio de {brl(m['ticket_1'])}), "
                       f"contra <b>{brl(m['ticket_2mais'])}</b> nos pedidos com 2 ou mais itens.")
            dica.append("treine o atendimento para sugerir um item a mais no caixa")
        if "share_lanche_sem_bebida" in m:
            pts.append(f"<b>{pct(m['share_lanche_sem_bebida'], 0)}</b> dos pedidos com lanche saem sem bebida.")
            dica.append("crie um combo lanche + bebida")
            pts.append(f"Simulação: se 10% desses pedidos incluíssem uma bebida (média de {brl(m['preco_bebida'])}), "
                       f"seriam cerca de <b>{brl(m['sim_10'])}</b> a mais no período (estimativa simples, sem custos).")
        if m.get("pares"):
            (a, b), n = m["pares"][0]
            pts.append(f"O par mais pedido junto é {lista([a, b])} ({n} pedidos).")
            dica.append("transforme os pares mais frequentes em combos com preço atrativo")
    caps.append({"tag": "Como o cliente compra", "titulo": "Como o cliente monta o pedido?", "pontos": pts,
                 "dica": "; ".join(dica).capitalize() + "." if dica else ""})

    # 4) Evolução
    pts, dica = [], []
    if "cresc" in m:
        (m1, v1), (m2, v2) = m["mes_ini"], m["mes_fim"]
        verbo = "subiu" if m["cresc"] >= 0 else "caiu"
        pts.append(f"A média diária de faturamento {verbo} de <b>{brl(v1)}</b> ({mes_pt(m1)}) para <b>{brl(v2)}</b> "
                   f"({mes_pt(m2)}): <b>{'+' if m['cresc'] >= 0 else ''}{pct(m['cresc'])}</b>.")
        dica.append("acompanhe esse indicador todo mês para saber se as ações estão funcionando")
    if "inicio_mes" in m:
        sinal = "maior" if m["inicio_mes"] >= 0 else "menor"
        pts.append(f"Nos dias 5 a 10 de cada mês, a média diária foi <b>{pct(abs(m['inicio_mes']))} {sinal}</b> "
                   f"que nos demais dias, período em que costuma haver mais renda circulando.")
        dica.append("antecipe estoque e destaque promoções nessa janela, e confira se o padrão se repete nos próximos meses")
    caps.append({"tag": "Evolução", "titulo": "Para onde o negócio caminha?", "pontos": pts,
                 "dica": "; ".join(dica).capitalize() + "." if dica else ""})
    return caps


def prioridades(m: dict) -> list[str]:
    itens = []
    if "share_lanche_sem_bebida" in m:
        itens.append(f"Testar um <b>combo lanche + bebida</b>: {pct(m['share_lanche_sem_bebida'], 0)} dos pedidos com lanche saem sem bebida.")
    if "vale" in m:
        s, e, p = m["vale"]
        itens.append(f"Criar uma <b>oferta para a faixa das {s}h às {e}h</b>, hoje com só {pct(p, 0)} dos pedidos.")
    if len(m["cauda"]):
        itens.append(f"Revisar os <b>{len(m['cauda'])} itens de baixa participação</b> (menos de 2% do faturamento cada).")
    if "pico" in m and len(itens) < 3:
        s, e, _ = m["pico"]
        itens.append(f"Reforçar <b>equipe e estoque entre {s}h e {e}h</b>, o horário de maior movimento.")
    return itens[:3]
