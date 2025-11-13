# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

st.set_page_config(page_title="Analisador de Fundos", layout="wide")
st.title("📊 Analisador de Fundos de Investimento")

# ---------------------------
# Funções utilitárias
# ---------------------------
def parse_brazilian_int(x):
    """
    Converte valores em formato brasileiro para inteiro desconsiderando centavos.
    Exemplos:
      "8.450.785.258,06" -> 8450785258
      "R$ 1.234,56" -> 1234
      1234.56 (float) -> 1234
      "1234" -> 1234
    Retorna np.nan se não conseguir parsear.
    """
    if pd.isna(x):
        return np.nan
    # se já é número (int/float), mantemos a parte inteira
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        try:
            return int(np.trunc(x))
        except:
            return np.nan
    s = str(x).strip()
    # remove currency symbols e parênteses
    s = s.replace('R$', '').replace('$', '').replace('€', '')
    s = s.replace('(', '').replace(')', '').strip()
    # se contém vírgula (formato BR), pegar parte antes da vírgula
    if ',' in s:
        left = s.split(',')[0]
        # remover tudo que nao dígito ou sinal
        cleaned = re.sub(r'[^\d\-]', '', left)
        return int(cleaned) if cleaned != '' else np.nan
    # se não contém vírgula, pode ter pontos como milhares (ou ser formato en)
    # remove pontos e outros não dígitos, ou se for "1234.56" (ponto decimal), pega parte antes do ponto
    if '.' in s:
        # se houver mais de 1 ponto e vírgula ausente, assumir que pontos são separadores de milhar
        if s.count('.') > 1:
            cleaned = re.sub(r'[^\d\-]', '', s)
            return int(cleaned) if cleaned != '' else np.nan
        else:
            # caso comum "1234.56" -> pegar parte antes do ponto
            left = s.split('.')[0]
            cleaned = re.sub(r'[^\d\-]', '', left)
            return int(cleaned) if cleaned != '' else np.nan
    # caso só números e possivelmente espaços
    cleaned = re.sub(r'[^\d\-]', '', s)
    return int(cleaned) if cleaned != '' else np.nan

# ---------------------------
# UI - Upload
# ---------------------------
st.subheader("1️⃣ Upload das Planilhas (um fundo por vez)")
cotistas_file = st.file_uploader("Envie a planilha de Cotistas e Patrimônio Líquido (Excel)", type=["xlsx", "xls"])
balancete_file = st.file_uploader("Envie a planilha de Balancete (Excel)", type=["xlsx", "xls"])

if cotistas_file and balancete_file:
    # === Planilha 1: Cotistas e PL ===
    df_cotistas = pd.read_excel(cotistas_file)
    df_cotistas.columns = [col.strip() for col in df_cotistas.columns]

    # Normalizar nomes (caso sensível) - assumir colunas conforme descrito
    # Converter colunas monetárias e cotistas para inteiros (desconsiderando centavos)
    for col in df_cotistas.columns:
        if col.strip().lower() in ['patrimônio', 'patrimonio', 'patrimônio líquido', 'patrimonio liquido', 'patrimonio_liquido', 'patrimonio líquido']:
            df_cotistas[col] = df_cotistas[col].apply(parse_brazilian_int)
        if col.strip().lower() in ['captação', 'captacao', 'captações', 'captacoes', 'captação líquida', 'captação_liquida']:
            df_cotistas[col] = df_cotistas[col].apply(parse_brazilian_int)
        if col.strip().lower() in ['resgate', 'resgates']:
            df_cotistas[col] = df_cotistas[col].apply(parse_brazilian_int)
        if col.strip().lower() in ['cotistas', 'n_cotistas', 'qtde cotistas']:
            # garantir inteiro
            df_cotistas[col] = pd.to_numeric(df_cotistas[col], errors='coerce').apply(lambda v: int(v) if not pd.isna(v) else np.nan)

    # Identificar colunas com heurística
    def find_col(df_cols, possibles):
        for c in df_cols:
            if c.strip().lower() in possibles:
                return c
        return None

    cols_lower = [c.strip().lower() for c in df_cotistas.columns]
    col_cotistas = find_col(df_cotistas.columns, ['cotistas', 'n_cotistas', 'qtde cotistas'])
    col_patrimonio = find_col(df_cotistas.columns, ['patrimônio', 'patrimonio', 'patrimonio líquido', 'patrimonio liquido', 'pl'])
    col_captacao = find_col(df_cotistas.columns, ['captação', 'captacao', 'captações', 'captacoes'])
    col_resgate = find_col(df_cotistas.columns, ['resgate', 'resgates'])

    # Segurança: se não encontrar pelo nome exato, tentar match parcial
    if col_patrimonio is None:
        for c in df_cotistas.columns:
            if 'patr' in c.strip().lower():
                col_patrimonio = c; break
    if col_cotistas is None:
        for c in df_cotistas.columns:
            if 'cotist' in c.strip().lower():
                col_cotistas = c; break

    # ordenar por data se existir coluna data
    date_col = None
    for c in df_cotistas.columns:
        if 'data' == c.strip().lower() or 'data' in c.strip().lower():
            date_col = c; break
    if date_col:
        df_cotistas[date_col] = pd.to_datetime(df_cotistas[date_col], dayfirst=True, errors='coerce')
        df_cotistas = df_cotistas.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)

    # Agora extrair métricas (tratando possíveis NaNs)
    try:
        cotistas_final = int(df_cotistas[col_cotistas].dropna().iloc[-1]) if col_cotistas and not df_cotistas[col_cotistas].dropna().empty else np.nan
    except:
        cotistas_final = np.nan

    try:
        pl_final = int(df_cotistas[col_patrimonio].dropna().iloc[-1]) if col_patrimonio and not df_cotistas[col_patrimonio].dropna().empty else np.nan
    except:
        pl_final = np.nan

    try:
        pl_inicial = int(df_cotistas[col_patrimonio].dropna().iloc[0]) if col_patrimonio and not df_cotistas[col_patrimonio].dropna().empty else np.nan
    except:
        pl_inicial = np.nan

    # captações líquidas
    sum_capt = int(df_cotistas[col_captacao].dropna().apply(lambda v: int(v)).sum()) if col_captacao and not df_cotistas[col_captacao].dropna().empty else 0
    sum_resg = int(df_cotistas[col_resgate].dropna().apply(lambda v: int(v)).sum()) if col_resgate and not df_cotistas[col_resgate].dropna().empty else 0
    capt_liq = sum_capt - sum_resg
    variacao_pl = (pl_final - pl_inicial) if (not pd.isna(pl_final) and not pd.isna(pl_inicial)) else np.nan

    # === Planilha 2: Balancete ===
    df_balancete = pd.read_excel(balancete_file)
    df_balancete.columns = [col.strip() for col in df_balancete.columns]

    # Confirmar colunas esperadas
    if "Descrição da Conta" not in df_balancete.columns or "Valor Saldo" not in df_balancete.columns:
        st.error("Planilha Balancete deve conter as colunas exatas: 'Descrição da Conta' e 'Valor Saldo'.")
    else:
        # Converter Valor Saldo para inteiros (desconsiderando centavos)
        df_balancete["Valor Saldo Int"] = df_balancete["Valor Saldo"].apply(parse_brazilian_int)

        # Total de ativos: linha que contenha 'realiz' (realizável)
        total_ativos = df_balancete.loc[
            df_balancete["Descrição da Conta"].str.contains("realiz", case=False, na=False),
            "Valor Saldo Int"
        ].sum()

        # Listas de busca (busca case-insensitive parcial)
        operacoes_keywords = [
            "aplicações em operações compromissadas",
            "letras do tesouro nacional",
            "notas do tesouro nacional",
            "letras financeiras do tesouro"
        ]
        publicos_keywords = [
            "títulos públicos federais", "tesouro nacional",
            "letras financeiras do tesouro",
            "letras do tesouro nacional",
            "notas do tesouro nacional"
        ]
        privados_keywords = [
            "letras financeiras", "debêntures", "debentures",
            "letras financeiras subordinadas", "cotas de fundos", "cotas de fundo",
            "certificados de depósito bancário", "certificados de deposito bancario",
            "certificados de recebíveis imobiliários", "certificados de recebiveis imobiliarios",
            "títulos de renda variável", "ações", "cotas de fundo imobiliário",
            "aplicações em títulos e valores mobiliários no exterior",
            "outros títulos privados", "bdr", "cdr", "cotAS de fundo de investimento índice de mercado"
        ]

        def sum_by_keywords(df, keywords):
            mask = pd.Series(False, index=df.index)
            desc = df["Descrição da Conta"].astype(str).str.lower()
            for kw in keywords:
                kw_low = kw.lower()
                mask = mask | desc.str.contains(re.escape(kw_low), na=False)
            return int(df.loc[mask, "Valor Saldo Int"].sum())

        soma_operacoes = sum_by_keywords(df_balancete, operacoes_keywords)
        soma_publicos = sum_by_keywords(df_balancete, publicos_keywords)
        soma_privados = sum_by_keywords(df_balancete, privados_keywords)

        # === Exibição ===
        st.subheader("📈 Resultados - Cotistas e Patrimônio Líquido")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cotistas (final)", f"{int(cotistas_final):,}".replace(",", ".") if not pd.isna(cotistas_final) else "—")
        c2.metric("PL Final (R$)", f"{int(pl_final):,}".replace(",", ".") if not pd.isna(pl_final) else "—")
        c3.metric("Captação Líquida (R$)", f"{int(capt_liq):,}".replace(",", "."))
        c4.metric("Variação do PL (R$)", f"{int(variacao_pl):,}".replace(",", ".") if not pd.isna(variacao_pl) else "—")

        st.divider()
        st.subheader("🏦 Resultados - Balancete")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Ativos Totais (R$)", f"{int(total_ativos):,}".replace(",", "."))
        d2.metric("Operações Compromissadas (R$)", f"{int(soma_operacoes):,}".replace(",", "."))
        d3.metric("Títulos Públicos (R$)", f"{int(soma_publicos):,}".replace(",", "."))
        d4.metric("Títulos Privados (R$)", f"{int(soma_privados):,}".replace(",", "."))

        # Gráfico de pizza menor (figsize reduzido)
        # Gráfico de pizza ajustado
st.divider()
st.subheader("📊 Composição da Carteira (apenas categorias)")

labels = ["Operações Compromissadas", "Títulos Públicos", "Títulos Privados"]
values = [soma_operacoes, soma_publicos, soma_privados]

if sum(values) == 0:
    st.info("Sem valores para composição (todas as categorias com valor zero).")
else:
    fig, ax = plt.subplots(figsize=(3, 3))  # tamanho pequeno
    wedges, texts, autotexts = ax.pie(
        values,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 8},  # reduz o tamanho dos textos
    )

    # adiciona legenda lateral compacta
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

        st.success("✅ Análise concluída com sucesso!")
