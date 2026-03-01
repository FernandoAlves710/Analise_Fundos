import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import json
from io import BytesIO

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

def baixar_json(dados: dict, nome: str = "regras_classificacao.json"):
    conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
    return conteudo.encode("utf-8"), nome

def compilar_regras(regras):
    compiled = []
    for categoria, patterns in regras.items():
        safe_patterns = [p for p in patterns if isinstance(p, str) and p.strip()]
        if not safe_patterns:
            continue
        joined = "(" + ")|(".join(safe_patterns) + ")"
        compiled.append((categoria, re.compile(joined, flags=re.IGNORECASE)))
    return compiled

def classificar_por_regex(descricao: str, compiled_rules):
    if not isinstance(descricao, str):
        return None
    for categoria, rgx in compiled_rules:
        if rgx.search(descricao):
            return categoria
    return None

# =========================================================
# REGRAS PADRÃO
# =========================================================

DEFAULT_RULES = {
    "Derivativos": [
        r"\bDERIVAT",
        r"\bSWAP\b",
        r"\bOPÇ?A?O\b",
        r"\bFUTURO\b",
        r"\bTERMO\b",
        r"\bFORWARD\b",
        r"\bDI1\b",
    ],
    "Títulos Públicos": [
        r"\bTESOURO\b",
        r"\bT[IÍ]TULO[S]?\s+P[UÚ]BLICO[S]?\b",
        r"\bLTN\b",
        r"\bLFT\b",
        r"\bNTN\b",
        r"\bNTN-[A-Z0-9]+\b",
    ],
    "Títulos Privados": [
        r"\bDEB[ÊE]NTUR",
        r"\bCDB\b",
        r"\bCRI\b",
        r"\bCRA\b",
        r"\bLCI\b",
        r"\bLCA\b",
        r"\bFIDC\b",
        r"\bFUNDO[S]?\b",
        r"\bCOTA[S]?\b",
        r"\bA[CÇ][AÃ]O\b",
        r"\bBDR\b",
        r"\bCERTIFICAD",
        r"\bRECEB[IÍ]VEI",
    ]
}

# =========================================================
# SIDEBAR – REGRAS EDITÁVEIS + IMPORT/EXPORT
# =========================================================

st.sidebar.header("Regras de Classificação (Regex)")

if "regras" not in st.session_state:
    st.session_state.regras = DEFAULT_RULES

st.sidebar.caption("Edite as regras abaixo. Cada linha é um padrão regex.")

def regras_para_textarea(regras: dict) -> dict:
    return {k: "\n".join(v) for k, v in regras.items()}

def textarea_para_regras(textareas: dict) -> dict:
    regras = {}
    for categoria, texto in textareas.items():
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]
        regras[categoria] = linhas
    return regras

# Import JSON
uploaded_rules = st.sidebar.file_uploader(
    "Importar regras (JSON)",
    type=["json"],
    key="rules_json"
)

if uploaded_rules is not None:
    try:
        regras_importadas = json.loads(uploaded_rules.read().decode("utf-8"))
        if isinstance(regras_importadas, dict):
            st.session_state.regras = regras_importadas
            st.sidebar.success("Regras importadas com sucesso.")
        else:
            st.sidebar.error("JSON inválido: esperado um objeto (dict).")
    except Exception as e:
        st.sidebar.error(f"Erro ao ler JSON: {e}")

# Editor por categoria
textareas = regras_para_textarea(st.session_state.regras)

textareas["Derivativos"] = st.sidebar.text_area(
    "Derivativos",
    value=textareas.get("Derivativos", ""),
    height=160
)

textareas["Títulos Públicos"] = st.sidebar.text_area(
    "Títulos Públicos",
    value=textareas.get("Títulos Públicos", ""),
    height=160
)

textareas["Títulos Privados"] = st.sidebar.text_area(
    "Títulos Privados",
    value=textareas.get("Títulos Privados", ""),
    height=180
)

# Aplicar mudanças
if st.sidebar.button("Aplicar regras"):
    st.session_state.regras = textarea_para_regras(textareas)
    st.sidebar.success("Regras aplicadas.")

# Export JSON
json_bytes, json_name = baixar_json(st.session_state.regras)
st.sidebar.download_button(
    label="Exportar regras (JSON)",
    data=json_bytes,
    file_name=json_name,
    mime="application/json"
)

# =========================================================
# COMPILA REGRAS ATIVAS
# =========================================================

compiled_rules = compilar_regras(st.session_state.regras)

# =========================================================
# PARTE 1 – COTISTAS & PATRIMÔNIO LÍQUIDO
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
# PARTE 2 – MULTI-UPLOAD BALANCETE
# =========================================================

st.header("2. Exposição Econômica da Carteira (TVM = 100%)")

uploaded_files2 = st.file_uploader(
    "Envie uma ou mais planilhas de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2_multi",
    accept_multiple_files=True
)

def analisar_balancete(df2: pd.DataFrame, nome_arquivo: str):
    df2["Conta"] = df2["Conta"].astype(str).str.strip()
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    total_row = df2[df2["Conta"] == "13000004"]
    if total_row.empty:
        return None, None, None, f"[{nome_arquivo}] Conta 13000004 não encontrada."

    total_tvm = float(total_row["Valor Saldo"].iloc[0])

    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    df_tvm["Categoria"] = df_tvm["Descrição da Conta"].apply(
        lambda x: classificar_por_regex(x, compiled_rules)
    )

    df_nao_class = df_tvm[df_tvm["Categoria"].isna()].copy()
    df_class = df_tvm[df_tvm["Categoria"].notna()].copy()

    consolidado = (
        df_class.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    consolidado["Percentual"] = (consolidado["Valor Saldo"] / total_tvm) * 100

    return total_tvm, df_class, df_nao_class, consolidado

if uploaded_files2:
    resumo_geral = []

    for f in uploaded_files2:
        df2 = pd.read_excel(f)
        total_tvm, df_class, df_nao_class, consolidado = analisar_balancete(df2, f.name)

        if isinstance(consolidado, str):
            st.error(consolidado)
            continue

        with st.expander(f"Balancete: {f.name}", expanded=(len(uploaded_files2) == 1)):

            st.subheader("Resumo Executivo")
            cols = st.columns(max(1, len(consolidado)))

            for i in range(len(consolidado)):
                categoria = consolidado.iloc[i]["Categoria"]
                valor_categoria = float(consolidado.iloc[i]["Valor Saldo"])

                with cols[i]:
                    st.metric(categoria, formatar_moeda(valor_categoria))

                    with st.expander("Ver composição"):
                        df_cat = df_class[df_class["Categoria"] == categoria].copy()
                        soma_check = float(df_cat["Valor Saldo"].sum())
                        st.write("Soma das contas:", formatar_moeda(soma_check))

                        df_show = df_cat.sort_values("Valor Saldo", ascending=False).copy()
                        df_show["Valor Saldo"] = df_show["Valor Saldo"].apply(formatar_moeda)

                        st.dataframe(
                            df_show[["Conta", "Descrição da Conta", "Valor Saldo"]],
                            use_container_width=True
                        )

            st.metric("Total TVM (100%)", formatar_moeda(total_tvm))
            st.divider()

            col1, col2 = st.columns([1, 1.2])

            with col1:
                fig1, ax1 = plt.subplots(figsize=(3, 3))
                ax1.pie(
                    consolidado["Percentual"],
                    labels=consolidado["Categoria"],
                    autopct='%1.1f%%'
                )
                st.pyplot(fig1)

            with col2:
                fig2, ax2 = plt.subplots(figsize=(6, 3))
                ax2.barh(consolidado["Categoria"], consolidado["Percentual"])
                ax2.xaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, _: f"{x:.1f}%")
                )
                st.pyplot(fig2)

            st.divider()

            if not df_nao_class.empty:
                st.warning("Contas não classificadas (revisar regras):")
                df_nc = df_nao_class.sort_values("Valor Saldo", ascending=False).copy()
                df_nc["Valor Saldo"] = df_nc["Valor Saldo"].apply(formatar_moeda)
                st.dataframe(df_nc[["Conta", "Descrição da Conta", "Valor Saldo"]], use_container_width=True)

            st.subheader("Contas Consideradas na Análise")
            df_final = df_class.copy()
            df_final["Valor Saldo"] = df_final["Valor Saldo"].apply(formatar_moeda)
            st.dataframe(df_final, use_container_width=True)

        row = {"Arquivo": f.name, "Total TVM": total_tvm}
        for _, r in consolidado.iterrows():
            row[r["Categoria"]] = float(r["Valor Saldo"])
            row[f"% {r['Categoria']}"] = float(r["Percentual"])
        resumo_geral.append(row)

    if resumo_geral:
        st.divider()
        st.header("Resumo Consolidado (todos os balancetes)")
        df_resumo = pd.DataFrame(resumo_geral).fillna(0)

        for c in ["Total TVM", "Títulos Públicos", "Títulos Privados", "Derivativos"]:
            if c in df_resumo.columns:
                df_resumo[c] = df_resumo[c].apply(formatar_moeda)

        for c in [c for c in df_resumo.columns if c.startswith("% ")]:
            df_resumo[c] = df_resumo[c].apply(lambda x: f"{float(x):.2f}%")

        st.dataframe(df_resumo, use_container_width=True)
else:
    st.info("Envie um ou mais balancetes para iniciar a análise.")
