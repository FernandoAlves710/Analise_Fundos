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
# PARTE 2 – BALANCETE (VERSÃO INSTITUCIONAL)
# ==============================

import numpy as np

st.header("Parte 2 - Análise Estrutural do Balancete (COSIF)")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx):",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:

    df2 = pd.read_excel(uploaded_file2)
    df2.columns = df2.columns.str.strip()

    # ==============================
    # LIMPEZA
    # ==============================

    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    df2["Conta"] = df2["Conta"].astype(str)
    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    df2["Descricao"] = df2["Descricao"].astype(str).str.upper()

    # ==============================
    # FILTRAR SOMENTE ATIVO
    # ==============================

    df_ativo = df2[df2["Conta_limpa"].str.startswith("1")].copy()

    # ==============================
    # IDENTIFICAR CONTAS ANALÍTICAS
    # ==============================

    contas = df_ativo["Conta_limpa"].tolist()
    contas_set = set(contas)

    def eh_conta_analitica(conta):
        for outra in contas_set:
            if outra != conta and outra.startswith(conta):
                return False
        return True

    df_ativo["Conta_Analitica"] = df_ativo["Conta_limpa"].apply(eh_conta_analitica)

    df_analitico = df_ativo[df_ativo["Conta_Analitica"] == True].copy()

    # ==============================
    # FILTRAR APENAS TVM (13)
    # ==============================

    df_tvm = df_analitico[df_analitico["Conta_limpa"].str.startswith("13")].copy()

    # ==============================
    # CLASSIFICAÇÃO ECONÔMICA
    # ==============================

    def classificar(descricao):

        if any(p in descricao for p in ["COMPROMISSADA", "REPO"]):
            return "Compromissadas"

        if any(p in descricao for p in [
            "TESOURO", "LTN", "LFT", "NTN", "TITULO PUBLICO"
        ]):
            return "Titulos Publicos"

        if any(p in descricao for p in [
            "CDB", "DEBENTURE", "CRI", "CRA",
            "LETRA FINANCEIRA", "NOTA COMERCIAL",
            "FIDC", "DPGE"
        ]):
            return "Titulos Privados"

        return "Outros"

    df_tvm["Categoria"] = df_tvm["Descricao"].apply(classificar)

    # ==============================
    # CONSOLIDAÇÃO
    # ==============================

    consolidado = (
        df_tvm.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
    )

    total_tvm = df_tvm["Valor Saldo"].sum()

    publico = consolidado.loc[
        consolidado["Categoria"] == "Titulos Publicos",
        "Valor Saldo"
    ].sum()

    privado = consolidado.loc[
        consolidado["Categoria"] == "Titulos Privados",
        "Valor Saldo"
    ].sum()

    compromissadas = consolidado.loc[
        consolidado["Categoria"] == "Compromissadas",
        "Valor Saldo"
    ].sum()

    # ==============================
    # DASHBOARD EXECUTIVO
    # ==============================

    st.subheader("Resumo Executivo – TVM")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Títulos Públicos",
        f"R$ {publico:,.0f}"
    )

    col2.metric(
        "Títulos Privados",
        f"R$ {privado:,.0f}"
    )

    col3.metric(
        "Operações Compromissadas",
        f"R$ {compromissadas:,.0f}"
    )

    st.markdown("---")

    st.metric(
        "Total TVM (contas analíticas)",
        f"R$ {total_tvm:,.0f}"
    )

    # ==============================
    # TABELA DETALHADA
    # ==============================

    st.subheader("Detalhamento Analítico Classificado")

    st.dataframe(
        df_tvm[
            ["Conta_limpa", "Descricao", "Categoria", "Valor Saldo"]
        ].sort_values("Valor Saldo", ascending=False)
    )
