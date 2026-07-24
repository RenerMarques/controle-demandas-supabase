import logging

import streamlit as st

from config_supabase import (
    carregar_dados_demandas,
    carregar_dados_modelos,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Gestão Integrada - Supabase",
    page_icon="📋",
    layout="wide",
)


st.title("🏠 Sistema de Gestão Integrada")
st.markdown(
    "Painel central para controle de demandas, modelos e capítulos."
)


# -------------------------------------------------------------------
# MÉTRICAS PRINCIPAIS
# -------------------------------------------------------------------

try:
    df_demandas = carregar_dados_demandas()
    df_modelos = carregar_dados_modelos()

    st.subheader("📊 Visão Geral")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📋 Demandas", len(df_demandas))

    with col2:
        st.metric("🔧 Modelos", len(df_modelos))

    with col3:
        st.metric("✅ Status", "Operacional")

except Exception:
    logger.exception("Erro ao carregar as métricas da página inicial")
    st.error("❌ Não foi possível carregar as métricas.")


st.divider()


# -------------------------------------------------------------------
# NAVEGAÇÃO
# -------------------------------------------------------------------

col_esquerda, col_direita = st.columns([1, 2])


with col_esquerda:
    st.subheader("🎯 Acesso rápido")

    if st.button(
        "📋 Módulo de Demandas",
        use_container_width=True,
    ):
        st.switch_page("pages/Demandas.py")

    if st.button(
        "📚 Módulo de Capítulos",
        use_container_width=True,
    ):
        st.switch_page("pages/Capitulos.py")

    if st.button(
        "🔧 Módulo de Modelos",
        use_container_width=True,
    ):
        st.switch_page("pages/Modelos.py")

    if st.button(
        "📊 Dashboard Analítico",
        use_container_width=True,
    ):
        st.switch_page("pages/Dashboard.py")

    st.divider()

    if st.button(
        "🔄 Atualizar dados",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.success("✅ Cache atualizado.")
        st.rerun()


# -------------------------------------------------------------------
# ATIVIDADE RECENTE
# -------------------------------------------------------------------

with col_direita:
    st.subheader("📈 Atividade recente")

    try:
        if df_demandas.empty:
            st.info("Nenhuma demanda cadastrada ainda.")
        else:
            colunas = [
                "demanda",
                "tipo",
                "modulo",
                "manual",
                "versao",
            ]

            colunas_existentes = [
                coluna
                for coluna in colunas
                if coluna in df_demandas.columns
            ]

            st.dataframe(
                df_demandas[colunas_existentes].head(10),
                use_container_width=True,
                hide_index=True,
            )

    except Exception:
        logger.exception("Erro ao exibir atividade recente")
        st.error("❌ Não foi possível exibir a atividade recente.")


# -------------------------------------------------------------------
# AVISOS
# -------------------------------------------------------------------

st.divider()

st.subheader("📢 Comunicados")

col_aviso_1, col_aviso_2 = st.columns(2)

with col_aviso_1:
    st.info("ℹ️ O sistema utiliza o Supabase como banco de dados.")

with col_aviso_2:
    st.success("✅ Aplicação carregada com sucesso.")


st.divider()

st.caption("Gestão Integrada | Versão 2.0.0")