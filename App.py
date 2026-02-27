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
# PARTE 2 – BALANCETE (VERSÃO FINAL DEFINITIVA)
# ==============================

st.header("Parte 2 - Análise Estrutural do Balancete (COSIF)")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx):",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:

    df2 = pd.read_excel(uploaded_file2)

    # ==============================
    # LIMPEZA BÁSICA
    # ==============================

    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    df2["Conta"] = df2["Conta"].astype(str)
    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()

    # ==============================
    # FILTRAR APENAS ATIVO (grupo 1)
    # ==============================

    df_ativo = df2[df2["Conta_limpa"].str.startswith("1")].copy()

    # ==============================
    # IDENTIFICAR CONTAS ANALÍTICAS
    # (não possuem subcontas abaixo)
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
    # FILTRAR TVM (grupo 13)
    # ==============================

    df_tvm = df_analitico[df_analitico["Conta_limpa"].str.startswith("13")].copy()

    # ==============================
    # CLASSIFICAÇÃO ECONÔMICA
    # ==============================

    def classificar(descricao):

        descricao = descricao.upper()

        # 1️⃣ OPERAÇÕES COMPROMISSADAS
        if "COMPROMISS" in descricao:
            return "Operações Compromissadas"

        # 2️⃣ TÍTULOS PÚBLICOS
        if any(p in descricao for p in [
            "TESOURO",
            "LETRAS DO TESOURO",
            "NOTAS DO TESOURO",
            "LETRAS FINANCEIRAS DO TESOURO",
            "TÍTULOS PÚBLICOS FEDERAIS"
        ]):
            return "Títulos Públicos"

        # 3️⃣ TÍTULOS PRIVADOS
        if any(p in descricao for p in [
            "LETRAS FINANCEIRAS",
            "DEBÊNTURES",
            "DEBENTURES",
            "CERTIFICADOS DE DEPOSITO BANCARIO",
            "CERTIFICADOS DE RECEBÍVEIS",
            "COTAS DE FUNDO",
            "FUNDO",
            "FIDC",
            "CRI",
            "CRA",
            "AÇÕES",
            "BDR",
            "RENDA VARIAVEL",
            "EXTERIOR",
            "TÍTULOS PRIVADOS"
        ]):
            return "Títulos Privados"

        return "Outros"

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(classificar)

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
        consolidado["Categoria"] == "Títulos Públicos",
        "Valor Saldo"
    ].sum()

    privado = consolidado.loc[
        consolidado["Categoria"] == "Títulos Privados",
        "Valor Saldo"
    ].sum()

    compromissadas = consolidado.loc[
        consolidado["Categoria"] == "Operações Compromissadas",
        "Valor Saldo"
    ].sum()

    # ==============================
    # DASHBOARD EXECUTIVO
    # ==============================

    st.subheader("Resumo Executivo – TVM")

    col1, col2, col3 = st.columns(3)

    col1.metric("Títulos Públicos", f"R$ {publico:,.0f}")
    col2.metric("Títulos Privados", f"R$ {privado:,.0f}")
    col3.metric("Operações Compromissadas", f"R$ {compromissadas:,.0f}")

    st.markdown("---")
    st.metric("Total TVM (contas analíticas)", f"R$ {total_tvm:,.0f}")

    # ==============================
    # TABELA DETALHADA (AUDITORIA)
    # ==============================

    st.subheader("Detalhamento Analítico Classificado")

    st.dataframe(
        df_tvm[
            ["Conta_limpa", "Descrição da Conta", "Categoria", "Valor Saldo"]
        ].sort_values("Valor Saldo", ascending=False)
    )
