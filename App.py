import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# CONFIGURAÇÃO INICIAL
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
# PARTE 1 – COTISTAS & PATRIMÔNIO
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

st.header("2. Estrutura da Carteira – Balancete (COSIF)")

uploaded_file2 = st.file_uploader(
    "Envie a planilha de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2"
)

if uploaded_file2:

    df2 = pd.read_excel(uploaded_file2)

    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)
    df2["Conta"] = df2["Conta"].astype(str)

    df2["Conta_limpa"] = (
        df2["Conta"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()

    # FILTRA ATIVO
    df_ativo = df2[df2["Conta_limpa"].str.startswith("1")].copy()

    # IDENTIFICA CONTAS ANALÍTICAS
    contas = df_ativo["Conta_limpa"].tolist()
    contas_set = set(contas)

    def eh_conta_analitica(conta):
        for outra in contas_set:
            if outra != conta and outra.startswith(conta):
                return False
        return True

    df_ativo["Conta_Analitica"] = df_ativo["Conta_limpa"].apply(eh_conta_analitica)
    df_analitico = df_ativo[df_ativo["Conta_Analitica"]].copy()

    # FILTRA TVM (13)
    df_tvm = df_analitico[df_analitico["Conta_limpa"].str.startswith("13")].copy()

    # =====================================================
    # CLASSIFICAÇÃO ECONÔMICA MELHORADA
    # =====================================================

    def classificar(descricao):

        descricao = descricao.upper()

        if "COMPROMISS" in descricao:
            return "Operações Compromissadas"

        if any(p in descricao for p in [
            "TESOURO",
            "LETRAS DO TESOURO",
            "NOTAS DO TESOURO",
            "LETRAS FINANCEIRAS DO TESOURO",
            "TÍTULOS PÚBLICOS"
        ]):
            return "Títulos Públicos"

        if any(p in descricao for p in [
            "DEBÊNTURES", "DEBENTURES",
            "LETRAS FINANCEIRAS",
            "CDB", "CERTIFICADOS",
            "CRI", "CRA",
            "COTAS", "FUNDO",
            "AÇÕES", "BDR",
            "RENDA VARIAVEL",
            "EXTERIOR"
        ]):
            return "Títulos Privados"

        if any(p in descricao for p in [
            "CAIXA", "DISPONIBIL", "BANCOS"
        ]):
            return "Caixa e Disponibilidades"

        if any(p in descricao for p in [
            "FUTURO", "OPÇÃO", "SWAP", "TERMO", "DERIVAT"
        ]):
            return "Derivativos"

        if any(p in descricao for p in [
            "PROVIS", "OBRIGA", "TAXA", "DESPESA"
        ]):
            return "Provisões e Obrigações"

        return "Outros"

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(classificar)

    # =====================================================
    # CONSOLIDAÇÃO
    # =====================================================

    consolidado = (
        df_tvm.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    total_tvm = consolidado["Valor Saldo"].sum()

    # =====================================================
    # RESUMO EXECUTIVO
    # =====================================================

    st.subheader("Resumo Executivo")

    colunas_metricas = st.columns(len(consolidado))

    for i in range(len(consolidado)):
        colunas_metricas[i].metric(
            consolidado.iloc[i]["Categoria"],
            formatar_moeda(consolidado.iloc[i]["Valor Saldo"])
        )

    st.metric("Total TVM", formatar_moeda(total_tvm))

    st.divider()

    # =====================================================
    # GRÁFICOS AJUSTADOS
    # =====================================================

    st.subheader("Distribuição da Carteira")

    col_graf1, col_graf2 = st.columns(2)

    # Pizza
    with col_graf1:
        fig1, ax1 = plt.subplots(figsize=(4, 4))
        ax1.pie(
            consolidado["Valor Saldo"],
            labels=consolidado["Categoria"],
            autopct='%1.1f%%',
            textprops={'fontsize': 9}
        )
        ax1.set_title("Alocação Percentual", fontsize=11)
        st.pyplot(fig1)

    # Barras
    with col_graf2:
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.barh(
            consolidado["Categoria"],
            consolidado["Valor Saldo"]
        )
        ax2.set_title("Exposição por Categoria", fontsize=11)
        ax2.tick_params(axis='y', labelsize=9)
        ax2.tick_params(axis='x', labelsize=8)
        st.pyplot(fig2)

    st.divider()

    # =====================================================
    # TABELA ANALÍTICA
    # =====================================================

    st.subheader("Detalhamento Analítico")

    tabela_final = df_tvm[
        ["Descrição da Conta", "Categoria", "Valor Saldo"]
    ].sort_values("Valor Saldo", ascending=False)

    tabela_final["Valor Saldo"] = tabela_final["Valor Saldo"].apply(formatar_moeda)

    st.dataframe(
        tabela_final,
        use_container_width=True
    )
