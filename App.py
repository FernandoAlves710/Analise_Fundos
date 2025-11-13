import pandas as pd
import streamlit as st

# ==========================
# 📘 CONFIGURAÇÕES INICIAIS
# ==========================
st.set_page_config(page_title="Análise de Balancete", layout="wide")

st.title("📊 Análise de Balancete de Fundos")
st.write("Este painel consolida automaticamente as categorias Compromissadas, Títulos Públicos e Títulos Privados com base na planilha 2 (balancete).")

# Upload do arquivo Excel
uploaded_file = st.file_uploader("Carregue a planilha 2 (balancete)", type=["xlsx", "xls"])

if uploaded_file:
    # ==========================
    # 📂 LEITURA DO ARQUIVO
    # ==========================
    df = pd.read_excel(uploaded_file)

    # Padronização dos nomes das colunas
    df.columns = [col.strip().lower() for col in df.columns]

    # Tentando identificar colunas essenciais
    col_codigo = next((c for c in df.columns if "cód" in c or "codigo" in c or "code" in c), None)
    col_desc = next((c for c in df.columns if "descr" in c or "conta" in c or "nome" in c), None)
    col_valor = next((c for c in df.columns if "valor" in c or "saldo" in c), None)

    if not all([col_codigo, col_desc, col_valor]):
        st.error("❌ Não foi possível identificar as colunas de código, descrição e valor. Verifique os nomes na planilha.")
    else:
        df = df[[col_codigo, col_desc, col_valor]].copy()
        df.columns = ["codigo", "descricao", "valor"]

        # Remove linhas vazias ou nulas
        df.dropna(subset=["descricao", "valor"], inplace=True)
        df["descricao"] = df["descricao"].astype(str).str.strip()
        df["codigo"] = df["codigo"].astype(str).str.strip()

        # ==========================
        # 🧠 CLASSIFICAÇÃO AUTOMÁTICA
        # ==========================
        categorias = {
            "Compromissadas": ["compromissadas"],
            "Títulos Públicos": ["tesouro", "lft", "ltn", "ntn", "título público"],
            "Títulos Privados": ["debênture", "debentures", "fundo", "fii", "fidc", "cri", "cra", "cotas"]
        }

        def classificar_conta(descricao):
            desc = descricao.lower()
            for cat, termos in categorias.items():
                if any(t in desc for t in termos):
                    return cat
            return None

        df["categoria"] = df["descricao"].apply(classificar_conta)

        # ==========================
        # 🧮 EVITA DUPLICAÇÕES
        # ==========================
        # Identifica hierarquia (contas pai e filhas)
        # Exemplo: 1.1 é pai de 1.1.1, 1.1.2
        def is_child(code1, code2):
            return code2.startswith(code1 + ".") and code1 != code2

            # Função para eliminar valores de contas "pai"
        def remover_pais(df):
            pais = []
            for code in df["codigo"]:
                filhos = [c for c in df["codigo"] if is_child(code, c)]
                if filhos:
                    pais.append(code)
            return df[~df["codigo"].isin(pais)]

        df_sem_pais = remover_pais(df)

        # ==========================
        # 📊 CONSOLIDAÇÃO FINAL
        # ==========================
        resumo = (
            df_sem_pais[df_sem_pais["categoria"].notna()]
            .groupby("categoria", as_index=False)["valor"]
            .sum()
        )

        # Exibe os resultados
        st.subheader("📈 Resultado Consolidado")
        st.dataframe(resumo.style.format({"valor": "R$ {:,.2f}"}))

        # ==========================
        # 📉 GRÁFICO
        # ==========================
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.bar(resumo["categoria"], resumo["valor"])
        ax.set_title("Distribuição por Categoria")
        ax.set_ylabel("Valor (R$)")
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=15)
        st.pyplot(fig)

        # ==========================
        # 💾 DOWNLOAD OPCIONAL
        # ==========================
        csv = resumo.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="📥 Baixar resumo em CSV",
            data=csv,
            file_name="resumo_balancete.csv",
            mime="text/csv"
        )

else:
    st.info("⬆️ Carregue o arquivo da planilha 2 (balancete) para iniciar a análise.")
