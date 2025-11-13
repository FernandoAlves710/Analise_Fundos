import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Análise de Fundos", layout="centered")

st.title("📊 Ferramenta de Análise de Fundos – Bradesco Crédito Instituições Financeiras")
st.markdown("---")

# ====================================================
# Funções auxiliares
# ====================================================

def converter_valor_brasileiro(valor):
    """Converte string com formato brasileiro em inteiro (sem centavos)."""
    if pd.isna(valor):
        return 0
    if isinstance(valor, (int, float)):
        return int(valor)
    valor = str(valor).strip().replace(".", "").split(",")[0]
    try:
        return int(valor)
    except:
        return 0


def identificar_filhos(df, codigo_pai):
    """Identifica todas as contas-filhas baseadas no prefixo do código do pai."""
    prefixo = str(codigo_pai)[:3]  # usa os 3 primeiros dígitos para agrupar hierarquia
    filhos = df[df["Conta"].astype(str).str.startswith(prefixo)]
    return filhos


# ====================================================
# PARTE 1 — PLANILHA DE COTISTAS E PL
# ====================================================

st.header("📈 Parte 1 – Cotistas e Patrimônio Líquido")

uploaded_file1 = st.file_uploader(
    "Envie a planilha de Cotistas e Patrimônio Líquido (.xlsx):",
    type=["xlsx"],
    key="planilha1"
)

if uploaded_file1:
    df1 = pd.read_excel(uploaded_file1)
    df1.columns = df1.columns.str.strip().str.lower()

    # Renomeia colunas
    df1.rename(columns={
        "data": "data",
        "cota": "cota",
        "variação da cota diária": "variacao_cota",
        "patrimônio": "patrimonio",
        "captação": "captacao",
        "resgate": "resgate",
        "cotistas": "cotistas"
    }, inplace=True)

    # Converte valores
    for col in ["patrimonio", "captacao", "resgate", "cotistas"]:
        df1[col] = df1[col].apply(converter_valor_brasileiro)

    # Cálculos principais
    patrimonio_final = df1["patrimonio"].iloc[0]
    patrimonio_inicial = df1["patrimonio"].iloc[-1]
    variacao_patrimonio = patrimonio_final - patrimonio_inicial
    cotistas_finais = df1["cotistas"].iloc[0]
    captacoes_liquidas = df1["captacao"].sum() - df1["resgate"].sum()

    st.subheader("📊 Resultados — Cotistas & Patrimônio")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cotistas (data final)", f"{cotistas_finais:,}".replace(",", "."))
        st.metric("Variação do PL", f"R$ {variacao_patrimonio:,}".replace(",", "."))
    with col2:
        st.metric("Patrimônio (final)", f"R$ {patrimonio_final:,}".replace(",", "."))
        st.metric("Captação líquida", f"R$ {captacoes_liquidas:,}".replace(",", "."))

    st.divider()


# ====================================================
# PARTE 2 — PLANILHA DE BALANCETE
# ====================================================

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

    # Listas principais
    compromissadas = ["APLICAÇÕES EM OPERAÇÕES COMPROMISSADAS"]
    titulos_publicos = [
        "TÍTULOS PÚBLICOS FEDERAIS - TESOURO NACIONAL",
        "LETRAS FINANCEIRAS DO TESOURO",
        "LETRAS DO TESOURO NACIONAL",
        "NOTAS DO TESOURO NACIONAL"
    ]
    titulos_privados = [
        "LETRAS FINANCEIRAS",
        "DEBÊNTURES",
        "LETRAS FINANCEIRAS SUBORDINADAS",
        "COTAS DE FUNDOS DE INVESTIMENTO",
        "COTAS DE FUNDO DE RENDA FIXA",
        "COTAS DE FUNDO EM DIREITOS CREDITÓRIOS",
        "CERTIFICADOS DE DEPÓSITO BANCÁRIO",
        "CERTIFICADOS DE RECEBÍVEIS IMOBILIÁRIOS",
        "COTAS DE FUNDO MULTIMERCADO",
        "TÍTULOS DE RENDA VARIÁVEL",
        "AÇÕES DE COMPANHIAS ABERTAS",
        "COTAS DE FUNDO IMOBILIÁRIO",
        "APLICAÇÕES EM TÍTULOS E VALORES MOBILIÁRIOS NO EXTERIOR",
        "OUTROS TÍTULOS PRIVADOS - RENDA FIXA",
        "BDR - CERTIFICADO DE DEPÓSITO DE AÇÕES",
        "COTAS DE FUNDO DE INVESTIMENTO ÍNDICE DE MERCADO"
    ]

    # ===============================
    # Localiza contas principais
    # ===============================
    df2["Conta"] = df2["Conta"].astype(str)
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str)

    # Localiza pai Títulos e Valores Mobiliários (geral)
    conta_tvms = df2[df2["Descrição da Conta"].str.contains("TÍTULOS E VALORES MOBILIÁRIOS", case=False, na=False)]
    total_tvm = conta_tvms["Valor Saldo"].sum()

    # Compromissadas
    valor_compromissadas = df2[df2["Descrição da Conta"].isin(compromissadas)]["Valor Saldo"].sum()

    # Filtra públicos e privados (sem duplicar)
    publicos_filtrados = df2[df2["Descrição da Conta"].isin(titulos_publicos)][["Conta", "Descrição da Conta", "Valor Saldo"]]
    privados_filtrados = df2[df2["Descrição da Conta"].isin(titulos_privados)][["Conta", "Descrição da Conta", "Valor Saldo"]]

    soma_publicos = publicos_filtrados["Valor Saldo"].sum()
    soma_privados = privados_filtrados["Valor Saldo"].sum()

    st.subheader("📊 Resultados — Balancete")
    st.metric("Total Títulos e Valores Mobiliários", f"R$ {total_tvm:,}".replace(",", "."))
    st.metric("Operações Compromissadas", f"R$ {valor_compromissadas:,}".replace(",", "."))

    # Exibe detalhamento hierárquico
    st.divider()
    st.write("### 💛 Títulos Públicos — detalhamento")
    with st.expander("Ver contas detalhadas"):
        st.dataframe(publicos_filtrados, use_container_width=True)

    st.write("### 💚 Títulos Privados — detalhamento")
    with st.expander("Ver contas detalhadas"):
        st.dataframe(privados_filtrados, use_container_width=True)

    # ===============================
    # Gráfico da composição
    # ===============================
    st.divider()
    st.subheader("📉 Composição da Carteira")

    labels = ["Operações Compromissadas", "Títulos Públicos", "Títulos Privados"]
    values = [valor_compromissadas, soma_publicos, soma_privados]

    if sum(values) == 0:
        st.info("Sem valores para composição (todas as categorias com valor zero).")
    else:
        fig, ax = plt.subplots(figsize=(3, 3))
        wedges, texts, autotexts = ax.pie(
            values,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 8}
        )
        ax.legend(
            wedges,
            labels,
            title="Categorias",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=8,
            title_fontsize=9
        )
        ax.axis("equal")
        st.pyplot(fig)
