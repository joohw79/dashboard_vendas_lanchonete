"""Gera uma base de vendas FICTÍCIA de uma lanchonete de pequeno porte.

Uso: python gerar_base_ficticia.py [saida.xlsx]

Os dados são simulados apenas para desenvolvimento e teste do dashboard.
Nenhuma informação real de estabelecimento é utilizada.
"""
import sys
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

# produto: (categoria, preço, peso de popularidade)
CARDAPIO = {
    "X-Burger": ("Lanches", 20.00, 10),
    "X-Salada": ("Lanches", 22.00, 9),
    "X-Bacon": ("Lanches", 26.00, 9),
    "X-Egg": ("Lanches", 24.00, 6),
    "X-Tudo": ("Lanches", 30.00, 5),
    "Hot Dog": ("Lanches", 14.00, 7),
    "Misto Quente": ("Lanches", 11.00, 6),
    "Pão na Chapa": ("Lanches", 6.00, 5),
    "Porção de Batata Frita": ("Porções", 24.00, 6),
    "Porção de Calabresa": ("Porções", 32.00, 2),
    "Pastel de Carne": ("Salgados", 9.00, 6),
    "Pastel de Queijo": ("Salgados", 9.00, 5),
    "Coxinha": ("Salgados", 8.00, 7),
    "Esfiha de Carne": ("Salgados", 7.00, 4),
    "Pão de Queijo": ("Salgados", 5.00, 6),
    "Café": ("Bebidas", 4.50, 8),
    "Refrigerante Lata": ("Bebidas", 6.50, 12),
    "Suco Natural": ("Bebidas", 10.00, 5),
    "Água Mineral": ("Bebidas", 4.00, 6),
    "Milkshake": ("Sobremesas", 17.00, 2),
    "Pudim": ("Sobremesas", 9.00, 1),
}
PAGAMENTOS = {"Pix": 0.38, "Cartão de Débito": 0.22, "Cartão de Crédito": 0.25, "Dinheiro": 0.15}
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"]
# fator de movimento por dia da semana (0=segunda)
FATOR_DIA = [0.8, 0.85, 0.95, 1.0, 1.35, 1.45, 0.9]
# horário de funcionamento e pesos (picos no almoço e no jantar)
HORAS = list(range(11, 23))
PESO_HORA = [3, 9, 10, 4, 2, 2, 3, 5, 8, 9, 5, 2]


def gerar(inicio="2026-06-01", fim="2026-08-31"):
    datas = pd.date_range(inicio, fim, freq="D")
    nomes = list(CARDAPIO)
    pesos_prod = np.array([CARDAPIO[n][2] for n in nomes], dtype=float)
    pesos_prod /= pesos_prod.sum()
    ph = np.array(PESO_HORA, dtype=float)
    ph /= ph.sum()
    pg_nomes = list(PAGAMENTOS)
    pg_pesos = np.array(list(PAGAMENTOS.values()))

    linhas = []
    pedido = 1000
    for d in datas:
        # tendência de leve crescimento + efeito de início de mês (pagamento)
        progresso = (d - datas[0]).days / max(1, (datas[-1] - datas[0]).days)
        fator = 1 + 0.08 * progresso
        if 5 <= d.day <= 10:
            fator *= 1.12
        if d.weekday() == 0 and rng.random() < 0.10:   # segunda de movimento muito fraco
            fator *= 0.6
        n_pedidos = int(rng.poisson(46 * FATOR_DIA[d.weekday()] * fator))
        for _ in range(n_pedidos):
            pedido += 1
            hora = int(rng.choice(HORAS, p=ph))
            minuto = int(rng.integers(0, 60))
            pag = str(rng.choice(pg_nomes, p=pg_pesos))
            n_itens = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.40, 0.18, 0.07]))
            itens = rng.choice(nomes, size=n_itens, replace=False, p=pesos_prod)
            for prod in itens:
                cat, preco, _ = CARDAPIO[prod]
                qtd = int(rng.choice([1, 2, 3], p=[0.8, 0.15, 0.05]))
                linhas.append({
                    "ID_Pedido": pedido,
                    "Data": d.date(),
                    "Horario": f"{hora:02d}:{minuto:02d}",
                    "Dia_Semana": DIAS[d.weekday()],
                    "Produto": prod,
                    "Categoria": cat,
                    "Quantidade": qtd,
                    "Valor_Unitario": preco,
                    "Valor_Total": round(qtd * preco, 2),
                    "Forma_Pagamento": pag,
                })
    df = pd.DataFrame(linhas)

    # Inconsistências propositais (~0,5% das linhas) para demonstrar a validação
    n_bad = max(5, int(len(df) * 0.005))
    idx = rng.choice(df.index, size=n_bad * 3, replace=False)
    df.loc[idx[:n_bad], "Valor_Total"] = np.nan                 # valor ausente
    df.loc[idx[n_bad:2 * n_bad], "Quantidade"] = -1             # quantidade inválida
    df.loc[idx[2 * n_bad:], "Forma_Pagamento"] = np.nan         # pagamento ausente
    # algumas linhas duplicadas
    df = pd.concat([df, df.sample(8, random_state=SEED)], ignore_index=True)
    return df


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "vendas_lanchonete_ficticia.xlsx"
    base = gerar()
    base.to_excel(saida, index=False, sheet_name="Vendas")
    print(f"{len(base)} linhas gravadas em {saida}")
