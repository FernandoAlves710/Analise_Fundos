import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Análise de Fundos", layout="wide")

st.title("Ferramenta de Análise de Fundos")
st.markdown("---")

# ==============================
# Funções auxiliares
# ==============================

def converter_valor_brasileiro(valor):
    if pd.isna(valor):
        return 0
    if isinstance(valor, (int, float)):
        return int(valor)
    valor = str(valor).strip().replace(".", "").split(",")[0]
    try:
        return int(valor)
    except:
        return 0


# ==============================
# PARTE 1 - ORIGINAL (NÃO ALTERADA)
# ==============================

st.header("📈 Parte 1 – Cotistas e Patrimônio Líquido")

uploaded_file1 = st.file_uploader(
    "Envie a planilha de Cotistas e Patrimônio Líquido (.xlsx):",
    type=["xlsx"],
    key="planilha1"
)

if uploaded_file1:
    df1 = pd.read_excel(uploaded_file1)
    df1.columns = df1.columns.str.strip().str.lower()

    df1.rename(columns={
        "data": "data",
        "cota": "cota",
        "variação da cota diária": "variacao_cota",
        "patrimônio": "patrimonio",
        "captação": "captacao",
        "resgate": "resgate",
        "cotistas": "cotistas"
    }, inplace=True)

    for col in ["patrimonio", "captacao", "resgate", "cotistas"]:
        df1[col] = df1[col].apply(converter_valor_brasileiro)

    patrimonio_final = df1["patrimonio"].iloc[0]
    patrimonio_inicial = df1["patrimonio"].iloc[-1]
    variacao_patrimonio = patrimonio_final - patrimonio_inicial

    cotistas_finais = df1["cotistas"].iloc[0]
    captacoes_liquidas = df1["captacao"].sum() - df1["resgate"].sum()

    st.subheader("📊 Resultados — Cotistas & Patrimônio")
    st.metric("Cotistas (data final)", f"{cotistas_finais:,}".replace(",", "."))
    st.metric("Patrimônio (final)", f"R$ {patrimonio_final:,}".replace(",", "."))
    st.metric("Captação líquida (período)", f"R$ {captacoes_liquidas:,}".replace(",", "."))
    st.metric("Variação do PL (final - inicial)", f"R$ {variacao_patrimonio:,}".replace(",", "."))

    st.divider()


# ==============================
# PARTE 2 - BALANCETE (REFATORADA)
# ==============================

st.header("📘 Parte 2 – Balancete")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx):",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:
    df2 = pd.read_excel(uploaded_file2)
    df2.columns = df2.columns.str.strip()

    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)
    df2["Conta"] = df2["Conta"].astype(str)

    # Limpeza código COSIF
    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    # Filtra apenas grupo 13 (TVM)
    df2 = df2[df2["Conta_limpa"].str.startswith("13")]

    # ==============================
    # Identificar contas analíticas
    # ==============================

    contas = df2["Conta_limpa"].tolist()
    analiticas = []

    for c in contas:
        if not any((outra != c and outra.startswith(c)) for outra in contas):
            analiticas.append(c)

    df2_analitico = df2[df2["Conta_limpa"].isin(analiticas)].copy()

    # ==============================
    # Classificação COSIF
    # ==============================

    def classificar(row):
        conta = row["Conta_limpa"]
        desc = row["Descrição da Conta"].upper()

        if "COMPROMISSAD" in desc or conta.startswith("1319"):
            return "Operações Compromissadas"

        if conta.startswith("131"):
            return "Títulos Públicos"

        if conta.startswith("132"):
            return "Títulos Privados"

        return "Outros"

    df2_analitico["Categoria"] = df2_analitico.apply(classificar, axis=1)

    resumo = (
        df2_analitico
        .groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
    )

    valor_publicos = resumo.loc[resumo["Categoria"]=="Títulos Públicos", "Valor Saldo"].sum()
    valor_privados = resumo.loc[resumo["Categoria"]=="Títulos Privados", "Valor Saldo"].sum()
    valor_comp = resumo.loc[resumo["Categoria"]=="Operações Compromissadas", "Valor Saldo"].sum()

    # ==============================
    # Layout Executivo
    # ==============================

    col1, col2, col3 = st.columns(3)
    col1.metric("Títulos Públicos", f"R$ {valor_publicos:,}".replace(",", "."))
    col2.metric("Títulos Privados", f"R$ {valor_privados:,}".replace(",", "."))
    col3.metric("Operações Compromissadas", f"R$ {valor_comp:,}".replace(",", "."))

    st.divider()

    # ==============================
    # Gráfico
    # ==============================

    labels = ["Públicos", "Privados", "Compromissadas"]
    values = [valor_publicos, valor_privados, valor_comp]

    if sum(values) > 0:
        fig, ax = plt.subplots(figsize=(4,4))
        ax.pie(values, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

    st.divider()

    # ==============================
    # Tabela detalhada
    # ==============================

    st.subheader("📋 Detalhamento (contas analíticas)")
    st.dataframe(
        df2_analitico[["Conta", "Descrição da Conta", "Categoria", "Valor Saldo"]]
        .sort_values("Valor Saldo", ascending=False),
        use_container_width=True
    )
