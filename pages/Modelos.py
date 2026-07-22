import streamlit as st
import pandas as pd
import io
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from config_supabase import (
    carregar_dados_modelos,
    inserir_modelo,
    atualizar_modelo,
    deletar_modelo,
    LISTA_MODULOS, LISTA_MANUAIS, LISTA_MONTADORAS
)

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Gestão de Modelos", layout="wide")
st.title("📋 Controle de Modelos")

COLUNAS_ESPERADAS = ["modulo", "manual", "capitulo", "montadora", "modelo"]

# --- FUNÇÕES AUXILIARES ---
def get_selectbox_index(lista, valor, nome_campo):
    """Retorna o índice seguro para selectbox."""
    try:
        return lista.index(valor)
    except ValueError:
        st.warning(f"⚠️ '{valor}' não está na lista de {nome_campo}. Usando padrão.")
        logger.warning(f"Valor '{valor}' não encontrado em {nome_campo}")
        return 0


def validar_modelo(modulo, manual, capitulo, montadora, modelo):
    """Valida campos obrigatórios."""
    erros = []
    if not modelo.strip():
        erros.append("Modelo é obrigatório")
    if not capitulo.strip():
        erros.append("Capítulo é obrigatório")

    if erros:
        st.error("❌ Erros de validação:\n" + "\n".join(f"• {e}" for e in erros))
        return False
    return True


def validar_dataframe_upload(df):
    """Valida DataFrame do upload."""
    erros = []

    # Verifica colunas
    colunas_faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
    if colunas_faltando:
        erros.append(f"Colunas faltando: {', '.join(colunas_faltando)}")

    # Verifica linhas vazias
    if not df.empty and df[COLUNAS_ESPERADAS].isnull().all(axis=1).any():
        erros.append("Há linhas completamente vazias")

    # Verifica campo MODELO obrigatório
    if not df.empty and (df["modelo"].isnull().any() or (df["modelo"].astype(str).str.strip() == "").any()):
        erros.append("Campo MODELO contém valores vazios")

    if erros:
        st.error("❌ Erros no arquivo:\n" + "\n".join(f"• {e}" for e in erros))
        return False
    return True


def gerar_pdf_modelos(df):
    """Gera PDF formatado com tabela de modelos."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Estilos
    styles = getSampleStyleSheet()

    # Título
    title = Paragraph("Relatório de Modelos", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Data do relatório
    data_rel = Paragraph(
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        styles['Normal']
    )
    elements.append(data_rel)
    elements.append(Spacer(1, 12))

    # Tabela
    if not df.empty:
        colunas = list(df.columns)
        data = [colunas] + df.values.tolist()

        # Calcula largura das colunas
        col_widths = [80, 100, 80, 100, 80]

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhum registro encontrado.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --- ABAS ---
tab_m1, tab_m2, tab_m3, tab_m4, tab_m5 = st.tabs([
    "➕ Adicionar", "🔍 Buscar", "📝 Editar", "🗑️ Excluir", "📊 Relatórios"
])

# ============ TAB 1: ADICIONAR ============
with tab_m1:
    st.subheader("➕ Adicionar Modelos")
    modo_add = st.radio("Método de cadastro:", ["Manual", "Upload em Lote (Excel)"], horizontal=True)

    if modo_add == "Manual":
        with st.form("form_add_modelo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                m_modulo = st.selectbox("Módulo", LISTA_MODULOS)
                m_manual = st.selectbox("Manual", LISTA_MANUAIS)
                m_capitulo = st.text_input("Capítulo").strip()
            with col2:
                m_montadora = st.selectbox("Montadora", LISTA_MONTADORAS)
                m_modelo = st.text_input("Modelo").strip()

            if st.form_submit_button("💾 Salvar Modelo"):
                if validar_modelo(m_modulo, m_manual, m_capitulo, m_montadora, m_modelo):
                    with st.spinner("Salvando..."):
                        sucesso, msg = inserir_modelo(m_modulo, m_manual, m_capitulo, m_montadora, m_modelo)
                        if sucesso:
                            st.success(msg)
                            logger.info(f"Modelo criado: {m_modelo}")
                        else:
                            st.error(msg)

    else:  # Upload em Lote
        st.info("📋 O arquivo Excel deve conter as colunas: modulo, manual, capitulo, montadora, modelo")
        uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=["xlsx"])

        if uploaded_file is not None:
            with st.spinner("Lendo arquivo..."):
                try:
                    df_up = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(f"❌ Não foi possível ler o arquivo: {e}")
                    logger.error(f"Erro ao ler arquivo Excel: {e}", exc_info=True)
                    df_up = None

            if df_up is not None:
                if validar_dataframe_upload(df_up):
                    df_preview = df_up[COLUNAS_ESPERADAS].fillna("")
                    st.dataframe(df_preview.head(10), use_container_width=True, hide_index=True)
                    st.caption(f"📊 {len(df_preview)} linha(s) prontas para importação.")

                    if st.button("✅ Confirmar Importação em Lote"):
                        with st.spinner("Importando..."):
                            contador_sucesso = 0
                            contador_erro = 0

                            for idx, row in df_preview.iterrows():
                                sucesso, msg = inserir_modelo(
                                    row['modulo'], row['manual'], row['capitulo'],
                                    row['montadora'], row['modelo']
                                )
                                if sucesso:
                                    contador_sucesso += 1
                                else:
                                    contador_erro += 1

                            st.success(f"✅ {contador_sucesso} modelo(s) importado(s) com sucesso!")
                            if contador_erro > 0:
                                st.warning(f"⚠️ {contador_erro} modelo(s) falharam")
                            logger.info(f"Importação em lote: {contador_sucesso} modelos")

# ============ TAB 2: BUSCAR ============
with tab_m2:
    st.subheader("🔍 Busca Avançada de Modelos")
    df_mod = carregar_dados_modelos()

    if df_mod.empty:
        st.info("Nenhum modelo cadastrado ainda.")
    else:
        modo_busca_m = st.radio(
            "Escolha o método de busca:",
            ["Filtros em Cascata", "Busca por Campo Específico"],
            key="radio_mod",
            horizontal=True
        )

        if modo_busca_m == "Filtros em Cascata":
            c1, c2, c3 = st.columns(3)
            with c1:
                mod_sel = st.selectbox("Módulo", ["Todos"] + sorted(df_mod["modulo"].unique().tolist()))
                man_sel = st.selectbox("Manual", ["Todos"] + sorted(df_mod["manual"].unique().tolist()))
            with c2:
                mont_sel = st.selectbox("Montadora", ["Todas"] + sorted(df_mod["montadora"].unique().tolist()))
                cap_sel = st.selectbox("Capítulo", ["Todos"] + sorted(df_mod["capitulo"].unique().tolist()))
            with c3:
                model_sel = st.selectbox("Modelo", ["Todos"] + sorted(df_mod["modelo"].unique().tolist()))

            final_mod = df_mod.copy()
            if mod_sel != "Todos":
                final_mod = final_mod[final_mod["modulo"] == mod_sel]
            if man_sel != "Todos":
                final_mod = final_mod[final_mod["manual"] == man_sel]
            if mont_sel != "Todas":
                final_mod = final_mod[final_mod["montadora"] == mont_sel]
            if cap_sel != "Todos":
                final_mod = final_mod[final_mod["capitulo"] == cap_sel]
            if model_sel != "Todos":
                final_mod = final_mod[final_mod["modelo"] == model_sel]

            st.write(f"**Total de registros:** {len(final_mod)}")
            st.dataframe(final_mod, use_container_width=True, hide_index=True)

        else:  # Busca por Campo Específico
            c1, c2 = st.columns([1, 2])
            with c1:
                coluna_alvo = st.selectbox("Selecione o campo:", df_mod.columns.tolist(), key="col_mod")
            with c2:
                valor_busca

