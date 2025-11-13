# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import unicodedata
import re

st.set_page_config(page_title="Análise de Fundos", layout="centered")
st.title("📊 Ferramenta de Análise de Fundos – Bradesco (Cotistas & Balancete)")
st.markdown("---")

# -----------------------
# Utilitários
# -----------------------
def normalizar_texto(s):
    """Remove acentos e deixa em minúsculas para comparação robusta."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    return s

def converter_valor_brasileiro_para_int(valor):
    """
    Converte valores no formato brasileiro em inteiro, descartando centavos.
    Ex: "8.450.785.258,06" -> 8450785258
    """
    if pd.isna(valor):
        return 0
    # se já é número
    if isinstance(valor, (int, np.integer)):
        return int(valor)
    if isinstance(valor, (float, np.floating)):
        return int(np.trunc(valor))
    s = str(valor).strip()
    # remove símbolos de moeda e parênteses
    s = s.replace("R$", "").replace("$", "").replace("(", "").replace(")", "").strip()
    # se tem vírgula (BR) pega parte antes da vírgula
    if "," in s:
        left = s.split(",")[0]
        cleaned = re.sub(r"[^\d\-]", "", left)
        return int(cleaned) if cleaned != "" else 0
    # se tem ponto(s)
    if "." in s:
        # se múltiplos pontos, remover pontos (milhares)
        if s.count(".") > 1:
            cleaned = re.sub(r"[^\d\-]", "", s)
            return int(cleaned) if cleaned != "" else 0
        else:
            # caso "1234.56" -> pegar parte antes do ponto
            left = s.split(".")[0]
            cleaned = re.sub(r"[^\d\-]", "", left)
            return int(cleaned) if cleaned != "" else 0
    cleaned = re.sub(r"[^\d\-]", "", s)
    return int(cleaned) if cleaned != "" else 0

def achar_coluna_por_palavras(cols, palavras_possiveis):
    """Procura em cols (iterável de nomes) por correspondência parcial com palavras_possiveis (lista). Retorna primeiro match."""
    cols_norm = [normalizar_texto(c) for c in cols]
    for p in palavras_possiveis:
        p_norm = normalizar_texto(p)
        for i, c_norm in enumerate(cols_norm):
            if p_norm == c_norm or p_norm in c_norm or c_norm in p_norm:
                return cols[i]
    return None

# -----------------------
# Uploads
# -----------------------
st.header("1) Upload das planilhas (um fundo por vez)")
st.write("Envie primeiro a planilha de Cotistas & PL e depois a planilha de Balancete para o mesmo fundo.")

cotistas_file = st.file_uploader("Planilha 1 — Cotistas e Patrimônio Líquido (.xlsx)", type=["xlsx"], key="cotistas")
balancete_file = st.file_uploader("Planilha 2 — Balancete (.xlsx)", type=["xlsx"], key="balancete")

if cotistas_file:
    # Leitura robusta do Excel
    df1 = pd.read_excel(cotistas_file)
    # normalizar nomes das colunas (manter originais para exibição)
    cols1 = list(df1.columns)
    cols1_stripped = [c.strip() for c in cols1]

    # detectar colunas relevantes com heurística
    col_data = achar_coluna_por_palavras(cols1_stripped, ["data", "datas"])
    col_patrimonio = achar_coluna_por_palavras(cols1_stripped, ["patrimônio", "patrimonio", "pl"])
    col_captacao = achar_coluna_por_palavras(cols1_stripped, ["captação", "captacao", "captações", "captacoes"])
    col_resgate = achar_coluna_por_palavras(cols1_stripped, ["resgate", "resgates"])
    col_cotistas = achar_coluna_por_palavras(cols1_stripped, ["cotistas", "n_cotistas", "qtde cotistas"])

    if col_patrimonio is None:
        st.error("Não encontrei automaticamente a coluna de patrimônio. Verifique o nome da coluna na planilha (ex: 'Patrimônio').")
    else:
        # converter valores (inteiros sem centavos)
        df1[col_patrimonio] = df1[col_patrimonio].apply(converter_valor_brasileiro_para_int)
    if col_captacao:
        df1[col_captacao] = df1[col_captacao].apply(converter_valor_brasileiro_para_int)
    if col_resgate:
        df1[col_resgate] = df1[col_resgate].apply(converter_valor_brasileiro_para_int)
    if col_cotistas:
        # garantir int
        df1[col_cotistas] = pd.to_numeric(df1[col_cotistas], errors="coerce").fillna(0).astype(int)

    # ordenar por data (se houver coluna data) para definir início e fim do período corretamente
    if col_data:
        try:
            df1[col_data] = pd.to_datetime(df1[col_data], dayfirst=True, errors="coerce")
            df1 = df1.dropna(subset=[col_data]).sort_values(col_data).reset_index(drop=True)
        except:
            # se erro ao parsear, não ordena
            pass

    # extrair patrimônio inicial e final por posição (primeiro = inicial, último = final)
    # caso a planilha esteja em ordem decrescente, garantir que este código pegue min/max por data se disponível
    if col_patrimonio:
        if col_data:
            # pegar pela menor e maior data
            try:
                pl_inicial = int(df1.loc[df1[col_data] == df1[col_data].min(), col_patrimonio].dropna().iloc[0])
                pl_final = int(df1.loc[df1[col_data] == df1[col_data].max(), col_patrimonio].dropna().iloc[-1])
            except Exception:
                # fallback por posição
                pl_inicial = int(df1[col_patrimonio].dropna().iloc[0]) if not df1[col_patrimonio].dropna().empty else 0
                pl_final = int(df1[col_patrimonio].dropna().iloc[-1]) if not df1[col_patrimonio].dropna().empty else 0
        else:
            # sem coluna data, assumir primeira linha = data final (como antes) -> mas para evitar erro, pegar posicoes
            pl_final = int(df1[col_patrimonio].dropna().iloc[0]) if not df1[col_patrimonio].dropna().empty else 0
            pl_inicial = int(df1[col_patrimonio].dropna().iloc[-1]) if not df1[col_patrimonio].dropna().empty else 0
    else:
        pl_final = pl_inicial = 0

    # cotistas (pegar valor da data mais recente se tiver data; senão pegar primeira linha)
    if col_cotistas:
        if col_data:
            try:
                cotistas_final = int(df1.loc[df1[col_data] == df1[col_data].max(), col_cotistas].dropna().iloc[-1])
            except:
                cotistas_final = int(df1[col_cotistas].dropna().iloc[0]) if not df1[col_cotistas].dropna().empty else 0
        else:
            cotistas_final = int(df1[col_cotistas].dropna().iloc[0]) if not df1[col_cotistas].dropna().empty else 0
    else:
        cotistas_final = 0

    # captações líquidas
    sum_capt = int(df1[col_captacao].dropna().sum()) if col_captacao and not df1[col_captacao].dropna().empty else 0
    sum_resg = int(df1[col_resgate].dropna().sum()) if col_resgate and not df1[col_resgate].dropna().empty else 0
    captacoes_liquidas = sum_capt - sum_resg

    variacao_pl = int(pl_final) - int(pl_inicial)

    # Exibir resultados da planilha 1
    st.header("Resultados — Cotistas & Patrimônio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cotistas (data final)", f"{cotistas_final:,}".replace(",", "."))
    c2.metric("Patrimônio (final)", f"R$ {pl_final:,}".replace(",", "."))
    c3.metric("Captação líquida (período)", f"R$ {captacoes_liquidas:,}".replace(",", "."))
    # variaçãoPode ser negativa - mostrar com sinal
    sign = "-" if variacao_pl < 0 else ""
    c4.metric("Variação do PL (final - inicial)", f"{sign}R$ {abs(variacao_pl):,}".replace(",", "."))

st.markdown("---")

if balancete_file:
    df2 = pd.read_excel(balancete_file)
    df2.columns = [c.strip() for c in df2.columns]

    # verificar colunas obrigatórias
    if "Descrição da Conta" not in df2.columns and "Descrição da conta" not in df2.columns and "descricao da conta" not in [c.lower() for c in df2.columns]:
        st.error("A planilha Balancete precisa conter a coluna 'Descrição da Conta' (verifique maiúsculas/acentos).")
    elif "Valor Saldo" not in df2.columns and "valor saldo" not in [c.lower() for c in df2.columns]:
        st.error("A planilha Balancete precisa conter a coluna 'Valor Saldo' (verifique maiúsculas).")
    else:
        # garantir colunas com nomes padronizados
        # encontrar as colunas reais
        desc_col = None
        saldo_col = None
        for c in df2.columns:
            if normalizar_texto(c) == normalizar_texto("Descrição da Conta"):
                desc_col = c
            if normalizar_texto(c) == normalizar_texto("Valor Saldo"):
                saldo_col = c
        # fallback: procurar por palavras-chaves
        if desc_col is None:
            for c in df2.columns:
                if "descri" in normalizar_texto(c):
                    desc_col = c; break
        if saldo_col is None:
            for c in df2.columns:
                if "valor" in normalizar_texto(c) and "saldo" in normalizar_texto(c):
                    saldo_col = c; break

        # converter saldo para inteiro sem centavos
        df2["VALOR_INT"] = df2[saldo_col].apply(converter_valor_brasileiro_para_int)
        df2["DESC_NORM"] = df2[desc_col].apply(normalizar_texto)

        # total de ativos (linha que contenha 'realiz' ou 'realizavel')
        mask_realiz = df2["DESC_NORM"].str.contains("realiz", na=False)
        total_ativos = int(df2.loc[mask_realiz, "VALOR_INT"].sum())

        # operações compromissadas -> pegar apenas a linha "aplicações em operações compromissadas"
        termo_ops = normalizar_texto("aplicações em operações compromissadas")
        mask_ops = df2["DESC_NORM"].str.contains(normalizar_texto("aplicações em operações compromissadas"), na=False)
        valor_aplic_ops = int(df2.loc[mask_ops, "VALOR_INT"].sum())

        # listas de nomenclaturas para títulos públicos e privados (cada item será mostrado com seu valor)
        titulos_publicos_noms = [
            "títulos públicos federais - tesouro nacional",
            "letras financeiras do tesouro",
            "letras do tesouro nacional",
            "notas do tesouro nacional"
        ]
        titulos_privados_noms = [
            "letras financeiras",
            "debêntures",
            "letras financeiras subordinadas",
            "cotas de fundos de investimento",
            "cotas de fundo de renda fixa",
            "cotas de fundo em direitos creditórios",
            "certificados de depósito bancário",
            "certificados de recebíveis imobiliários",
            "cotas de fundo multimercado",
            "títulos de renda variável",
            "ações de companhias abertas",
            "cotas de fundo imobiliário",
            "aplicações em títulos e valores mobiliários no exterior",
            "outros títulos privados - renda fixa",
            "cotas de fundos de investimento",  # repetido intencionalmente se existe
            "bdr - certificado de depósito de ações",
            "cotas de fundo de investimento índice de mercado"
        ]

        # função que, dado uma lista de nomenclaturas, retorna dataframe com cada nomenclatura e seu valor (soma das linhas que contenham a nomenclatura)
        def listar_valores_por_nomenclatura(df, col_desc_norm, col_val_int, nomenclaturas):
            rows = []
            for nome in nomenclaturas:
                nome_norm = normalizar_texto(nome)
                # buscar linhas que contenham o termo (case-insensitive, sem acentos)
                mask = df[col_desc_norm].str.contains(re.escape(nome_norm), na=False)
                # se nenhum resultado com expressão exata, tentar busca por palavras-chave sem escapar (mais permissiva)
                if not mask.any():
                    mask = df[col_desc_norm].str.contains(nome_norm, na=False)
                valor = int(df.loc[mask, col_val_int].sum()) if mask.any() else 0
                rows.append({"nomenclatura": nome, "valor": valor})
            return pd.DataFrame(rows)

        df_publicos = listar_valores_por_nomenclatura(df2, "DESC_NORM", "VALOR_INT", titulos_publicos_noms)
        df_privados = listar_valores_por_nomenclatura(df2, "DESC_NORM", "VALOR_INT", titulos_privados_noms)

        # Exibição dos resultados resumidos
        st.header("Resultados — Balancete")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total de Ativos (Realizável)", f"R$ {total_ativos:,}".replace(",", "."))
        r2.metric("Aplicações em Ops Compromissadas", f"R$ {valor_aplic_ops:,}".replace(",", "."))
        # somas para compor gráfico (somar publicos + privados + operacoes)
        total_publicos = int(df_publicos["valor"].sum())
        total_privados = int(df_privados["valor"].sum())
        r3.metric("Total Títulos Públicos (soma itens)", f"R$ {total_publicos:,}".replace(",", "."))
        r4.metric("Total Títulos Privados (soma itens)", f"R$ {total_privados:,}".replace(",", "."))

        st.markdown("**Títulos Públicos — valores por nomenclatura**")
        # formatação para exibição (R$ e sem centavos)
        df_publicos_display = df_publicos.copy()
        df_publicos_display["valor_formatado"] = df_publicos_display["valor"].apply(lambda v: f"R$ {v:,}".replace(",", "."))
        st.table(df_publicos_display.rename(columns={"nomenclatura":"Nomenclatura", "valor_formatado":"Valor"}).set_index("Nomenclatura"))

        st.markdown("**Títulos Privados — valores por nomenclatura**")
        df_privados_display = df_privados.copy()
        df_privados_display["valor_formatado"] = df_privados_display["valor"].apply(lambda v: f"R$ {v:,}".replace(",", "."))
        st.table(df_privados_display.rename(columns={"nomenclatura":"Nomenclatura", "valor_formatado":"Valor"}).set_index("Nomenclatura"))

        # Gráfico de pizza (operacoes vs publicos vs privados) - pequeno e com legenda lateral
        st.markdown("**Composição (categorias principais)**")
        labels = ["Operações Compromissadas", "Títulos Públicos", "Títulos Privados"]
        values = [valor_aplic_ops, total_publicos, total_privados]

        if sum(values) == 0:
            st.info("Sem valores para composição (todas as categorias com valor zero).")
        else:
            fig, ax = plt.subplots(figsize=(3, 3))
            wedges, texts, autotexts = ax.pie(
                values,
                autopct="%1.1f%%",
                startangle=90,
                textprops={"fontsize": 8}
            )
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

        st.success("✅ Análise do balancete concluída.")
