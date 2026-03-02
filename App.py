import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
from io import BytesIO
from datetime import datetime
import os

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
# CARREGAR CONFIGURAÇÃO OFICIAL DO BANCO
# =========================================================

if os.path.exists("config_oficial_banco.json"):
    with open("config_oficial_banco.json", "r", encoding="utf-8") as f:
        CONFIG_OFICIAL = json.load(f)
else:
    st.error("Arquivo config_oficial_banco.json não encontrado.")
    st.stop()

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
# SIDEBAR – OVERRIDE TEMPORÁRIO (OPCIONAL)
# =========================================================

st.sidebar.header("Configuração do time (temporário)")
st.sidebar.caption("Esses termos complementam a configuração oficial do banco.")

if "termos_extras" not in st.session_state:
    st.session_state.termos_extras = {
        "Derivativos": [],
        "Títulos Públicos": [],
        "Títulos Privados": []
    }

def list_to_text(lst):
    return "\n".join(lst) if lst else ""

def text_to_list(txt):
    return [t.strip().upper() for t in txt.split("\n") if t.strip()]

txt_der = st.sidebar.text_area(
    "Derivativos – termos extras",
    value=list_to_text(st.session_state.termos_extras["Derivativos"]),
    height=80
)

txt_pub = st.sidebar.text_area(
    "Títulos Públicos – termos extras",
    value=list_to_text(st.session_state.termos_extras["Títulos Públicos"]),
    height=80
)

txt_priv = st.sidebar.text_area(
    "Títulos Privados – termos extras",
    value=list_to_text(st.session_state.termos_extras["Títulos Privados"]),
    height=120
)

if st.sidebar.button("Aplicar termos temporários"):
    st.session_state.termos_extras["Derivativos"] = text_to_list(txt_der)
    st.session_state.termos_extras["Títulos Públicos"] = text_to_list(txt_pub)
    st.session_state.termos_extras["Títulos Privados"] = text_to_list(txt_priv)
    st.sidebar.success("Termos aplicados apenas nesta sessão.")

# =========================================================
# CLASSIFICAÇÃO
# =========================================================

def classificar(descricao):
    desc = (descricao or "").upper()

    termos_der = CONFIG_OFICIAL["Derivativos"] + st.session_state.termos_extras["Derivativos"]
    termos_pub = CONFIG_OFICIAL["Títulos Públicos"] + st.session_state.termos_extras["Títulos Públicos"]
    termos_priv = CONFIG_OFICIAL["Títulos Privados"] + st.session_state.termos_extras["Títulos Privados"]

    if any(t in desc for t in termos_der):
        return "Derivativos"
    if any(t in desc for t in termos_pub):
        return "Títulos Públicos"
    if any(t in desc for t in termos_priv):
        return "Títulos Privados"

    return None

# =========================================================
# PARTE 1 – COTISTAS
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
# PARTE 2 – BALANCETE
# =========================================================

st.header("2. Exposição Econômica da Carteira")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:

    df2 = pd.read_excel(uploaded_file2)

    df2["Conta"] = df2["Conta"].astype(str)
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    total_row = df2[df2["Conta"] == "13000004"]
    total_tvm = total_row["Valor Saldo"].iloc[0]

    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(classificar)

    df_class = df_tvm[df_tvm["Categoria"].notna()].copy()
    df_nao_class = df_tvm[df_tvm["Categoria"].isna()].copy()

    consolidado = (
        df_class.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    consolidado["Percentual"] = (
        consolidado["Valor Saldo"] / total_tvm
    ) * 100

    st.subheader("Resumo Executivo")

    col_total, col_pizza = st.columns([1, 1])

    with col_total:
        for _, row in consolidado.iterrows():
            st.metric(row["Categoria"], formatar_moeda(row["Valor Saldo"]))

        st.metric("Total TVM", formatar_moeda(total_tvm))

    with col_pizza:
        fig, ax = plt.subplots(figsize=(1.6, 1.6))
        ax.pie(
            consolidado["Percentual"],
            labels=consolidado["Categoria"],
            autopct='%1.1f%%',
            textprops={'fontsize': 6}
        )
        st.pyplot(fig)

    st.divider()

    if not df_nao_class.empty:
        st.warning("Contas não classificadas")
        df_nao_class["Valor Saldo"] = df_nao_class["Valor Saldo"].apply(formatar_moeda)
        st.dataframe(df_nao_class[["Conta", "Descrição da Conta", "Valor Saldo"]])
