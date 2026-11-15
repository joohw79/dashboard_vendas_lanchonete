"""Leitura, validação e cálculo de indicadores da base de vendas."""
import pandas as pd

COLUNAS_OBRIGATORIAS = [
    "ID_Pedido", "Data", "Horario", "Produto", "Categoria",
    "Quantidade", "Valor_Unitario", "Valor_Total", "Forma_Pagamento",
]
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"]


def carregar(arquivo) -> pd.DataFrame:
    """Lê um .xlsx ou .csv e confere se as colunas obrigatórias existem."""
    nome = getattr(arquivo, "name", str(arquivo)).lower()
    df = pd.read_csv(arquivo) if nome.endswith(".csv") else pd.read_excel(arquivo)
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(faltando))
    return df


def tratar(df: pd.DataFrame):
    """Retorna (base_limpa, relatorio_de_inconsistencias)."""
    df = df.copy()
    total_inicial = len(df)
    rel = {"Linhas lidas": total_inicial}

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    for c in ["Quantidade", "Valor_Unitario", "Valor_Total"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    dup = df.duplicated().sum()
    df = df.drop_duplicates()
    rel["Linhas duplicadas removidas"] = int(dup)

    # Valor_Total ausente pode ser recalculado com segurança (qtd x unitário)
    recalc = df["Valor_Total"].isna() & df["Quantidade"].gt(0) & df["Valor_Unitario"].notna()
    df.loc[recalc, "Valor_Total"] = df.loc[recalc, "Quantidade"] * df.loc[recalc, "Valor_Unitario"]
    rel["Valor total recalculado (qtd x unitário)"] = int(recalc.sum())

    invalidas = (
        df["Data"].isna() | df["Produto"].isna()
        | df["Quantidade"].isna() | df["Quantidade"].le(0)
        | df["Valor_Total"].isna() | df["Valor_Total"].lt(0)
    )
    rel["Linhas inválidas removidas"] = int(invalidas.sum())
    df = df[~invalidas].copy()

    sem_pg = df["Forma_Pagamento"].isna().sum()
    df["Forma_Pagamento"] = df["Forma_Pagamento"].fillna("Não informado")
    rel["Forma de pagamento não informada"] = int(sem_pg)

    df["Hora"] = pd.to_datetime(df["Horario"].astype(str), format="%H:%M", errors="coerce").dt.hour
    df["Dia_Semana"] = df["Data"].dt.dayofweek.map(dict(enumerate(DIAS)))
    df["Mes"] = df["Data"].dt.to_period("M").astype(str)
    rel["Linhas utilizadas"] = len(df)
    return df.reset_index(drop=True), rel


def indicadores(df: pd.DataFrame) -> dict:
    faturamento = df["Valor_Total"].sum()
    pedidos = df["ID_Pedido"].nunique()
    return {
        "faturamento": faturamento,
        "pedidos": pedidos,
        "ticket_medio": faturamento / pedidos if pedidos else 0.0,
        "itens": int(df["Quantidade"].sum()),
    }
