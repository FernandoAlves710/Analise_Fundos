# =========================================================
# IMPORTS (PRIMEIRO BLOCO)
# =========================================================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
from io import BytesIO
from datetime import datetime

# =========================================================
# CONFIGURAÇÃO (PRIMEIRA CHAMADA STREAMLIT)
# =========================================================
st.set_page_config(
    page_title="Análise de Fundos",
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
            return None, "Arquivo inválido (esperado dicionário)."
        for k in ["Derivativos", "Títulos Públicos", "Títulos Privados"]:
            data.setdefault(k, [])
            if not isinstance(data[k], list):
                return None, f"Arquivo inválido: '{k}' deve ser uma lista."
        return data, None
    except Exception as e:
        return None, f"Erro ao ler arquivo: {e}"

def exportar_json_termos(termos_extras: dict) -> bytes:
    return json.dumps(termos_extras, ensure_ascii=False, indent=2).encode("utf-8")

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
    """
    Gera um .xlsx com abas:
      - Resumo
      - Contas_Consideradas
      - Nao_Classificadas
      - Log_Regras
    """
    output = BytesIO()

    # Aba Resumo
    resumo = consolidado.copy()
    if not resumo.empty:
        resumo["Valor (R$)"] = resumo["Valor Saldo"].apply(formatar_moeda)
        resumo["Percentual"] = resumo["Percentual"].apply(lambda x: f"{float(x):.2f}%")
        resumo = resumo[["Categoria", "Valor (R$)", "Percentual"]]

    resumo_total = pd.DataFrame(
        [{"Arquivo": arquivo_nome, "Total TVM": formatar_moeda(total_tvm)}]
    )

    # Formata contas consideradas
    cons = df_consideradas.copy()
    if not cons.empty:
        cons = cons[["Conta", "Descrição da Conta", "Categoria", "Valor Saldo"]].copy()
        cons["Valor Saldo"] = cons["Valor Saldo"].apply(formatar_moeda)

    # Formata não classificadas
    nc = df_nao_classificadas.copy()
    if not nc.empty:
        nc = nc[["Conta", "Descrição da Conta", "Valor Saldo"]].copy()
        nc["Valor Saldo"] = nc["Valor Saldo"].apply(formatar_moeda)

    # Formata log
    lg = df_log.copy()
    if lg is not None and not lg.empty:
        lg = lg.copy()
        if "Valor" in lg.columns:
            lg["Valor"] = lg["Valor"].apply(formatar_moeda)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumo_total.to_excel(writer, index=False, sheet_name="Resumo", startrow=0)
        if resumo is not None and not resumo.empty:
            resumo.to_excel(writer, index=False, sheet_name="Resumo", startrow=3)

        cons.to_excel(writer, index=False, sheet_name="Contas_Consideradas")
        nc.to_excel(writer, index=False, sheet_name="Nao_Classificadas")
        if lg is not None and not lg.empty:
            lg.to_excel(writer, index=False, sheet_name="Log_Regras")
        else:
            pd.DataFrame([{"Info": "Sem regras registradas no log."}]).to_excel(
                writer, index=False, sheet_name="Log_Regras"
            )

    return output.getvalue()

# =========================================================
# CONFIGURAÇÃO PADRÃO DO BANCO (ARQUIVO OFICIAL)
# =========================================================

CONFIG_PADRAO_BANCO = {
    "Derivativos": [
        "FUTURO", "OPÇÃO", "SWAP", "DERIVAT"
    ],
    "Títulos Públicos": [
        "TESOURO", "LFT", "LTN", "NTN"
    ],
    "Títulos Privados": [
        "DEBÊNTURE", "DEBENTURE", "CDB", "CRI", "CRA",
        "FUNDO", "AÇÃO", "ACAO", "BDR",
        "LCI", "LCA",
        "RENDA VARIAVEL", "RENDA VARIÁVEL",
        "CERTIFICADOS DE DEPÓSITO BANCÁRIO",
        "CERTIFICADOS DE DEPOSITO BANCARIO",
        "DEPÓSITO BANCÁRIO",
        "DEPOSITO BANCARIO"
    ]
}

# =========================================================
# SIDEBAR – CONFIGURAÇÕES
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

st.sidebar.download_button(
    "Baixar configuração padrão do banco",
    data=exportar_json_termos(CONFIG_PADRAO_BANCO),
    file_name="config_padrao_banco.json",
    mime="application/json"
)

cfg_upload = st.sidebar.file_uploader("Importar configuração do time", type=["json"])
if cfg_upload is not None:
    data, err = carregar_json_termos(cfg_upload)
    if err:
        st.sidebar.error(err)
    else:
        st.session_state.termos_extras = data
        st.sidebar.success("Configuração importada.")

txt_der = st.sidebar.text_area(
    "Derivativos – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Derivativos"]),
    height=100
)
txt_pub = st.sidebar.text_area(
    "Títulos Públicos – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Públicos"]),
    height=100
)
txt_priv = st.sidebar.text_area(
    "Títulos Privados – termos extras (1 por linha)",
    value=list_to_text(st.session_state.termos_extras["Títulos Privados"]),
    height=120
)

if st.sidebar.button("Aplicar termos"):
    st.session_state.termos_extras["Derivativos"] = text_to_list(txt_der)
    st.session_state.termos_extras["Títulos Públicos"] = text_to_list(txt_pub)
    st.session_state.termos_extras["Títulos Privados"] = text_to_list(txt_priv)
    st.sidebar.success("Termos aplicados.")

st.sidebar.download_button(
    "Exportar configuração do time",
    data=exportar_json_termos(st.session_state.termos_extras),
    file_name="config_time.json",
    mime="application/json"
)

st.sidebar.divider()

st.sidebar.subheader("Modo avançado (só se necessário)")
st.sidebar.caption("Exclui blocos de contas por prefixo (1 por linha). Ex.: 1361")

exclusoes_texto = st.sidebar.text_area(
    "Prefixos para excluir",
    value="",
    height=90
)
PREFIXOS_EXCLUIR = [p.strip() for p in exclusoes_texto.split("\n") if p.strip()]

TOL_ABS = st.sidebar.number_input(
    "Tolerância p/ identificar totalizadoras (R$)",
    min_value=0.0,
    value=1.0,
    step=0.5
)

# =========================================================
# REGRAS BASE + AMBIGUIDADE
# =========================================================

BASE_DERIVATIVOS = ["FUTURO", "OPÇÃO", "SWAP", "DERIVAT"]
BASE_PUBLICOS = ["TESOURO", "LFT", "LTN", "NTN"]

BASE_PRIVADOS = [
    "DEBÊNTURE", "DEBENTURE", "CDB", "CRI", "CRA",
    "FUNDO", "AÇÃO", "ACAO", "BDR",
    "LCI", "LCA",
    "RENDA VARIAVEL", "RENDA VARIÁVEL",
    "CERTIFICADOS DE DEPÓSITO BANCÁRIO",
    "CERTIFICADOS DE DEPOSITO BANCARIO",
    "DEPÓSITO BANCÁRIO",
    "DEPOSITO BANCARIO"
]

AMBIGUOS = [
    "GARANTIA", "DADOS EM GARANTIA", "EM GARANTIA",
    "MARGEM", "BOLSA", "OPERAÇÕES EM BOLSA", "OPERACOES EM BOLSA",
    "VINCUL", "BLOQUEAD", "CUSTOD", "DEPOSITO EM GARANTIA",
    "COLATERAL"
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

def eh_ambigua(descricao: str) -> bool:
    desc = (descricao or "").upper()
    return any(p in desc for p in AMBIGUOS)

def aplicar_exclusoes(df: pd.DataFrame) -> pd.DataFrame:
    if not PREFIXOS_EXCLUIR:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    for pref in PREFIXOS_EXCLUIR:
        mask &= ~df["Conta"].astype(str).str.startswith(pref)
    return df[mask].copy()

# =========================================================
# COLAPSO HÍBRIDO DE TOTALIZADORAS (ambíguas sempre removidas)
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

    for grupo, g in work.groupby("Grupo", dropna=False):

        # Ambíguas sempre removidas
        amb_mask = g["Descrição da Conta"].apply(eh_ambigua)
        if amb_mask.any():
            g_amb = g[amb_mask].copy()
            g_rest = g[~amb_mask].copy()

            for _, row in g_amb.iterrows():
                logs.append({
                    "Grupo": grupo,
                    "Conta": row["Conta"],
                    "Descrição": row["Descrição da Conta"],
                    "Valor": float(row["Valor Saldo"]),
                    "Regra": "Ambígua",
                    "Decisão": "Removida"
                })

            g = g_rest
            if g.empty:
                continue

        if len(g) == 1:
            out_rows.append(g)
            continue

        total_grupo = float(g["Valor Saldo"].sum())

        # identifica totalizador por soma
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
        desc_total = str(totalizador["Descrição da Conta"])
        cat_total = classificar(desc_total)

        filhos = g.drop(index=totalizador_idx)

        if cat_total is not None:
            logs.append({
                "Grupo": grupo,
                "Conta": totalizador["Conta"],
                "Descrição": totalizador["Descrição da Conta"],
                "Valor": float(totalizador["Valor Saldo"]),
                "Regra": "Totalizadora",
                "Decisão": "Mantida"
            })
            out_rows.append(pd.DataFrame([totalizador]))
        else:
            logs.append({
                "Grupo": grupo,
                "Conta": totalizador["Conta"],
                "Descrição": totalizador["Descrição da Conta"],
                "Valor": float(totalizador["Valor Saldo"]),
                "Regra": "Totalizadora",
                "Decisão": "Removida"
            })
            out_rows.append(filhos)

    df_out = pd.concat(out_rows, ignore_index=True) if out_rows else work.iloc[0:0].copy()
    df_out = df_out.drop(columns=["Grupo"], errors="ignore")

    df_log = pd.DataFrame(logs)
    return df_out, df_log

# =========================================================
# PARTE 1 – COTISTAS & PATRIMÔNIO (cards sem truncar números)
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

    def card(titulo, valor):
        st.markdown(
            f"""
            <div style="padding:10px 0px;">
                <div style="font-size:14px; color:gray;">{titulo}</div>
                <div style="font-size:22px; font-weight:600;">
                    {valor}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        card("Cotistas (Final)", f"{cotistas_finais:,}".replace(",", "."))

    with col2:
        card("Patrimônio Final", formatar_moeda(patrimonio_final))

    with col3:
        card("Captação Líquida", formatar_moeda(captacoes_liquidas))

    with col4:
        card("Variação do PL", formatar_moeda(variacao_patrimonio))

    st.divider()

# =========================================================
# PARTE 2 – EXPOSIÇÃO ECONÔMICA + MULTI-UPLOAD + AJUDA RÁPIDA
# =========================================================

st.header("2. Exposição Econômica da Carteira")

st.info(
    "Ajuda rápida:\n"
    "- Se aparecer **“Contas não classificadas”**, adicione palavras-chave na barra lateral em **Configuração do time**.\n"
    "- Use **Modo avançado** apenas se precisar excluir um bloco inteiro por prefixo.\n"
    "- O relatório pode ser exportado em Excel (Resumo, Contas consideradas, Não classificadas e Log)."
)

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
        return None, None, None, None, None, "Conta 13000004 não encontrada."

    total_tvm = float(total_row["Valor Saldo"].iloc[0])

    df_tvm = df2[
        (df2["Conta"].str.startswith("13")) &
        (df2["Conta"] != "13000004") &
        (df2["Valor Saldo"] != 0)
    ].copy()

    df_tvm = aplicar_exclusoes(df_tvm)

    df_sem_dupla, df_log = colapsar_totalizadoras_hibrido(df_tvm, tol_abs=TOL_ABS)

    df_sem_dupla["Categoria"] = df_sem_dupla["Descrição da Conta"].apply(classificar)

    df_class = df_sem_dupla[df_sem_dupla["Categoria"].notna()].copy()
    df_nao_class = df_sem_dupla[df_sem_dupla["Categoria"].isna()].copy()

    consolidado = (
        df_class.groupby("Categoria")["Valor Saldo"]
        .sum()
        .reset_index()
        .sort_values("Valor Saldo", ascending=False)
    )
    consolidado["Percentual"] = (consolidado["Valor Saldo"] / total_tvm) * 100

    return total_tvm, df_class, df_nao_class, consolidado, df_log, None

if uploaded_files2:
    resumo_consolidado = []

    for f in uploaded_files2:
        df2 = pd.read_excel(f)
        total_tvm, df_class, df_nao_class, consolidado, df_log, err = processar_balancete(df2)

        if err:
            st.error(f"[{f.name}] {err}")
            continue

        with st.expander(f"Balancete: {f.name}", expanded=(len(uploaded_files2) == 1)):
            st.subheader("Resumo Executivo")

            # Botão de export (relatório Excel do arquivo)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_relatorio = f"Relatorio_{f.name.replace('.xlsx','')}_{ts}.xlsx"
            relatorio_bytes = excel_bytes_relatorio(
                arquivo_nome=f.name,
                total_tvm=total_tvm,
                consolidado=consolidado,
                df_consideradas=df_class,
                df_nao_classificadas=df_nao_class,
                df_log=df_log if df_log is not None else pd.DataFrame()
            )

            st.download_button(
                "Exportar relatório (Excel)",
                data=relatorio_bytes,
                file_name=nome_relatorio,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.divider()

            # Métricas
            cols = st.columns(max(1, len(consolidado)))
            for i in range(len(consolidado)):
                categoria = consolidado.iloc[i]["Categoria"]
                valor_categoria = float(consolidado.iloc[i]["Valor Saldo"])

                with cols[i]:
                    st.metric(categoria, formatar_moeda(valor_categoria))
                    with st.expander("Ver composição"):
                        df_cat = df_class[df_class["Categoria"] == categoria].copy()
                        soma_check = float(df_cat["Valor Saldo"].sum())
                        st.write("Soma das contas consideradas:", formatar_moeda(soma_check))

                        df_show = df_cat.sort_values("Valor Saldo", ascending=False).copy()
                        df_show["Valor Saldo"] = df_show["Valor Saldo"].apply(formatar_moeda)
                        st.dataframe(df_show[["Conta", "Descrição da Conta", "Valor Saldo"]], use_container_width=True)

            # Total + Pizza ao lado (pizza bem pequena)
            st.divider()
            col_total, col_pizza = st.columns([1, 1])

            with col_total:
                st.metric("Total TVM", formatar_moeda(total_tvm))

            with col_pizza:
                fig1, ax1 = plt.subplots(figsize=(1.6, 1.6))
                ax1.pie(
                    consolidado["Percentual"],
                    labels=consolidado["Categoria"],
                    autopct='%1.1f%%',
                    textprops={'fontsize': 6}
                )
                st.pyplot(fig1)

            st.divider()

            if df_log is not None and not df_log.empty:
                with st.expander("Log de regras aplicadas"):
                    df_log_show = df_log.copy()
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
            st.dataframe(df_final, use_container_width=True)

        row = {"Arquivo": f.name, "Total TVM": total_tvm}
        for _, r in consolidado.iterrows():
            row[r["Categoria"]] = float(r["Valor Saldo"])
            row[f"% {r['Categoria']}"] = float(r["Percentual"])
        resumo_consolidado.append(row)

    if resumo_consolidado:
        st.divider()
        st.header("Resumo Consolidado")

        df_resumo = pd.DataFrame(resumo_consolidado).fillna(0)

        for c in ["Total TVM", "Títulos Públicos", "Títulos Privados", "Derivativos"]:
            if c in df_resumo.columns:
                df_resumo[c] = df_resumo[c].apply(formatar_moeda)

        for c in [c for c in df_resumo.columns if c.startswith("% ")]:
            df_resumo[c] = df_resumo[c].apply(lambda x: f"{float(x):.2f}%")

        st.dataframe(df_resumo, use_container_width=True)

else:
    st.info("Envie uma ou mais planilhas de balancete para iniciar a análise.")
