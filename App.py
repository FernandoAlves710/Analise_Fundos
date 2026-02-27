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
# CLASSE DA ÁRVORE CONTÁBIL
# =========================================================

class ContaNode:
    def __init__(self, codigo, descricao, valor):
        self.codigo = codigo
        self.descricao = descricao
        self.valor = float(valor)
        self.pai = None
        self.filhos = []

    def adicionar_filho(self, filho):
        self.filhos.append(filho)
        filho.pai = self

    def eh_folha(self):
        return len(self.filhos) == 0

# =========================================================
# FUNÇÕES DE HIERARQUIA (ROBUSTA)
# =========================================================

def limpar_codigo(codigo):
    return str(codigo).replace("-", "").strip()

def construir_arvore_tvm(df):

    df_13 = df[df["Conta"].astype(str).str.startswith("13")].copy()
    df_13["Conta"] = df_13["Conta"].apply(limpar_codigo)

    df_13 = df_13.sort_values("Conta", key=lambda x: x.str.len())

    nodes = {}

    for _, row in df_13.iterrows():
        nodes[row["Conta"]] = ContaNode(
            row["Conta"],
            row["Descrição da Conta"],
            row["Valor Saldo"]
        )

    codigos_ordenados = sorted(nodes.keys(), key=len)

    for codigo in codigos_ordenados:

        possiveis_pais = [
            c for c in codigos_ordenados
            if len(c) < len(codigo) and codigo.startswith(c)
        ]

        if possiveis_pais:
            pai_correto = max(possiveis_pais, key=len)
            nodes[pai_correto].adicionar_filho(nodes[codigo])

    return nodes

def encontrar_raiz(nodes):
    # menor código iniciando em 13
    return sorted(nodes.values(), key=lambda x: len(x.codigo))[0]

def listar_folhas(nodes):
    return [node for node in nodes.values() if node.eh_folha()]

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
# PARTE 2 – BALANCETE COM HIERARQUIA REAL
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
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()

    nodes = construir_arvore_tvm(df2)
    raiz = encontrar_raiz(nodes)

    total_tvm_oficial = raiz.valor
    folhas = listar_folhas(nodes)

    soma_folhas = sum(n.valor for n in folhas)
    diferenca = total_tvm_oficial - soma_folhas

    df_folhas = pd.DataFrame([{
        "Conta": n.codigo,
        "Descrição da Conta": n.descricao,
        "Valor Saldo": n.valor
    } for n in folhas])

    # =====================================================
    # CLASSIFICAÇÃO ECONÔMICA
    # =====================================================

    def classificar(descricao):

        if "COMPROMISS" in descricao:
            return "Operações Compromissadas"

        if any(p in descricao for p in [
            "TESOURO", "LETRAS DO TESOURO",
            "NOTAS DO TESOURO", "TÍTULOS PÚBLICOS"
        ]):
            return "Títulos Públicos"

        if any(p in descricao for p in [
            "DEBÊNTURES", "CDB", "CRI", "CRA",
            "FUNDO", "AÇÕES", "BDR"
        ]):
            return "Títulos Privados"

        if any(p in descricao for p in [
            "FUTURO", "OPÇÃO", "SWAP", "DERIVAT"
        ]):
            return "Derivativos"

        return "Outros"

    df_folhas["Categoria"] = df_folhas["Descrição da Conta"].apply(classificar)

    consolidado = (
        df_folhas.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    consolidado["Percentual"] = (
        consolidado["Valor Saldo"] / total_tvm_oficial
    ) * 100

    # =====================================================
    # RESUMO
    # =====================================================

    st.subheader("Resumo Executivo")

    colunas_metricas = st.columns(len(consolidado))

    for i in range(len(consolidado)):
        colunas_metricas[i].metric(
            consolidado.iloc[i]["Categoria"],
            formatar_moeda(consolidado.iloc[i]["Valor Saldo"])
        )

    st.metric("Total TVM (Oficial)", formatar_moeda(total_tvm_oficial))

    if abs(diferenca) > 1:
        st.warning(f"Diferença entre Total e Folhas: {formatar_moeda(diferenca)}")
    else:
        st.success("Validação estrutural OK – Total fecha com as folhas.")

    st.divider()

    # =====================================================
    # GRÁFICOS
    # =====================================================

    col_graf1, col_graf2 = st.columns([1, 1.2])

    with col_graf1:
        fig1, ax1 = plt.subplots(figsize=(3.2, 3.2))
        ax1.pie(
            consolidado["Valor Saldo"],
            labels=consolidado["Categoria"],
            autopct='%1.1f%%',
            textprops={'fontsize': 8}
        )
        st.pyplot(fig1)

    with col_graf2:
        fig2, ax2 = plt.subplots(figsize=(5.5, 2.8))
        ax2.barh(
            consolidado["Categoria"],
            consolidado["Percentual"]
        )
        ax2.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x:.1f}%")
        )
        st.pyplot(fig2)

    st.divider()

    # =====================================================
    # DETALHAMENTO
    # =====================================================

    st.subheader("Detalhamento das Contas Folha")

    df_folhas["Valor Saldo"] = df_folhas["Valor Saldo"].apply(formatar_moeda)
    st.dataframe(df_folhas, use_container_width=True)
