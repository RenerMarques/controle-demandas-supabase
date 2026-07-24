import pandas as pd
import plotly.express as px
import streamlit as st

from config_supabase import (
    carregar_dados_demandas,
    carregar_dados_modelos,
    carregar_dados_capitulos,
)


st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard Analítico")

df_demandas = carregar_dados_demandas()
df_modelos = carregar_dados_modelos()
df_capitulos = carregar_dados_capitulos()

if df_demandas.empty:
    st.warning("Nenhuma demanda cadastrada.")
    st.stop()


st.subheader("🔍 Filtros")

col1, col2, col3, col4 = st.columns(4)

with col1:
    valor_versao = st.selectbox(
        "Versão",
        ["Todas"]
        + sorted(
            df_demandas["versao"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
    )

with col2:
    valor_modulo = st.selectbox(
        "Módulo",
        ["Todos"]
        + sorted(
            df_demandas["modulo"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
    )

with col3:
    valor_tipo = st.selectbox(
        "Tipo",
        ["Todos"]
        + sorted(
            df_demandas["tipo"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
    )

with col4:
    valor_montadora = st.selectbox(
        "Montadora",
        ["Todas"]
        + sorted(
            df_demandas["montadora"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
    )


df = df_demandas.copy()

if valor_versao != "Todas":
    df = df[df["versao"] == valor_versao]

if valor_modulo != "Todos":
    df = df[df["modulo"] == valor_modulo]

if valor_tipo != "Todos":
    df = df[df["tipo"] == valor_tipo]

if valor_montadora != "Todas":
    df = df[df["montadora"] == valor_montadora]


st.divider()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Demandas", len(df))
c2.metric("Modelos", len(df_modelos))
c3.metric("Capítulos", len(df_capitulos))
c4.metric("Manuais", df["manual"].nunique())


col1, col2 = st.columns(2)

with col1:
    dados = df["versao"].value_counts()

    figura = px.bar(
        x=dados.index,
        y=dados.values,
        labels={
            "x": "Versão",
            "y": "Quantidade",
        },
        title="Demandas por versão",
    )

    st.plotly_chart(
        figura,
        use_container_width=True,
    )

with col2:
    dados = df["modulo"].value_counts()

    figura = px.pie(
        values=dados.values,
        names=dados.index,
        title="Demandas por módulo",
    )

    st.plotly_chart(
        figura,
        use_container_width=True,
    )


st.divider()
st.subheader("📋 Demandas")

termo = st.text_input(
    "Buscar"
).strip()

resultado = df.copy()

if termo:
    resultado = resultado[
        resultado.astype(str)
        .apply(
            lambda coluna: coluna.str.contains(
                termo,
                case=False,
                regex=False,
                na=False,
            )
        )
        .any(axis=1)
    ]

st.dataframe(
    resultado,
    use_container_width=True,
    hide_index=True,
)

st.write(
    f"**Registros encontrados:** {len(resultado)}"
)