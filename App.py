import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Análise de Fundos", layout="centered")

st.title("📊 Ferramenta de Análise de Fundos – Bradesco Crédito Instituições Financeiras")
st.markdown("---")

# ==============================
# Funções auxiliares
# ==============================

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


# ==============================
# PARTE 1 - PLANILHA 1
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

    # Normaliza nomes esperados
    df1.rename(columns={
        "data": "data",
        "cota": "cota",
        "variação da cota diária": "variacao_cota",
        "patrimônio": "patrimonio",
        "captação": "captacao",
        "resgate": "resgate",
        "cotistas": "cotistas"
    }, inplace=True)

    # Converte colunas numéricas
    for col in ["patrimonio", "captacao", "resgate", "cotistas"]:
        df1[col] = df1[col].apply(converter_valor_brasileiro)

    # Extrai métricas
    patrimonio_final = df1["patrimonio"].iloc[0]
    patrimonio_inicial = df1["patrimonio"].iloc[-1]
    cotistas_finais = df1["cotistas"].iloc[0]
    captacoes_liquidas = df1["captacao"].sum() - df1["resgate"].sum()
    variacao_patrimonio = patrimonio_final - patrimonio_inicial

    st.subheader("📊 Resultados – Planilha 1")
    st.metric("Número de Cotistas (Data Final)", f"{cotistas_finais:,}".replace(",", "."))
    st.metric("Patrimônio Líquido (Data Final)", f"R$ {patrimonio_final:,}".replace(",", "."))
    st.metric("Captação Líquida no Período", f"R$ {captacoes_liquidas:,}".replace(",", "."))
    st.metric("Variação do Patrimônio Líquido", f"R$ {variacao_patrimonio:,}".replace(",", "."))

    st.divider()


# ==============================
# PARTE 2 - PLANILHA 2
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

    # Converte valores
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    # ==============================
    # Dicionários de busca
    # ==============================

    operacoes_compromissadas = [
        "APLICAÇÕES EM OPERAÇÕES COMPROMISSADAS",
        "LETRAS DO TESOURO NACIONAL",
        "NOTAS DO TESOURO NACIONAL",
        "LETRAS FINANCEIRAS DO TESOURO"
    ]

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
        "COTAS DE FUNDOS DE INVESTIMENTO",
        "BDR - CERTIFICADO DE DEPÓSITO DE AÇÕES",
        "COTAS DE FUNDO DE INVESTIMENTO ÍNDICE DE MERCADO"
    ]

    # ==============================
    # Cálculos
    # ==============================

    total_ativo = df2.loc[df2["Descrição da Conta"].str.contains("REALIZÁVEL", case=False, na=False), "Valor Saldo"].sum()

    soma_operacoes = df2.loc[df2["Descrição da Conta"].isin(operacoes_compromissadas), "Valor Saldo"].sum()
    soma_publicos = df2.loc[df2["Descrição da Conta"].isin(titulos_publicos), "Valor Saldo"].sum()
    soma_privados = df2.loc[df2["Descrição da Conta"].isin(titulos_privados), "Valor Saldo"].sum()

    st.subheader("📊 Resultados – Balancete")
    st.metric("Total de Ativos (Realizável)", f"R$ {total_ativo:,}".replace(",", "."))
    st.metric("Operações Compromissadas", f"R$ {soma_operacoes:,}".replace(",", "."))
    st.metric("Títulos Públicos", f"R$ {soma_publicos:,}".replace(",", "."))
    st.metric("Títulos Privados", f"R$ {soma_privados:,}".replace(",", "."))

    # ==============================
    # Gráfico de pizza ajustado
    # ==============================

    st.divider()
    st.subheader("📉 Composição da Carteira (apenas categorias)")

    labels = ["Operações Compromissadas", "Títulos Públicos", "Títulos Privados"]
    values = [soma_operacoes, soma_publicos, soma_privados]

    if sum(values) == 0:
        st.info("Sem valores para composição (todas as categorias com valor zero).")
    else:
        fig, ax = plt.subplots(figsize=(3, 3))  # pequeno
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
