import streamlit as st
import pandas as pd
from datetime import datetime
import io
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from config_supabase import (
    carregar_dados_demandas,
    inserir_demanda,
    atualizar_demanda,
    deletar_demanda,
    LISTA_TIPOS, LISTA_MODULOS, LISTA_MANUAIS,
    LISTA_MONTADORAS, LISTA_VERSOES
)

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Controle de Demandas", layout="wide")
st.title("📋 Controle de Demandas")

# --- FUNÇÕES AUXILIARES ---
def parse_data(data_str):
    """Parse data em múltiplos formatos."""
    if not data_str or pd.isna(data_str):
        return datetime.now().date()

    data_str = str(data_str).strip()
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y']

    for fmt in formatos:
        try:
            return datetime.strptime(data_str, fmt).date()
        except ValueError:
            continue

    st.warning(f"⚠️ Não consegui interpretar a data: '{data_str}'")
    logger.warning(f"Data inválida: '{data_str}'")
    return datetime.now().date()


def formatar_data(data_obj):
    """Formata data para YYYY-MM-DD."""
    if isinstance(data_obj, str):
        data_obj = parse_data(data_obj)
    return data_obj.strftime("%Y-%m-%d") if data_obj else ""


def get_selectbox_index(lista, valor, nome_campo):
    """Retorna o índice seguro para selectbox."""
    try:
        return lista.index(valor)
    except ValueError:
        st.warning(f"⚠️ '{valor}' não está na lista de {nome_campo}. Usando padrão.")
        logger.warning(f"Valor '{valor}' não encontrado em {nome_campo}")
        return 0


def validar_demanda(demanda, tipo, modulo, manual, capitulo, montadora, versao):
    """Valida campos obrigatórios."""
    erros = []
    if not demanda.strip():
        erros.append("Demanda é obrigatória")
    if not capitulo.strip():
        erros.append("Capítulo é obrigatório")

    if erros:
        st.error("❌ Erros de validação:\n" + "\n".join(f"• {e}" for e in erros))
        return False
    return True


def gerar_pdf_demandas(df):
    """Gera PDF formatado com tabela de demandas."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Estilos
    styles = getSampleStyleSheet()

    # Título
    title = Paragraph("Relatório de Demandas", styles['Heading1'])
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
        col_widths = [60, 60, 60, 60, 60, 60, 60, 60]

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhum registro encontrado.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --- ABAS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ Adicionar", "🔍 Buscar", "📝 Editar", "🗑️ Excluir", "📊 Relatórios"
])

# ============ TAB 1: ADICIONAR ============
with tab1:
    st.subheader("➕ Nova Demanda")
    with st.form("form_adicionar", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            demanda = st.text_input("Demanda").strip()
            tipo = st.selectbox("Tipo", LISTA_TIPOS)
            modulo = st.selectbox("Módulo", LISTA_MODULOS)
            manual = st.selectbox("Manual", LISTA_MANUAIS)
        with col2:
            data_obj = st.date_input("Data Linkagem")
            data_linkagem = formatar_data(data_obj)
            capitulo = st.text_input("Capítulo").strip()
            montadora = st.selectbox("Montadora", LISTA_MONTADORAS)
            versao = st.selectbox("Versão", LISTA_VERSOES)

        if st.form_submit_button("💾 Salvar Nova Demanda"):
            if validar_demanda(demanda, tipo, modulo, manual, capitulo, montadora, versao):
                with st.spinner("Salvando..."):
                    sucesso, msg = inserir_demanda(
                        demanda, tipo, modulo, manual, 
                        data_linkagem, capitulo, montadora, versao
                    )
                    if sucesso:
                        st.success(msg)
                        logger.info(f"Demanda criada: {demanda}")
                    else:
                        st.error(msg)

    st.divider()
    st.subheader("📋 Demandas Cadastradas Recentemente")
    try:
        df_atualizado = carregar_dados_demandas()
        if not df_atualizado.empty:
            st.dataframe(df_atualizado.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma demanda cadastrada ainda.")
    except Exception as e:
        st.error(f"❌ Erro ao carregar demandas: {str(e)}")
        logger.error(f"Erro ao carregar demandas recentes: {e}", exc_info=True)

# ============ TAB 2: BUSCAR ============
with tab2:
    st.subheader("🔍 Busca Avançada")
    df_mod = carregar_dados_demandas()

    if df_mod.empty:
        st.info("Nenhuma demanda disponível.")
    else:
        modo_busca_m = st.radio(
            "Escolha o método de busca:",
            ["Filtros em Cascata", "Busca por Campo Específico"],
            key="radio_dem",
            horizontal=True
        )

        if modo_busca_m == "Filtros em Cascata":
            c1, c2, c3 = st.columns(3)
            with c1:
                mod_sel = st.selectbox("Módulo", ["Todos"] + sorted(df_mod["modulo"].unique().tolist()))
                tipo_sel = st.selectbox("Tipo", ["Todos"] + sorted(df_mod["tipo"].unique().tolist()))
            with c2:
                mont_sel = st.selectbox("Montadora", ["Todas"] + sorted(df_mod["montadora"].unique().tolist()))
                man_sel = st.selectbox("Manual", ["Todos"] + sorted(df_mod["manual"].unique().tolist()))
            with c3:
                ver_sel = st.selectbox("Versão", ["Todas"] + sorted(df_mod["versao"].unique().tolist()))

            final_mod = df_mod.copy()
            if mod_sel != "Todos":
                final_mod = final_mod[final_mod["modulo"] == mod_sel]
            if tipo_sel != "Todos":
                final_mod = final_mod[final_mod["tipo"] == tipo_sel]
            if mont_sel != "Todas":
                final_mod = final_mod[final_mod["montadora"] == mont_sel]
            if man_sel != "Todos":
                final_mod = final_mod[final_mod["manual"] == man_sel]
            if ver_sel != "Todas":
                final_mod = final_mod[final_mod["versao"] == ver_sel]

            st.write(f"**Total de registros:** {len(final_mod)}")
            st.dataframe(final_mod, use_container_width=True, hide_index=True)

        else:  # Busca por Campo Específico
            c1, c2 = st.columns([1, 2])
            with c1:
                coluna_alvo = st.selectbox("Selecione o campo:", df_mod.columns.tolist(), key="col_dem")
            with c2:
                valor_busca = st.text_input("Digite o valor para busca:", key="val_dem", placeholder="Ex: Ford").strip()

            if valor_busca:
                resultado_mod = df_mod[
                    df_mod[coluna_alvo].astype(str).str.contains(valor_busca, case=False, regex=False, na=False)
                ]
                st.write(f"**Resultados encontrados:** {len(resultado_mod)}")
                st.dataframe(resultado_mod, use_container_width=True, hide_index=True)
            else:
                st.info("💡 Digite um termo para começar a busca.")

# ============ TAB 3: EDITAR ============
with tab3:
    st.subheader("📝 Editar Demanda")
    df_edit = carregar_dados_demandas()

    if df_edit.empty:
        st.info("Nenhuma demanda disponível para editar.")
    else:
        demanda_sel = st.selectbox("Selecione a demanda para editar:", df_edit["demanda"].tolist())

        if demanda_sel:
            dados = df_edit[df_edit["demanda"] == demanda_sel].iloc[0]
            id_demanda = dados["id"]

            with st.form("form_edit_dem"):
                col1, col2 = st.columns(2)
                with col1:
                    n_dem = st.text_input("Demanda", value=str(dados["demanda"])).strip()
                    n_tipo = st.selectbox(
                        "Tipo",
                        LISTA_TIPOS,
                        index=get_selectbox_index(LISTA_TIPOS, dados["tipo"], "Tipo")
                    )
                    n_mod = st.selectbox(
                        "Módulo",
                        LISTA_MODULOS,
                        index=get_selectbox_index(LISTA_MODULOS, dados["modulo"], "Módulo")
                    )
                    n_man = st.selectbox(
                        "Manual",
                        LISTA_MANUAIS,
                        index=get_selectbox_index(LISTA_MANUAIS, dados["manual"], "Manual")
                    )
                with col2:
                    data_val = parse_data(dados["data_linkagem"])
                    n_data = st.date_input("Data Linkagem", value=data_val)
                    n_data_str = formatar_data(n_data)

                    n_cap = st.text_input("Capítulo", value=str(dados["capitulo"])).strip()
                    n_mon = st.selectbox(
                        "Montadora",
                        LISTA_MONTADORAS,
                        index=get_selectbox_index(LISTA_MONTADORAS, dados["montadora"], "Montadora")
                    )
                    n_ver = st.selectbox(
                        "Versão",
                        LISTA_VERSOES,
                        index=get_selectbox_index(LISTA_VERSOES, dados["versao"], "Versão")
                    )

                if st.form_submit_button("💾 Atualizar"):
                    if validar_demanda(n_dem, n_tipo, n_mod, n_man, n_cap, n_mon, n_ver):
                        with st.spinner("Atualizando..."):
                            sucesso, msg = atualizar_demanda(
                                id_demanda, n_dem, n_tipo, n_mod, n_man, 
                                n_data_str, n_cap, n_mon, n_ver
                            )
                            if sucesso:
                                st.success(msg)
                                logger.info(f"Demanda atualizada: {n_dem}")
                            else:
                                st.error(msg)

# ============ TAB 4: EXCLUIR ============
with tab4:
    st.subheader("🗑️ Excluir Demanda")
    df_del = carregar_dados_demandas()

    if df_del.empty:
        st.info("Nenhuma demanda disponível para excluir.")
    else:
        dem_del = st.selectbox("Selecione a Demanda a excluir", [""] + df_del["demanda"].tolist())

        if dem_del:
            registro = df_del[df_del["demanda"] == dem_del].iloc[0]
            id_demanda = registro["id"]

            st.warning(f"Você tem certeza que deseja excluir: **{dem_del}**?")
            confirmar = st.checkbox("Confirmo que quero excluir este registro permanentemente.", key="confirma_del_dem")

            if st.button("🗑️ Confirmar Exclusão", type="primary"):
                if not confirmar:
                    st.error("❌ Marque a confirmação antes de excluir.")
                else:
                    with st.spinner("Excluindo..."):
                        sucesso, msg = deletar_demanda(id_demanda)
                        if sucesso:
                            st.success(msg)
                            logger.info(f"Demanda deletada: {dem_del}")
                        else:
                            st.error(msg)

# ============ TAB 5: RELATÓRIOS ============
with tab5:
    st.header("📊 Relatórios e Exportação")
    df_geral = carregar_dados_demandas()

    if df_geral.empty:
        st.info("Nenhuma demanda disponível para relatório.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Por Versão")
            df_geral["versao"] = df_geral["versao"].astype(str).str.strip()
            st.bar_chart(df_geral["versao"].value_counts().sort_index())
        with col2:
            st.subheader("Por Módulo")
            df_geral["modulo"] = df_geral["modulo"].astype(str).str.strip()
            st.bar_chart(df_geral["modulo"].value_counts().sort_index())

        st.divider()
        st.subheader("📥 Gerar e Exportar Relatório")
        col_sel, formato_sel = st.columns(2)
        with col_sel:
            filtro_versao = st.selectbox("Versão:", ["Todas"] + sorted(df_geral["versao"].unique().tolist()))
            filtro_modulo = st.selectbox("Módulo:", ["Todos"] + sorted(df_geral["modulo"].unique().tolist()))
        with formato_sel:
            formato = st.radio("Formato de exportação:", ["Excel (.xlsx)", "PDF (.pdf)"])

        df_export = df_geral.copy()
        if filtro_versao != "Todas":
            df_export = df_export[df_export["versao"] == filtro_versao]
        if filtro_modulo != "Todos":
            df_export = df_export[df_export["modulo"] == filtro_modulo]

        if formato == "Excel (.xlsx)":
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name="Demandas")
            buffer.seek(0)
            st.download_button(
                "📥 Baixar Excel",
                data=buffer.getvalue(),
                file_name=f"relatorio_demandas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.ms-excel"
            )
        elif formato == "PDF (.pdf)":
            buffer = gerar_pdf_demandas(df_export)
            st.download_button(
                "📥 Baixar PDF",
                data=buffer.getvalue(),
                file_name=f"relatorio_demandas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )