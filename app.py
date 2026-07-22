import streamlit as st
import logging
from config_supabase import carregar_dados_demandas, carregar_dados_modelos

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Gestão Integrada - Supabase", layout="wide")

st.title("🏠 Sistema de Gestão Integrada (Supabase)")
st.markdown("Bem-vindo ao painel central com banco de dados PostgreSQL")

# --- MÉTRICAS ---
try:
    df_d = carregar_dados_demandas()
    df_m = carregar_dados_modelos()

    st.subheader("📊 Visão Geral")
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Demandas", len(df_d))
    col2.metric("🔧 Modelos", len(df_m))
    col3.metric("✅ Status", "Operacional")
except Exception as e:
    st.error(f"❌ Erro ao carregar dados: {str(e)}")
    logger.error(f"Erro ao carregar métricas: {e}", exc_info=True)

st.divider()

# --- NAVEGAÇÃO ---
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("🎯 Acesso Rápido")

    if st.button("📋 Módulo de Demandas", use_container_width=True):
        st.switch_page("pages/Demandas.py")

    if st.button("📚 Módulo de Capítulos", use_container_width=True):
        st.switch_page("pages/Capitulos.py")

    if st.button("🔧 Módulo de Modelos", use_container_width=True):
        st.switch_page("pages/Modelos.py")

    if st.button("📊 Dashboard Analítico", use_container_width=True):
        st.switch_page("pages/Dashboard.py")

    st.write("---")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        with st.spinner("Atualizando cache..."):
            st.cache_data.clear()
            st.success("✅ Cache atualizado!")
            st.rerun()

with col_right:
    st.subheader("📈 Atividade Recente")
    try:
        if not df_d.empty:
            st.dataframe(
                df_d[['demanda', 'tipo', 'modulo', 'manual', 'versao']].head(5),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma demanda cadastrada ainda.")
    except Exception as e:
        st.error(f"❌ Erro ao exibir atividade: {str(e)}")

# --- AVISOS ---
st.divider()
st.subheader("📢 Comunicados")
c_av1, c_av2 = st.columns(2)
with c_av1:
    st.info("ℹ️ Projeto migrado para Supabase (PostgreSQL)")
with c_av2:
    st.success("✅ Sistema operacional e totalmente gratuito!")

# --- RODAPÉ ---
st.divider()
st.write("© 2026 Gestão Integrada | Versão 2.0.0 (Supabase)")