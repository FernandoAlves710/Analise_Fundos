import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json

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

def carregar_json_termos(uploaded):
    try:
        data = json.loads(uploaded.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None, "JSON inválido (esperado objeto/dict)."
        for k in ["Derivativos", "Títulos Públicos", "Títulos Privados"]:
            data.setdefault(k, [])
            if not isinstance(data[k], list):
                return None, f"JSON inválido: '{k}' deve ser lista."
        return data, None
    except Exception as e:
        return None, f"Erro ao ler JSON: {e}"

def exportar_json_termos(termos_extras: dict) -> bytes:
    return json.dumps(termos_extras, ensure_ascii=False, indent=2).encode("utf-8")

def list_to_text(lst):
    return "\n".join(lst) if lst else ""

def text_to_list(txt):
    return [t.strip().upper() for t in txt.split("\n") if t.strip()]

def identificar_folhas_por_prefixo(df_contas: pd.DataFrame, col_conta: str = "Conta") -> pd.DataFrame:
    """
    Marca e retorna apenas contas folha:
    uma conta é totalizadora se existir alguma outra conta que começa com ela e é diferente.
    """
    contas = df_contas[col_conta].astype(str).tolist()
    contas_set = set(contas)

    def eh_folha(c):
        # se existir "outra" que tenha prefixo = c, então c é pai (não folha)
        for outra in contas_set:
            if outra != c and outra.startswith(c):
                return False
        return True

    df = df_contas.copy()
    df["Folha"] = df[col_conta].apply(eh_folha)
    return df[df["Folha"]].copy()

# =========================================================
# SIDEBAR – TERMOS EXTRAS + EXCLUSÕES
# =========================================================

st.sidebar.header("Configurações (Parte 2)")

if "termos_extras" not in st.session_state:
    st.session_state.termos_extras = {
        "Derivativos": [],
        "Títulos Públicos": [],
        "Títulos Privados": []
    }

st.sidebar.subheader("Termos extras (opcional)")
st.sidebar.caption("Adiciona termos às regras base, sem alterar o que já funciona.")

json_upload = st.sidebar.file_uploader("Importar termos extras (JSON)", type=["json"])
if json_upload is not None:
    data, err = carregar_json_termos(json_upload)
    if err:
        st.sidebar.error(err)
    else:
        st.session_state.termos_extras = data
        st.sidebar.success("Termos extras importados.")

txt_der = st.sidebar.text_area(
    "Derivativos – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Derivativos"]),
    height=110
)

txt_pub = st.sidebar.text_area(
    "Títulos Públicos – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Públicos"]),
    height=110
)

txt_priv = st.sidebar.text_area(
    "Títulos Privados – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Privados"]),
    height=130
)

if st.sidebar.button("Aplicar termos extras"):
    st.session_state.termos_extras["Derivativos"] = text_to_list(txt_der)
    st.session_state.termos_extras["Títulos Públicos"] = text_to_list(txt_pub)
    st.session_state.termos_extras["Títulos Privados"] = text_to_list(txt_priv)
    st.sidebar.success("Termos extras aplicados.")

st.sidebar.download_button(
    "Exportar termos extras (JSON)",
    data=exportar_json_termos(st.session_state.termos_extras),
    file_name="termos_extras_classificacao.json",
    mime="application/json"
)

st.sidebar.divider()
st.sidebar.subheader("Exclusões (opcional)")
st.sidebar.caption(
    "Use para excluir contas (ou subárvores) pelo prefixo do código. "
    "Ex.: '1361' excluiria 13610009 e seus filhos."
)

exclusoes_texto = st.sidebar.text_area(
    "Prefixos para excluir (1 por linha)",
    value="",
    height=110
)
PREFIXOS_EXCLUIR = [p.strip() for p in exclusoes_texto.split("\n") if p.strip()]

# =========================================================
# REGRAS BASE (AS DO SEU CÓDIGO)
# =========================================================

BASE_DERIVATIVOS = ["FUTURO", "OPÇÃO", "SWAP", "DERIVAT"]
BASE_PUBLICOS = ["TESOURO", "LFT", "LTN", "NTN"]
BASE_PRIVADOS = [
    "DEBÊNTURE", "CDB", "CRI", "CRA",
    "FUNDO", "AÇÃO", "BDR",
    "LCI", "LCA"
]

def classificar(descricao: str) -> str | None:
    desc = (descricao or "").upper()

    der = BASE_DERIVATIVOS + st.session_state.termos_extras["Derivativos"]
    pub = BASE_PUBLICOS + st.session_state.termos_extras["Títulos Públicos"]
    priv = BASE_PRIVADOS + st.session_state.termos_extras["Títulos Privados"]

    if any(p in desc for p in der):
        return "Derivativos"
    if any(p in desc for p in pub):
        return "Títulos Públicos"
    if any(p in desc for p in priv):
        return "Títulos Privados"
    return None

def aplicar_exclusoes(df: pd.DataFrame) -> pd.DataFrame:
    if not PREFIXOS_EXCLUIR:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    for pref in PREFIXOS_EXCLUIR:
        mask &= ~df["Conta"].astype(str).str.startswith(pref)
    return df[mask].copy()

# =========================================================
# PARTE 1 – COTISTAS & PATRIMÔNIO LÍQUIDO (NÃO MEXER)
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
# PARTE 2 – EXPOSIÇÃO ECONÔMICA (MULTI-UPLOAD + FOLHAS)
# =========================================================

st.header("2. Exposição Econômica da Carteira (TVM = 100%)")

uploaded_files2 = st.file_uploader(
    "Envie uma ou mais planilhas de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2_multi",
    accept_multiple_files=True
)

def processar_balancete(df2: pd.DataFrame):
    df2["Conta"] = df2["Conta"].astype(str).str.strip()
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    total_row = df2[df2["Conta"] == "13000004"]
    if total_row.empty:
        return None, None, None, None, "Conta 13000004 não encontrada."

    total_tvm = float(total_row["Valor Saldo"].iloc[0])

    # universo: grupo 13 (exceto total)
    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    # aplica exclusões opcionais
    df_tvm = aplicar_exclusoes(df_tvm)

    # >>> ponto CRUCIAL: remover totalizadores e manter apenas folhas <<<
    df_folhas = identificar_folhas_por_prefixo(df_tvm, col_conta="Conta")

    # classifica apenas as folhas (evita dupla contagem)
    df_folhas["Categoria"] = df_folhas["Descrição da Conta"].apply(classificar)

    df_class = df_folhas[df_folhas["Categoria"].notna()].copy()
    df_nao_class = df_folhas[df_folhas["Categoria"].isna()].copy()

    consolidado = (
        df_class.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )
    consolidado["Percentual"] = (consolidado["Valor Saldo"] / total_tvm) * 100

    return total_tvm, df_class, df_nao_class, consolidado, None

if uploaded_files2:

    resumo_consolidado = []

    for f in uploaded_files2:
        df2 = pd.read_excel(f)
        total_tvm, df_class, df_nao_class, consolidado, err = processar_balancete(df2)

        if err:
            st.error(f"[{f.name}] {err}")
            continue

        with st.expander(f"Balancete: {f.name}", expanded=(len(uploaded_files2) == 1)):

            st.subheader("Resumo Executivo (somando apenas contas folha)")

            cols = st.columns(max(1, len(consolidado)))

            for i in range(len(consolidado)):
                categoria = consolidado.iloc[i]["Categoria"]
                valor_categoria = float(consolidado.iloc[i]["Valor Saldo"])

                with cols[i]:
                    st.metric(categoria, formatar_moeda(valor_categoria))

                    with st.expander("Ver composição"):
                        df_cat = df_class[df_class["Categoria"] == categoria].copy()
                        soma_check = float(df_cat["Valor Saldo"].sum())
                        st.write("Soma das contas (folhas):", formatar_moeda(soma_check))

                        df_show = df_cat.sort_values("Valor Saldo", ascending=False).copy()
                        df_show["Valor Saldo"] = df_show["Valor Saldo"].apply(formatar_moeda)

                        st.dataframe(
                            df_show[["Conta", "Descrição da Conta", "Valor Saldo"]],
                            use_container_width=True
                        )

            st.metric("Total TVM (100%)", formatar_moeda(total_tvm))
            st.divider()

            # Gráficos
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
                st.warning("Contas folha não classificadas (revisar termos extras ou exclusões):")
                df_nc = df_nao_class.sort_values("Valor Saldo", ascending=False).copy()
                df_nc["Valor Saldo"] = df_nc["Valor Saldo"].apply(formatar_moeda)
                st.dataframe(df_nc[["Conta", "Descrição da Conta", "Valor Saldo"]], use_container_width=True)

            st.subheader("Contas folha consideradas na análise")
            df_final = df_class.copy()
            df_final["Valor Saldo"] = df_final["Valor Saldo"].apply(formatar_moeda)
            st.dataframe(df_final, use_container_width=True)

        row = {"Arquivo": f.name, "Total TVM": total_tvm}
        for _, r in consolidado.iterrows():
            row[r["Categoria"]] = float(r["Valor Saldo"])
            row[f"% {r['Categoria']}"] = float(r["Percentual"])
        resumo_consolidado.append(row)

    if resumo_consolidado:
        st.divider()
        st.header("Resumo Consolidado (todos os balancetes)")

        df_resumo = pd.DataFrame(resumo_consolidado).fillna(0)

        for c in ["Total TVM", "Títulos Públicos", "Títulos Privados", "Derivativos"]:
            if c in df_resumo.columns:
                df_resumo[c] = df_resumo[c].apply(formatar_moeda)

        for c in [c for c in df_resumo.columns if c.startswith("% ")]:
            df_resumo[c] = df_resumo[c].apply(lambda x: f"{float(x):.2f}%")

        st.dataframe(df_resumo, use_container_width=True)

else:
    st.info("Envie um ou mais balancetes para iniciar a análise.")
