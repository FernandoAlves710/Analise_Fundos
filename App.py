import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# ==========================================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================================

st.set_page_config(
    page_title="Análise de Fundos - COSIF",
    layout="wide"
)

st.title("📊 Ferramenta Profissional de Análise de Fundos")
st.markdown("Estruturação automática do Balancete conforme hierarquia COSIF.")
st.divider()

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def converter_valor_brasileiro(valor):
    if pd.isna(valor):
        return 0
    if isinstance(valor, (int, float)):
        return float(valor)
    valor = str(valor).strip().replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except:
        return 0


def identificar_contas_analiticas(df):
    contas = df["Conta_limpa"].tolist()
    analiticas = []

    for c in contas:
        if not any((outra != c and outra.startswith(c)) for outra in contas):
            analiticas.append(c)

    return df[df["Conta_limpa"].isin(analiticas)]


def classificar_tvm(row):
    conta = row["Conta_limpa"]
    desc = row["Descrição da Conta"].upper()

    # Compromissadas
    if "COMPROMISSAD" in desc or conta.startswith("1319"):
        return "Operações Compromissadas"

    # Títulos Públicos
    if conta.startswith("131"):
        return "Títulos Públicos"

    # Títulos Privados
    if conta.startswith("132"):
        return "Títulos Privados"

    return "Outros"


def gerar_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="TVM_Classificado")
    return output.getvalue()

# ==========================================================
# PARTE 1 – COTISTAS E PL
# ==========================================================

st.header("📈 Parte 1 – Cotistas e Patrimônio Líquido")

uploaded_file1 = st.file_uploader(
    "Envie a planilha de Cotistas e PL (.xlsx)",
    type=["xlsx"],
    key="pl"
)

if uploaded_file1:
    df1 = pd.read_excel(uploaded_file1)
    df1.columns = df1.columns.str.strip().str.lower()

    df1.rename(columns={
        "patrimônio": "patrimonio"
    }, inplace=True)

    for col in ["patrimonio", "captacao", "resgate", "cotistas"]:
        if col in df1.columns:
            df1[col] = df1[col].apply(converter_valor_brasileiro)

    patrimonio_final = df1["patrimonio"].iloc[0]
    patrimonio_inicial = df1["patrimonio"].iloc[-1]
    variacao_patrimonio = patrimonio_final - patrimonio_inicial
    captacoes_liquidas = df1["captacao"].sum() - df1["resgate"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PL Final", f"R$ {patrimonio_final:,.0f}".replace(",", "."))
    c2.metric("Captação Líquida", f"R$ {captacoes_liquidas:,.0f}".replace(",", "."))
    c3.metric("Variação PL", f"R$ {variacao_patrimonio:,.0f}".replace(",", "."))
    c4.metric("Cotistas", f"{int(df1['cotistas'].iloc[0]):,}".replace(",", "."))

    st.divider()

# ==========================================================
# PARTE 2 – BALANCETE (COSIF)
# ==========================================================

st.header("📘 Parte 2 – Balancete Estruturado (COSIF)")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx)",
    type=["xlsx"],
    key="balancete"
)

if uploaded_file2:
    df2 = pd.read_excel(uploaded_file2)
    df2.columns = df2.columns.str.strip()

    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)
    df2["Conta"] = df2["Conta"].astype(str)

    # Limpa código COSIF
    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    # Filtra apenas grupo 13 (TVM)
    df2 = df2[df2["Conta_limpa"].str.startswith("13")]

    # Identifica contas analíticas
    df2_analitico = identificar_contas_analiticas(df2)

    # Classifica
    df2_analitico["Categoria"] = df2_analitico.apply(classificar_tvm, axis=1)

    # Resumo executivo
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
    # CARDS EXECUTIVOS
    # ==============================

    col1, col2, col3 = st.columns(3)

    col1.metric("Títulos Públicos", f"R$ {valor_publicos:,.0f}".replace(",", "."))
    col2.metric("Títulos Privados", f"R$ {valor_privados:,.0f}".replace(",", "."))
    col3.metric("Operações Compromissadas", f"R$ {valor_comp:,.0f}".replace(",", "."))

    st.divider()

    # ==============================
    # GRÁFICO
    # ==============================

    labels = ["Títulos Públicos", "Títulos Privados", "Compromissadas"]
    values = [valor_publicos, valor_privados, valor_comp]

    if sum(values) > 0:
        fig, ax = plt.subplots(figsize=(4,4))
        ax.pie(values, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.info("Sem valores classificados em TVM.")

    st.divider()

    # ==============================
    # TABELA DETALHADA
    # ==============================

    st.subheader("📋 Detalhamento Analítico (sem dupla contagem)")

    tabela_final = df2_analitico[
        ["Conta", "Descrição da Conta", "Categoria", "Valor Saldo"]
    ].sort_values(by="Valor Saldo", ascending=False)

    st.dataframe(tabela_final, use_container_width=True)

    # ==============================
    # DOWNLOAD EXCEL
    # ==============================

    excel_file = gerar_excel_download(tabela_final)

    st.download_button(
        label="📥 Baixar classificação em Excel",
        data=excel_file,
        file_name="classificacao_tvm.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
