# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
from io import BytesIO
from datetime import datetime

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
    try:
        v = float(valor)
    except:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def carregar_config(uploaded):
    try:
        data = json.loads(uploaded.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None, "Arquivo inválido (esperado dicionário)."
        for k in ["Derivativos", "Títulos Públicos", "Títulos Privados"]:
            data.setdefault(k, [])
            if not isinstance(data[k], list):
                return None, f"Arquivo inválido: '{k}' deve ser uma lista."
        return data, None
    except Exception as e:
        return None, f"Erro ao ler arquivo: {e}"

def exportar_config(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

def list_to_text(lst):
    return "\n".join(lst) if lst else ""

def text_to_list(txt):
    return [t.strip().upper() for t in txt.split("\n") if t.strip()]

def excel_bytes_relatorio(
    arquivo_nome: str,
    total_tvm: float,
    consolidado: pd.DataFrame,
    df_consideradas: pd.DataFrame,
    df_nao_classificadas: pd.DataFrame,
    df_log: pd.DataFrame
) -> bytes:
    output = BytesIO()

    resumo_total = pd.DataFrame([{
        "Arquivo": arquivo_nome,
        "Total TVM": formatar_moeda(total_tvm)
    }])

    resumo = consolidado.copy()
    if not resumo.empty:
        resumo["Valor (R$)"] = resumo["Valor Saldo"].apply(formatar_moeda)
        resumo["Percentual"] = resumo["Percentual"].apply(lambda x: f"{float(x):.2f}%")
        resumo = resumo[["Categoria", "Valor (R$)", "Percentual"]]

    cons = df_consideradas.copy()
    if not cons.empty:
        cons = cons[["Conta", "Descrição da Conta", "Categoria", "Valor Saldo"]].copy()
        cons["Valor Saldo"] = cons["Valor Saldo"].apply(formatar_moeda)

    nc = df_nao_classificadas.copy()
    if not nc.empty:
        nc = nc[["Conta", "Descrição da Conta", "Valor Saldo"]].copy()
        nc["Valor Saldo"] = nc["Valor Saldo"].apply(formatar_moeda)

    lg = df_log.copy() if df_log is not None else pd.DataFrame()
    if not lg.empty and "Valor" in lg.columns:
        lg["Valor"] = lg["Valor"].apply(formatar_moeda)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumo_total.to_excel(writer, index=False, sheet_name="Resumo", startrow=0)
        if not resumo.empty:
            resumo.to_excel(writer, index=False, sheet_name="Resumo", startrow=3)

        cons.to_excel(writer, index=False, sheet_name="Contas_Consideradas")
        nc.to_excel(writer, index=False, sheet_name="Nao_Classificadas")
        if not lg.empty:
            lg.to_excel(writer, index=False, sheet_name="Log")
        else:
            pd.DataFrame([{"Info": "Sem registros no log."}]).to_excel(writer, index=False, sheet_name="Log")

    return output.getvalue()

# =========================================================
# CONFIG PADRÃO DO BANCO (OFICIAL NO CÓDIGO)
# =========================================================
CONFIG_PADRAO_BANCO = {
    "Derivativos": ["FUTURO", "OPÇÃO", "SWAP", "DERIVAT"],
    "Títulos Públicos": ["TESOURO", "LFT", "LTN", "NTN"],
    "Títulos Privados": [
        "DEBÊNTURE", "DEBENTURE", "CDB", "CRI", "CRA",
        "FUNDO", "COTAS", "AÇÃO", "ACAO", "BDR",
        "LCI", "LCA",
        "RENDA VARIAVEL", "RENDA VARIÁVEL",
        "CERTIFICADOS DE DEPÓSITO BANCÁRIO",
        "CERTIFICADOS DE DEPOSITO BANCARIO",
        "DEPÓSITO BANCÁRIO",
        "DEPOSITO BANCARIO",
        "LETRA FINANCEIRA",
        "LETRAS FINANCEIRAS",
        "LETRA FINANCEIRA SUBORDINADA",
        "LETRAS FINANCEIRAS SUBORDINADAS"
    ]
}

# =========================================================
# SIDEBAR – CONFIGURAÇÃO DO TIME + EXCLUSÕES POR CATEGORIA
# =========================================================
st.sidebar.header("Configurações")

st.sidebar.subheader("Configuração do time (importar/exportar)")
st.sidebar.caption("Se aparecer “não classificado”, adicione termos aqui.")

if "termos_extras" not in st.session_state:
    st.session_state.termos_extras = {
        "Derivativos": [],
        "Títulos Públicos": [],
        "Títulos Privados": []
    }

if "excluir_por_categoria" not in st.session_state:
    st.session_state.excluir_por_categoria = {
        "Derivativos": [],
        "Títulos Públicos": [],
        "Títulos Privados": []
    }

st.sidebar.download_button(
    "Baixar configuração padrão do banco",
    data=exportar_config(CONFIG_PADRAO_BANCO),
    file_name="config_padrao_banco.json",
    mime="application/json",
    key="download_cfg_padrao"
)

cfg_upload = st.sidebar.file_uploader("Importar configuração do time", type=["json"], key="upload_cfg_time")
if cfg_upload is not None:
    data, err = carregar_config(cfg_upload)
    if err:
        st.sidebar.error(err)
    else:
        st.session_state.termos_extras = data
        st.sidebar.success("Configuração importada.")

st.sidebar.markdown("*Adicionar termos (extras)*")
txt_der_add = st.sidebar.text_area(
    "Derivativos — adicionar (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Derivativos"]),
    height=80,
    key="txt_der_add"
)
txt_pub_add = st.sidebar.text_area(
    "Títulos Públicos — adicionar (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Públicos"]),
    height=80,
    key="txt_pub_add"
)
txt_priv_add = st.sidebar.text_area(
    "Títulos Privados — adicionar (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Privados"]),
    height=100,
    key="txt_priv_add"
)

st.sidebar.markdown("*Excluir termos (por categoria)*")
st.sidebar.caption("Se um termo estiver aqui, contas classificadas nessa categoria serão removidas do cálculo.")
txt_der_exc = st.sidebar.text_area(
    "Derivativos — excluir (1 por linha)",
    value=list_to_text(st.session_state.excluir_por_categoria["Derivativos"]),
    height=80,
    key="txt_der_exc"
)
txt_pub_exc = st.sidebar.text_area(
    "Títulos Públicos — excluir (1 por linha)",
    value=list_to_text(st.session_state.excluir_por_categoria["Títulos Públicos"]),
    height=80,
    key="txt_pub_exc"
)
txt_priv_exc = st.sidebar.text_area(
    "Títulos Privados — excluir (1 por linha)",
    value=list_to_text(st.session_state.excluir_por_categoria["Títulos Privados"]),
    height=100,
    key="txt_priv_exc"
)

if st.sidebar.button("Aplicar termos", key="btn_aplicar_termos"):
    st.session_state.termos_extras["Derivativos"] = text_to_list(txt_der_add)
    st.session_state.termos_extras["Títulos Públicos"] = text_to_list(txt_pub_add)
    st.session_state.termos_extras["Títulos Privados"] = text_to_list(txt_priv_add)

    st.session_state.excluir_por_categoria["Derivativos"] = text_to_list(txt_der_exc)
    st.session_state.excluir_por_categoria["Títulos Públicos"] = text_to_list(txt_pub_exc)
    st.session_state.excluir_por_categoria["Títulos Privados"] = text_to_list(txt_priv_exc)

    st.sidebar.success("Configurações aplicadas.")

st.sidebar.divider()
st.sidebar.subheader("Modo avançado (só se necessário)")
st.sidebar.caption("Exclui blocos de contas por prefixo (1 por linha). Ex.: 1361")

exclusoes_texto = st.sidebar.text_area("Prefixos para excluir", value="", height=90, key="txt_prefixos_excluir")
PREFIXOS_EXCLUIR = [p.strip() for p in exclusoes_texto.split("\n") if p.strip()]

TOL_ABS = st.sidebar.number_input(
    "Tolerância p/ identificar totalizadoras (R$)",
    min_value=0.0,
    value=1.0,
    step=0.5,
    key="num_tol_abs"
)

# =========================================================
# CLASSIFICAÇÃO + AMBIGUIDADE
# =========================================================
BASE_DERIVATIVOS = CONFIG_PADRAO_BANCO["Derivativos"]
BASE_PUBLICOS = CONFIG_PADRAO_BANCO["Títulos Públicos"]
BASE_PRIVADOS = CONFIG_PADRAO_BANCO["Títulos Privados"]

AMBIGUOS = [
    "GARANTIA", "DADOS EM GARANTIA", "EM GARANTIA",
    "MARGEM", "BOLSA", "OPERAÇÕES EM BOLSA", "OPERACOES EM BOLSA",
    "VINCUL", "BLOQUEAD", "CUSTOD", "DEPOSITO EM GARANTIA",
    "COLATERAL"
]

def classificar(descricao: str):
    desc = (descricao or "").upper()

    der = BASE_DERIVATIVOS + st.session_state.termos_extras["Derivativos"]
    pub = BASE_PUBLICOS + st.session_state.termos_extras["Títulos Públicos"]
    priv = BASE_PRIVADOS + st.session_state.termos_extras["Títulos Privados"]

    if any(t in desc for t in der):
        return "Derivativos"
    if any(t in desc for t in pub):
        return "Títulos Públicos"
    if any(t in desc for t in priv):
        return "Títulos Privados"
    return None

def eh_ambigua(descricao: str) -> bool:
    desc = (descricao or "").upper()
    return any(p in desc for p in AMBIGUOS)

def aplicar_exclusoes_prefixo(df: pd.DataFrame) -> pd.DataFrame:
    if not PREFIXOS_EXCLUIR:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    for pref in PREFIXOS_EXCLUIR:
        mask &= ~df["Conta"].astype(str).str.startswith(pref)
    return df[mask].copy()

def aplicar_exclusoes_por_categoria(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df, pd.DataFrame()

    logs = []
    keep_mask = pd.Series([True] * len(df), index=df.index)

    for cat, termos in st.session_state.excluir_por_categoria.items():
        if not termos:
            continue

        mask_cat = df["Categoria"] == cat
        if not mask_cat.any():
            continue

        desc_series = df.loc[mask_cat, "Descrição da Conta"].astype(str).str.upper()

        excluir_idx = []
        for termo in termos:
            hits = desc_series.str.contains(termo, na=False)
            if hits.any():
                excluir_idx.extend(hits[hits].index.tolist())

        if excluir_idx:
            excluir_idx = list(set(excluir_idx))
            keep_mask.loc[excluir_idx] = False

            for i in excluir_idx:
                logs.append({
                    "Conta": df.at[i, "Conta"],
                    "Descrição": df.at[i, "Descrição da Conta"],
                    "Valor": float(df.at[i, "Valor Saldo"]),
                    "Regra": "Exclusão por categoria",
                    "Decisão": f"Removida ({cat})"
                })

    df_out = df.loc[keep_mask].copy()
    df_log = pd.DataFrame(logs)
    return df_out, df_log

# =========================================================
# COLAPSO HÍBRIDO DE TOTALIZADORAS
# =========================================================
def chave_grupo_cosif(conta: str) -> str:
    c = str(conta).strip()
    if len(c) >= 6:
        return c[:-3]
    return c[:-1] if len(c) > 1 else c

def colapsar_totalizadoras_hibrido(df: pd.DataFrame, tol_abs: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    work["Conta"] = work["Conta"].astype(str).str.strip()
    work["Valor Saldo"] = pd.to_numeric(work["Valor Saldo"], errors="coerce").fillna(0.0)
    work["Grupo"] = work["Conta"].apply(chave_grupo_cosif)

    logs = []
    out_rows = []

    for _, g in work.groupby("Grupo", dropna=False):

        amb_mask = g["Descrição da Conta"].apply(eh_ambigua)
        if amb_mask.any():
            for _, row in g[amb_mask].iterrows():
                logs.append({
                    "Conta": row["Conta"],
                    "Descrição": row["Descrição da Conta"],
                    "Valor": float(row["Valor Saldo"]),
                    "Regra": "Ambígua",
                    "Decisão": "Removida"
                })
            g = g[~amb_mask].copy()
            if g.empty:
                continue

        if len(g) == 1:
            out_rows.append(g)
            continue

        total_grupo = float(g["Valor Saldo"].sum())

        totalizador_idx = None
        for idx, row in g.iterrows():
            v = float(row["Valor Saldo"])
            soma_outros = total_grupo - v
            if soma_outros > 0 and abs(v - soma_outros) <= tol_abs:
                totalizador_idx = idx
                break

        if totalizador_idx is None:
            out_rows.append(g)
            continue

        totalizador = g.loc[totalizador_idx]
        cat_total = classificar(str(totalizador["Descrição da Conta"]))
        filhos = g.drop(index=totalizador_idx)

        if cat_total is not None:
            logs.append({
                "Conta": totalizador["Conta"],
                "Descrição": totalizador["Descrição da Conta"],
                "Valor": float(totalizador["Valor Saldo"]),
                "Regra": "Totalizadora",
                "Decisão": "Mantida"
            })
            out_rows.append(pd.DataFrame([totalizador]))
        else:
            logs.append({
                "Conta": totalizador["Conta"],
                "Descrição": totalizador["Descrição da Conta"],
                "Valor": float(totalizador["Valor Saldo"]),
                "Regra": "Totalizadora",
                "Decisão": "Removida"
            })
            out_rows.append(filhos)

    df_out = pd.concat(out_rows, ignore_index=True) if out_rows else work.iloc[0:0].copy()
    df_out = df_out.drop(columns=["Grupo"], errors="ignore")
    return df_out, pd.DataFrame(logs)

# =========================================================
# PARTE 1 – COTISTAS & PATRIMÔNIO (MULTI-UPLOAD)
# =========================================================
st.header("1. Cotistas e Patrimônio Líquido")

uploaded_files1 = st.file_uploader(
    "Envie uma ou mais planilhas de Cotistas e Patrimônio Líquido (.xlsx)",
    type=["xlsx"],
    key="planilha1_multi",
    accept_multiple_files=True
)

resumo_cotistas = []

if uploaded_files1:
    for idx, file in enumerate(uploaded_files1):

        df1 = pd.read_excel(file)
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

        resumo_cotistas.append({
            "Arquivo": file.name,
            "Cotistas Finais": cotistas_finais,
            "Patrimônio Final": patrimonio_final,
            "Captação Líquida": captacoes_liquidas,
            "Variação PL": variacao_patrimonio
        })

    df_resumo_cotistas = pd.DataFrame(resumo_cotistas)

    df_display = df_resumo_cotistas.copy()
    df_display["Patrimônio Final"] = df_display["Patrimônio Final"].apply(formatar_moeda)
    df_display["Captação Líquida"] = df_display["Captação Líquida"].apply(formatar_moeda)
    df_display["Variação PL"] = df_display["Variação PL"].apply(formatar_moeda)

    st.dataframe(df_display, use_container_width=True)
    st.divider()

# =========================================================
# PARTE 2 – BALANCETE (MULTI-UPLOAD)
# =========================================================
st.header("2. Exposição Econômica da Carteira")

uploaded_files2 = st.file_uploader(
    "Envie uma ou mais planilhas de Balancete (.xlsx)",
    type=["xlsx"],
    key="planilha2_multi",
    accept_multiple_files=True
)

def processar_balancete(df2: pd.DataFrame):
    df2 = df2.copy()
    df2["Conta"] = df2["Conta"].astype(str).str.strip()
    df2["Descrição da Conta"] = df2["Descrição da Conta"].astype(str).str.upper()
    df2["Valor Saldo"] = df2["Valor Saldo"].apply(converter_valor_brasileiro)

    total_row = df2[df2["Conta"] == "13000004"]
    if total_row.empty:
        return None, None, None, None, None, "Conta 13000004 não encontrada."

    total_tvm = float(total_row["Valor Saldo"].iloc[0])

    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    df_tvm = aplicar_exclusoes_prefixo(df_tvm)

    df_sem_dupla, df_log_regras = colapsar_totalizadoras_hibrido(df_tvm, tol_abs=TOL_ABS)

    df_sem_dupla["Categoria"] = df_sem_dupla["Descrição da Conta"].apply(classificar)

    df_filtrado, df_log_exc = aplicar_exclusoes_por_categoria(df_sem_dupla)

    df_log = pd.concat(
        [df_log_regras, df_log_exc],
        ignore_index=True
    ) if (
        (df_log_regras is not None and not df_log_regras.empty) or
        (df_log_exc is not None and not df_log_exc.empty)
    ) else pd.DataFrame()

    df_class = df_filtrado[df_filtrado["Categoria"].notna()].copy()
    df_nao_class = df_filtrado[df_filtrado["Categoria"].isna()].copy()

    consolidado = (
        df_class.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )

    consolidado["Percentual"] = (consolidado["Valor Saldo"] / total_tvm) * 100 if total_tvm else 0.0

    return total_tvm, df_class, df_nao_class, consolidado, df_log, None

if uploaded_files2:
    for idx, f in enumerate(uploaded_files2):
        df2 = pd.read_excel(f)
        total_tvm, df_class, df_nao_class, consolidado, df_log, err = processar_balancete(df2)

        if err:
            st.error(f"[{f.name}] {err}")
            continue

        # ✅ expander sem key, mas com label único
        with st.expander(f"Balancete #{idx+1} — {f.name}", expanded=(len(uploaded_files2) == 1)):
            st.subheader("Resumo Executivo")

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_relatorio = f"Relatorio_{f.name.replace('.xlsx','')}{idx+1}{ts}.xlsx"
            relatorio_bytes = excel_bytes_relatorio(
                arquivo_nome=f"{f.name} (#{idx+1})",
                total_tvm=total_tvm,
                consolidado=consolidado,
                df_consideradas=df_class,
                df_nao_classificadas=df_nao_class,
                df_log=df_log
            )

            # ✅ download_button COM key único
            st.download_button(
                "Exportar relatório (Excel)",
                data=relatorio_bytes,
                file_name=nome_relatorio,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{idx}{f.name}{ts}"
            )

            st.divider()

            cols = st.columns(max(1, len(consolidado)))
            for i in range(len(consolidado)):
                categoria = str(consolidado.iloc[i]["Categoria"])
                valor_categoria = float(consolidado.iloc[i]["Valor Saldo"])

                with cols[i]:
                    st.metric(categoria, formatar_moeda(valor_categoria))

                    # ✅ expander interno sem key, mas com label único
                    with st.expander(f"Ver composição — {categoria} — arquivo #{idx+1}"):
                        df_cat = df_class[df_class["Categoria"] == categoria].copy()
                        soma_check = float(df_cat["Valor Saldo"].sum())
                        st.write("Soma das contas consideradas:", formatar_moeda(soma_check))

                        df_show = df_cat.sort_values("Valor Saldo", ascending=False).copy()
                        df_show["Valor Saldo"] = df_show["Valor Saldo"].apply(formatar_moeda)
                        st.dataframe(df_show[["Conta", "Descrição da Conta", "Valor Saldo"]], use_container_width=True)

            st.divider()
            col_total, col_pizza = st.columns([1, 1])

            with col_total:
                st.metric("Total TVM", formatar_moeda(total_tvm))

            with col_pizza:
                fig1, ax1 = plt.subplots(figsize=(1.6, 1.6))
                ax1.pie(
                    consolidado["Percentual"],
                    labels=consolidado["Categoria"],
                    autopct="%1.1f%%",
                    textprops={"fontsize": 6}
                )
                st.pyplot(fig1)

            st.divider()

            if df_log is not None and not df_log.empty:
                with st.expander(f"Log de regras aplicadas — arquivo #{idx+1}"):
                    df_log_show = df_log.copy()
                    if "Valor" in df_log_show.columns:
                        df_log_show["Valor"] = df_log_show["Valor"].apply(formatar_moeda)
                    st.dataframe(df_log_show, use_container_width=True)

            if not df_nao_class.empty:
                st.warning("Contas não classificadas")
                df_nc = df_nao_class.sort_values("Valor Saldo", ascending=False).copy()
                df_nc["Valor Saldo"] = df_nc["Valor Saldo"].apply(formatar_moeda)
                st.dataframe(df_nc[["Conta", "Descrição da Conta", "Valor Saldo"]], use_container_width=True)

            st.subheader("Contas consideradas na análise")
            df_final = df_class.copy()
            df_final["Valor Saldo"] = df_final["Valor Saldo"].apply(formatar_moeda)
            st.dataframe(df_final[["Conta", "Descrição da Conta", "Categoria", "Valor Saldo"]], use_container_width=True)

else:
    st.info("Envie uma ou mais planilhas de balancete para iniciar a análise.")

# =========================================================
# EXPORTAÇÃO GLOBAL CONSOLIDADA
# =========================================================

if uploaded_files1 or uploaded_files2:

    st.header("📥 Exportação Consolidada Geral")

    def gerar_excel_consolidado():

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:

            if uploaded_files1 and resumo_cotistas:
                df_cot = pd.DataFrame(resumo_cotistas)
                df_cot.to_excel(writer, sheet_name="Resumo_Cotistas", index=False)

            if uploaded_files2 and resumo_consolidado:
                df_bal = pd.DataFrame(resumo_consolidado)
                df_bal.to_excel(writer, sheet_name="Resumo_Balancetes", index=False)

        return output.getvalue()

    st.download_button(
        "Exportar Relatório Consolidado Completo",
        data=gerar_excel_consolidado(),
        file_name="Relatorio_Consolidado_Geral.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_consolidado_geral"
    )
