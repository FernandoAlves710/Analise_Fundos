import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Análise Profissional de Fundos",
    layout="wide"
)

st.title("Análise Profissional de Fundos de Investimento")
st.markdown("---")

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def converter_valor_brasileiro(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    valor = str(valor).replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except:
        return 0.0

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =========================================================
# PARTE 2 – EXPOSIÇÃO ECONÔMICA
# =========================================================

st.header("Exposição Econômica da Carteira (TVM = 100%)")

uploaded_file = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx)",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df["Conta"] = df["Conta"].astype(str).str.strip()
    df["Descrição da Conta"] = df["Descrição da Conta"].astype(str).str.upper()
    df["Valor Saldo"] = df["Valor Saldo"].apply(converter_valor_brasileiro)

    # =====================================================
    # TOTAL OFICIAL TVM
    # =====================================================

    total_row = df[df["Conta"] == "13000004"]

    if total_row.empty:
        st.error("Conta 13000004 não encontrada.")
        st.stop()

    total_tvm = total_row["Valor Saldo"].iloc[0]

    # =====================================================
    # APENAS CONTAS ANALÍTICAS
    # =====================================================

    df_tvm = df[
        (df["Conta"].str.startswith("13")) &
        (df["Conta"] != "13000004") &
        (df["Valor Saldo"] != 0)
    ].copy()

    # =====================================================
    # CLASSIFICAÇÃO PRECISA
    # =====================================================

    def classificar(descricao):

        # Derivativos
        if any(p in descricao for p in [
            "FUTURO", "OPÇÃO", "SWAP", "DERIVAT"
        ]):
            return "Derivativos"

        # Títulos Públicos
        if any(p in descricao for p in [
            "TESOURO", "LFT", "LTN", "NTN"
        ]):
            return "Títulos Públicos"

        # Títulos Privados reais
        if any(p in descricao for p in [
            "DEBÊNTURE", "CDB", "CRI", "CRA",
            "FUNDO", "AÇÃO", "BDR",
            "LCI", "LCA"
        ]):
            return "Títulos Privados"

        # Ignorar o resto
        return None

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(classificar)

    # Mantém apenas categorias válidas
    df_tvm = df_tvm[df_tvm["Categoria"].notna()]

    consolidado = (
        df_tvm.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    consolidado["Percentual"] = (
        consolidado["Valor Saldo"] / total_tvm
    ) * 100

    # =====================================================
    # RESULTADOS
    # =====================================================

    st.subheader("Resumo Executivo")

    cols = st.columns(len(consolidado))

    for i in range(len(consolidado)):
        cols[i].metric(
            consolidado.iloc[i]["Categoria"],
            formatar_moeda(consolidado.iloc[i]["Valor Saldo"])
        )

    st.metric("Total TVM (100%)", formatar_moeda(total_tvm))

    st.divider()

    # =====================================================
    # GRÁFICOS
    # =====================================================

    col1, col2 = st.columns([1, 1.2])

    with col1:
        fig1, ax1 = plt.subplots(figsize=(3, 3))
        ax1.pie(
            consolidado["Percentual"],
            labels=consolidado["Categoria"],
            autopct='%1.1f%%'
        )
        st.pyplot(fig1)

    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.barh(
            consolidado["Categoria"],
            consolidado["Percentual"]
        )
        ax2.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x:.1f}%")
        )
        st.pyplot(fig2)

    st.divider()

    st.subheader("Contas Consideradas na Análise")
    df_tvm["Valor Saldo"] = df_tvm["Valor Saldo"].apply(formatar_moeda)
    st.dataframe(df_tvm, use_container_width=True)
