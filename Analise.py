import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analisador de Fundos", layout="wide")

st.title("📊 Analisador de Fundos de Investimento")

# Upload das planilhas
st.subheader("1️⃣ Upload das Planilhas")
cotistas_file = st.file_uploader("Envie a planilha de Cotistas e Patrimônio Líquido", type=["xlsx", "xls"])
balancete_file = st.file_uploader("Envie a planilha de Balancete", type=["xlsx", "xls"])

if cotistas_file and balancete_file:
    # ==== PLANILHA 1: COTISTAS E PATRIMÔNIO ====
    df_cotistas = pd.read_excel(cotistas_file)
    df_cotistas.columns = [col.strip() for col in df_cotistas.columns]

    # Converte valores monetários
    for col in ["Cota", "Variação da Cota Diária", "Patrimônio", "Captação", "Resgate"]:
        if col in df_cotistas.columns:
            df_cotistas[col] = (
                df_cotistas[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

    # Calcula métricas
    cotistas_final = int(df_cotistas["Cotistas"].iloc[0])
    pl_final = df_cotistas["Patrimônio"].iloc[0]
    pl_inicial = df_cotistas["Patrimônio"].iloc[-1]
    capt_liq = df_cotistas["Captação"].sum() - df_cotistas["Resgate"].sum()
    variacao_pl = pl_final - pl_inicial

    # ==== PLANILHA 2: BALANCETE ====
    df_balancete = pd.read_excel(balancete_file)
    df_balancete.columns = [col.strip() for col in df_balancete.columns]

    # Converte valores brasileiros para float padrão
    df_balancete["Valor Saldo"] = (
        df_balancete["Valor Saldo"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    # Busca total de ativos
    total_ativos = df_balancete.loc[
        df_balancete["Descrição da Conta"].str.contains("realizável", case=False, na=False),
        "Valor Saldo"
    ].sum()

    # Dicionários de busca
    operacoes = [
        "APLICAÇÕES EM OPERAÇÕES COMPROMISSADAS",
        "LETRAS DO TESOURO NACIONAL",
        "NOTAS DO TESOURO NACIONAL",
        "LETRAS FINANCEIRAS DO TESOURO",
    ]
    titulos_publicos = [
        "TÍTULOS PÚBLICOS FEDERAIS - TESOURO NACIONAL",
        "LETRAS FINANCEIRAS DO TESOURO",
        "LETRAS DO TESOURO NACIONAL",
        "NOTAS DO TESOURO NACIONAL",
    ]
    titulos_privados = [
        "LETRAS FINANCEIRAS", "DEBÊNTURES", "LETRAS FINANCEIRAS SUBORDINADAS",
        "COTAS DE FUNDOS DE INVESTIMENTO", "COTAS DE FUNDO DE RENDA FIXA",
        "COTAS DE FUNDO EM DIREITOS CREDITÓRIOS", "CERTIFICADOS DE DEPÓSITO BANCÁRIO",
        "CERTIFICADOS DE RECEBÍVEIS IMOBILIÁRIOS", "COTAS DE FUNDO MULTIMERCADO",
        "TÍTULOS DE RENDA VARIÁVEL", "AÇÕES DE COMPANHIAS ABERTAS",
        "COTAS DE FUNDO IMOBILIÁRIO", "APLICAÇÕES EM TÍTULOS E VALORES MOBILIÁRIOS NO EXTERIOR",
        "OUTROS TÍTULOS PRIVADOS - RENDA FIXA", "COTAS DE FUNDOS DE INVESTIMENTO NO EXTERIOR",
        "BDR – CERTIFICADO DE DEPÓSITO DE AÇÕES", "COTAS DE FUNDO DE INVESTIMENTO ÍNDICE DE MERCADO"
    ]

    # Filtra valores
    soma_operacoes = df_balancete[df_balancete["Descrição da Conta"].isin(operacoes)]["Valor Saldo"].sum()
    soma_publicos = df_balancete[df_balancete["Descrição da Conta"].isin(titulos_publicos)]["Valor Saldo"].sum()
    soma_privados = df_balancete[df_balancete["Descrição da Conta"].isin(titulos_privados)]["Valor Saldo"].sum()

    # ==== EXIBIÇÃO ====
    st.subheader("📈 Resultados - Cotistas e Patrimônio Líquido")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cotistas (final)", f"{cotistas_final:,}".replace(",", "."))
    col2.metric("PL Final (R$)", f"{int(pl_final):,}".replace(",", "."))
    col3.metric("Captação Líquida (R$)", f"{int(capt_liq):,}".replace(",", "."))
    col4.metric("Variação do PL (R$)", f"{int(variacao_pl):,}".replace(",", "."))

    st.divider()
    st.subheader("🏦 Resultados - Balancete")
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Ativos Totais (R$)", f"{int(total_ativos):,}".replace(",", "."))
    col6.metric("Operações Compromissadas (R$)", f"{int(soma_operacoes):,}".replace(",", "."))
    col7.metric("Títulos Públicos (R$)", f"{int(soma_publicos):,}".replace(",", "."))
    col8.metric("Títulos Privados (R$)", f"{int(soma_privados):,}".replace(",", "."))

    # ==== GRÁFICO DE PIZZA ====
    st.divider()
    st.subheader("📊 Composição da Carteira")

    labels = ["Operações Compromissadas", "Títulos Públicos", "Títulos Privados"]
    values = [soma_operacoes, soma_publicos, soma_privados]

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")  # deixa o gráfico circular

    st.pyplot(fig)

    st.success("✅ Análise concluída com sucesso!")

else:
    st.info("Envie as duas planilhas para iniciar a análise.")
