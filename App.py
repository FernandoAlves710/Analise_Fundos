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
# PARTE 2 - BALANCETE (ESTRUTURA COMPLETA COSIF)
# ==============================

st.header("📘 Parte 2 – Estruturação Completa do Balancete")

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

    # =========================================
    # 1️⃣ Limpeza COSIF
    # =========================================

    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    # =========================================
    # 2️⃣ Identificação Hierárquica Completa
    # =========================================

    todas_contas = df2["Conta_limpa"].tolist()

    def identificar_tipo_conta(codigo):
        for outra in todas_contas:
            if outra != codigo and outra.startswith(codigo):
                return "Sintética"
        return "Analítica"

    df2["Tipo_Conta"] = df2["Conta_limpa"].apply(identificar_tipo_conta)

    # =========================================
    # 3️⃣ Trabalhar apenas com contas analíticas
    # =========================================

    df_analitico = df2[df2["Tipo_Conta"] == "Analítica"].copy()

    # =========================================
    # 4️⃣ Separar Ativo e Passivo
    # =========================================

    df_analitico["Grupo"] = df_analitico["Conta_limpa"].str[0]

    ativo = df_analitico[df_analitico["Grupo"] == "1"].copy()
    passivo = df_analitico[df_analitico["Grupo"] == "2"].copy()

    # =========================================
    # 5️⃣ Dentro do Ativo, identificar TVM
    # =========================================

    ativo["Subgrupo"] = ativo["Conta_limpa"].str[:2]

    tvm = ativo[ativo["Subgrupo"] == "13"].copy()

    # =========================================
    # 6️⃣ Classificação Inteligente
    # =========================================

    def classificar_tvm(row):
        conta = row["Conta_limpa"]
        desc = row["Descrição da Conta"].upper()

        if "COMPROMISSAD" in desc:
            return "Operações Compromissadas"

        if conta.startswith("131"):
            return "Títulos Públicos"

        if conta.startswith("132"):
            return "Títulos Privados"

        return "Outros TVM"

    tvm["Categoria"] = tvm.apply(classificar_tvm, axis=1)

    resumo = (
        tvm
        .groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
    )

    # =========================================
    # 7️⃣ Cards Executivos
    # =========================================

    valor_publicos = resumo.loc[resumo["Categoria"]=="Títulos Públicos","Valor Saldo"].sum()
    valor_privados = resumo.loc[resumo["Categoria"]=="Títulos Privados","Valor Saldo"].sum()
    valor_comp = resumo.loc[resumo["Categoria"]=="Operações Compromissadas","Valor Saldo"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Títulos Públicos", f"R$ {valor_publicos:,.0f}".replace(",", "."))
    col2.metric("Títulos Privados", f"R$ {valor_privados:,.0f}".replace(",", "."))
    col3.metric("Operações Compromissadas", f"R$ {valor_comp:,.0f}".replace(",", "."))

    st.divider()

    # =========================================
    # 8️⃣ Mostrar Estrutura Completa (para auditoria)
    # =========================================

    st.subheader("📋 Estrutura Analítica Completa (Ativo)")
    st.dataframe(
        ativo[["Conta","Descrição da Conta","Valor Saldo","Tipo_Conta"]],
        use_container_width=True
    )
