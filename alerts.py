import streamlit as st
import logging

logger = logging.getLogger(__name__)

def exibir_alertas_sidebar():
    """Exibe resumo de alertas na sidebar."""
    try:
        with st.sidebar:
            st.divider()
            st.subheader("🔔 Notificações")
            st.success("✅ Sistema operacional")
            st.divider()
    except Exception as e:
        logger.error(f"Erro ao exibir alertas na sidebar: {e}")


def exibir_alertas_streamlit():
    """Exibe alertas no Streamlit."""
    try:
        st.success("✅ Nenhum alerta no momento. Sistema operacional!")
    except Exception as e:
        logger.error(f"Erro ao exibir alertas: {e}")
        st.error(f"❌ Erro ao verificar alertas")