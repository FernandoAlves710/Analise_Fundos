import streamlit as st
import pandas as pd

# =======================
# ⚙️ CONFIGURAÇÕES INICIAIS
# =======================
st.set_page_config(page_title="Análise de Ativos Financeiros", layout="wide")
st.title("📊 Análise da Carteira de Ativos Financeiros")

# =======================
# 📂 LEITURA DO ARQUIVO
# =======================
uploaded_file = st.file_uploader("Envie o arquivo Balancete.xlsx", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Balancete")

    # Normaliza colunas
    df.columns = [col.strip().upper() for col in df.columns]
    df = df.rename(columns={
        "CONTA": "codigo",
        "NOME": "nome",
        "VALOR": "valor"
    })

    # Mantém apenas colunas relevantes
    df = df[["codigo", "nome", "valor"]]
    df["codigo"] = df["codigo"].astype(str)
    
    # =======================
    # 🧩 DEFINIÇÃO DAS CONTAS
    # =======================
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

    # =======================
    # 🔍 FUNÇÕES AUXILIARES
    # =======================
    def buscar_subcontas(df, termo):
        """
        Busca linhas do balancete que contenham determinado termo no nome.
        Evita duplicar subtotais (somente filhos diretos).
        """
        encontrados = df[df["nome"].str.contains(termo, case=False, na=False)]
        # Remove potenciais duplicatas
        encontrados = encontrados.drop_duplicates(subset=["nome"], keep="first")
        return encontrados

    def exibir_grupo(titulo, lista_termos):
        """
        Exibe o grupo (pai) com subtotais e detalhamento no Streamlit.
        """
        st.markdown(f"### {titulo}")

        total_grupo = 0
        for termo in lista_termos:
            sub_df = buscar_subcontas(df, termo)
            if not sub_df.empty:
                subtotal = sub_df["valor"].sum()
                total_grupo += subtotal

                with st.expander(f"📂 {termo} — **R$ {subtotal:,.2f}**", expanded=False):
                    st.dataframe(sub_df[["nome", "valor"]].style.format({"valor": "R$ {:,.2f}"}), hide_index=True)

        st.markdown(f"**💰 Total {titulo}: R$ {total_grupo:,.2f}**")
        st.markdown("---")
        return total_grupo

    # =======================
    # 🧾 EXIBIÇÃO DOS RESULTADOS
    # =======================
    col1, col2, col3 = st.columns(3)

    with col1:
        total_compromissadas = exibir_grupo("Aplicações em Operações Compromissadas", compromissadas)
    with col2:
        total_publicos = exibir_grupo("Títulos Públicos", titulos_publicos)
    with col3:
        total_privados = exibir_grupo("Títulos Privados", titulos_privados)

    # =======================
    # 📊 RESUMO FINAL
    # =======================
    st.subheader("Resumo Consolidado")
    resumo_df = pd.DataFrame({
        "Categoria": ["Compromissadas", "Títulos Públicos", "Títulos Privados"],
        "Total (R$)": [total_compromissadas, total_publicos, total_privados]
    })

    st.dataframe(resumo_df.style.format({"Total (R$)": "R$ {:,.2f}"}), hide_index=True)
    st.markdown(f"### 💼 Total Geral da Carteira: **R$ {(total_compromissadas + total_publicos + total_privados):,.2f}**")

else:
    st.info("Envie o arquivo **Balancete.xlsx** para iniciar a análise.")
