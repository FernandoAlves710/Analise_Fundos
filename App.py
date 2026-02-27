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
# PARTE 1 – COTISTAS & PATRIMÔNIO LÍQUIDO
# =========================================================

st.header("1. Cotistas e Patrimônio Líquido")

uploaded_file1 = st.file_uploader(
    "Envie a planilha de Cotistas e Patrimônio Líquido (.xlsx)",
    type=["xlsx"],
    key="planilha1"
)

if uploaded_file1:

    df1 = pd.read_excel(uploaded_file1)
    df1.columns = df1.columns.str.strip().str.lower()

    df1.rename(columns={
        "patrimônio": "patrimonio",
        "captação": "captacao",
        "resgate": "resgate",
        "cotistas": "cotistas"
    }, inplace=True)

    for col in ["patrimonio", "captacao", "resgate", "cotistas"]:
        if col in df1.columns:
            df1[col] = df1[col].apply(converter_valor_brasileiro)

    patrimonio_final = df1["patrimonio"].iloc[0]
    patrimonio_inicial = df1["patrimonio"].iloc[-1]
    variacao_patrimonio = patrimonio_final - patrimonio_inicial
    cotistas_finais = int(df1["cotistas"].iloc[0])
    captacoes_liquidas = df1["captacao"].sum() - df1["resgate"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Cotistas (Final)", f"{cotistas_finais:,}".replace(",", "."))
    col2.metric("Patrimônio Final", formatar_moeda(patrimonio_final))
    col3.metric("Captação Líquida", formatar_moeda(captacoes_liquidas))
    col4.metric("Variação do PL", formatar_moeda(variacao_patrimonio))

    st.divider()

# =========================================================
# PARTE 2 – EXPOSIÇÃO ECONÔMICA (TVM = 100%)
# =========================================================

st.header("2. Exposição Econômica da Carteira (TVM = 100%)")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:

    df2 = pd.read_excel(uploaded_file2)

    df2["Conta"] = df2["Conta"].astype(str).str.strip()
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    # =====================================================
    # TOTAL OFICIAL TVM (13000004)
    # =====================================================

    total_row = df2[df2["Conta"] == "13000004"]

    if total_row.empty:
        st.error("Conta 13000004 não encontrada.")
        st.stop()

    total_tvm = total_row["Valor Saldo"].iloc[0]

    # =====================================================
    # FILTRAR CONTAS ANALÍTICAS
    # =====================================================

    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    # =====================================================
    # CLASSIFICAÇÃO
    # =====================================================

    def classificar(descricao):

        if any(p in descricao for p in ["FUTURO", "OPÇÃO", "SWAP", "DERIVAT"]):
            return "Derivativos"

        if any(p in descricao for p in ["TESOURO", "LFT", "LTN", "NTN"]):
            return "Títulos Públicos"

        if any(p in descricao for p in [
            "DEBÊNTURE", "CDB", "CRI", "CRA",
            "FUNDO", "AÇÃO", "BDR",
            "LCI", "LCA"
        ]):
            return "Títulos Privados"

        return None

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(classificar)
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
    # RESUMO EXECUTIVO COM ABERTURA
    # =====================================================

    st.subheader("Resumo Executivo")

    cols = st.columns(len(consolidado))

    for i in range(len(consolidado)):

        categoria = consolidado.iloc[i]["Categoria"]
        valor_categoria = consolidado.iloc[i]["Valor Saldo"]

        with cols[i]:
            st.metric(
                categoria,
                formatar_moeda(valor_categoria)
            )

            # 🔎 ABERTURA DO TOTAL
            with st.expander("Ver composição"):

                df_categoria = df_tvm[df_tvm["Categoria"] == categoria].copy()

                soma_check = df_categoria["Valor Saldo"].sum()

                st.write("Soma das contas:", formatar_moeda(soma_check))

                df_exibicao = df_categoria.sort_values(
                    "Valor Saldo",
                    ascending=False
                ).copy()

                df_exibicao["Valor Saldo"] = df_exibicao["Valor Saldo"].apply(formatar_moeda)

                st.dataframe(
                    df_exibicao[["Conta", "Descrição da Conta", "Valor Saldo"]],
                    use_container_width=True
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

    # =====================================================
    # TABELA FINAL
    # =====================================================

    st.subheader("Contas Consideradas na Análise")

    df_exibicao_final = df_tvm.copy()
    df_exibicao_final["Valor Saldo"] = df_exibicao_final["Valor Saldo"].apply(formatar_moeda)

    st.dataframe(df_exibicao_final, use_container_width=True)
