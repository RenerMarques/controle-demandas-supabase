import logging

import streamlit as st

from config_supabase import (
    carregar_dados_demandas,
    carregar_dados_modelos,
    carregar_dados_capitulos,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
)

st.set_page_config(
    page_title="Gestão Integrada",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Sistema de Gestão Integrada")
st.write("Controle de demandas, modelos e capítulos.")


df_demandas = carregar_dados_demandas()
df_modelos = carregar_dados_modelos()
df_capitulos = carregar_dados_capitulos()


col1, col2, col3 = st.columns(3)

col1.metric(
    "📋 Demandas",
    len(df_demandas),
)

col2.metric(
    "🔧 Modelos",
    len(df_modelos),
)

col3.metric(
    "📚 Capítulos",
    len(df_capitulos),
)


st.divider()

st.subheader("📈 Atividade recente")

if df_demandas.empty:
    st.info("Nenhuma demanda cadastrada.")
else:
    colunas = [
        coluna
        for coluna in [
            "demanda",
            "tipo",
            "modulo",
            "manual",
            "versao",
            "created_at",
            "ordem_origem",
        ]
        if coluna in df_demandas.columns
    ]

    st.dataframe(
        df_demandas[colunas].head(10),
        use_container_width=True,
        hide_index=True,
    )


st.divider()

st.info(
    "Use o menu lateral para acessar Demandas, "
    "Modelos, Capítulos ou Dashboard."
)


if st.button(
    "🔄 Atualizar dados",
    use_container_width=True,
):
    st.cache_data.clear()
    st.rerun()