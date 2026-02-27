import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def formatar_moeda(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


# =========================================================
# APP
# =========================================================

st.title("Análise de TVM")

arquivo = st.file_uploader("Envie a planilha", type=["xlsx"])

if arquivo:

    df = pd.read_excel(arquivo)

    # ---------------------------
    # PADRONIZAÇÃO
    # ---------------------------

    df.columns = df.columns.str.strip()

    df["Valor Saldo"] = df["Valor Saldo"].apply(limpar_valor)
    df["Conta"] = df["Conta"].astype(str)

    # ---------------------------
    # PLANILHA 1 (BASE COMPLETA)
    # ---------------------------

    st.subheader("Planilha 1 - Base Completa")
    st.dataframe(df, use_container_width=True)

    # ---------------------------
    # FILTRAR TVM (grupo 13)
    # ---------------------------

    df_tvm = df[df["Conta"].str.startswith("13")].copy()

    total_tvm_oficial = df[df["Conta"] == "13000004"]["Valor Saldo"].sum()

    # ---------------------------
    # CLASSIFICAÇÃO
    # ---------------------------

    def classificar(conta):

        if conta.startswith("131"):
            return "Títulos Privados"

        elif conta.startswith("133"):
            return "Títulos Públicos"

        elif conta.startswith("136"):
            return "Derivativos"

        else:
            return None

    df_tvm["Categoria"] = df_tvm["Conta"].apply(classificar)

    df_tvm = df_tvm[df_tvm["Categoria"].notna()].copy()

    # ---------------------------
    # CONSOLIDAÇÃO
    # ---------------------------

    consolidado = (
        df_tvm.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    # =====================================================
    # RESUMO EXECUTIVO
    # =====================================================

    st.subheader("Resumo Executivo")

    colunas = st.columns(len(consolidado))

    for i in range(len(consolidado)):

        categoria = consolidado.iloc[i]["Categoria"]
        valor_total = float(consolidado.iloc[i]["Valor Saldo"])

        with colunas[i]:

            st.metric(
                categoria,
                formatar_moeda(valor_total)
            )

            with st.expander("Ver composição"):

                df_categoria = df_tvm[df_tvm["Categoria"] == categoria].copy()

                df_categoria["Valor Saldo"] = pd.to_numeric(
                    df_categoria["Valor Saldo"],
                    errors="coerce"
                )

                soma_check = float(df_categoria["Valor Saldo"].sum())
                diferenca = soma_check - valor_total

                st.write("Soma interna:", formatar_moeda(soma_check))
                st.write("Diferença:", formatar_moeda(diferenca))

                df_exibicao = df_categoria.sort_values(
                    "Valor Saldo",
                    ascending=False
                ).copy()

                df_exibicao["Valor Saldo"] = df_exibicao["Valor Saldo"].apply(formatar_moeda)

                st.dataframe(
                    df_exibicao[["Conta", "Descrição da Conta", "Valor Saldo"]],
                    use_container_width=True
                )

    # =====================================================
    # GRÁFICO DE PIZZA
    # =====================================================

    st.subheader("Distribuição % sobre Total TVM")

    if total_tvm_oficial != 0:

        percentuais = consolidado["Valor Saldo"] / total_tvm_oficial * 100

        fig, ax = plt.subplots()

        ax.pie(
            percentuais,
            labels=consolidado["Categoria"],
            autopct="%1.1f%%"
        )

        ax.axis("equal")

        st.pyplot(fig)

    # =====================================================
    # TABELA DE EXPOSIÇÃO %
    # =====================================================

    st.subheader("Exposição por Categoria (%)")

    tabela_percentual = consolidado.copy()

    if total_tvm_oficial != 0:
        tabela_percentual["Percentual (%)"] = (
            tabela_percentual["Valor Saldo"] / total_tvm_oficial * 100
        ).round(2)
    else:
        tabela_percentual["Percentual (%)"] = 0

    st.dataframe(
        tabela_percentual[["Categoria", "Percentual (%)"]],
        use_container_width=True
    )

    # =====================================================
    # VALIDAÇÃO FINAL
    # =====================================================

    st.subheader("Validação")

    soma_folhas = consolidado["Valor Saldo"].sum()
    diferenca_total = soma_folhas - total_tvm_oficial

    st.write("Total TVM Oficial:", formatar_moeda(total_tvm_oficial))
    st.write("Soma das Categorias:", formatar_moeda(soma_folhas))
    st.write("Diferença:", formatar_moeda(diferenca_total))
