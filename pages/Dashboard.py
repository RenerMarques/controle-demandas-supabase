import io
import logging
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from config_supabase import (
    carregar_dados_capitulos,
    carregar_dados_demandas,
    carregar_dados_modelos,
)


logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Dashboard Analítico",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard Analítico")
st.caption(
    "Análise de demandas, modelos e capítulos armazenados no Supabase."
)


# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------

def texto_seguro(valor):
    if pd.isna(valor):
        return ""

    return str(valor).strip()


def normalizar_dataframe(df):
    """
    Garante que as colunas textuais possam ser filtradas sem erro.
    """
    df = df.copy()

    colunas_texto = [
        "demanda",
        "tipo",
        "modulo",
        "manual",
        "capitulo",
        "montadora",
        "versao",
    ]

    for coluna in colunas_texto:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def remover_colunas_internas(df):
    """
    Remove campos técnicos antes de exibir/exportar.
    """
    return df.drop(
        columns=[
            "id",
            "created_at",
            "updated_at",
        ],
        errors="ignore",
    )


# -------------------------------------------------------------------
# CARREGAR DADOS
# -------------------------------------------------------------------

try:
    df_demandas = carregar_dados_demandas()
    df_modelos = carregar_dados_modelos()
    df_capitulos = carregar_dados_capitulos()

    df_demandas = normalizar_dataframe(df_demandas)
    df_modelos = normalizar_dataframe(df_modelos)
    df_capitulos = normalizar_dataframe(df_capitulos)

except Exception:
    logger.exception("Erro ao carregar dados do dashboard")
    st.error("❌ Não foi possível carregar os dados do dashboard.")
    st.stop()


if df_demandas.empty:
    st.warning(
        "⚠️ Nenhuma demanda cadastrada. "
        "Não há dados suficientes para montar o dashboard."
    )
    st.stop()


# -------------------------------------------------------------------
# FILTROS
# -------------------------------------------------------------------

st.subheader("🔍 Filtros globais")

col_1, col_2, col_3, col_4 = st.columns(4)

with col_1:
    opcoes_versao = ["Todas"] + sorted(
        df_demandas["versao"].unique().tolist()
    )

    filtro_versao = st.selectbox(
        "Versão",
        opcoes_versao,
        key="dashboard_filtro_versao",
    )

with col_2:
    opcoes_modulo = ["Todos"] + sorted(
        df_demandas["modulo"].unique().tolist()
    )

    filtro_modulo = st.selectbox(
        "Módulo",
        opcoes_modulo,
        key="dashboard_filtro_modulo",
    )

with col_3:
    opcoes_tipo = ["Todos"] + sorted(
        df_demandas["tipo"].unique().tolist()
    )

    filtro_tipo = st.selectbox(
        "Tipo",
        opcoes_tipo,
        key="dashboard_filtro_tipo",
    )

with col_4:
    opcoes_montadora = ["Todas"] + sorted(
        df_demandas["montadora"].unique().tolist()
    )

    filtro_montadora = st.selectbox(
        "Montadora",
        opcoes_montadora,
        key="dashboard_filtro_montadora",
    )


df_filtrado = df_demandas.copy()

if filtro_versao != "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["versao"] == filtro_versao
    ]

if filtro_modulo != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["modulo"] == filtro_modulo
    ]

if filtro_tipo != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["tipo"] == filtro_tipo
    ]

if filtro_montadora != "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["montadora"] == filtro_montadora
    ]


if df_filtrado.empty:
    st.warning(
        "⚠️ Nenhum registro corresponde aos filtros selecionados."
    )
    st.stop()


# -------------------------------------------------------------------
# KPIs
# -------------------------------------------------------------------

st.divider()
st.subheader("📈 Indicadores principais")

col_1, col_2, col_3, col_4, col_5 = st.columns(5)

with col_1:
    st.metric(
        "Demandas filtradas",
        len(df_filtrado),
        delta=len(df_filtrado) - len(df_demandas),
    )

with col_2:
    st.metric(
        "Total de demandas",
        len(df_demandas),
    )

with col_3:
    st.metric(
        "Total de modelos",
        len(df_modelos),
    )

with col_4:
    st.metric(
        "Total de capítulos",
        len(df_capitulos),
    )

with col_5:
    st.metric(
        "Manuais utilizados",
        df_filtrado["manual"].nunique(),
    )


# -------------------------------------------------------------------
# GRÁFICOS: VERSÃO E TIPO
# -------------------------------------------------------------------

st.divider()
st.subheader("📊 Demandas por versão e tipo")

col_1, col_2 = st.columns(2)

with col_1:
    demandas_por_versao = (
        df_filtrado["versao"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    demandas_por_versao.columns = [
        "versao",
        "quantidade",
    ]

    figura_versao = px.bar(
        demandas_por_versao,
        x="versao",
        y="quantidade",
        title="Demandas por versão",
        labels={
            "versao": "Versão",
            "quantidade": "Quantidade",
        },
        color="quantidade",
        color_continuous_scale="Viridis",
    )

    figura_versao.update_layout(
        showlegend=False,
    )

    st.plotly_chart(
        figura_versao,
        use_container_width=True,
    )

with col_2:
    demandas_por_tipo = (
        df_filtrado["tipo"]
        .value_counts()
        .reset_index()
    )

    demandas_por_tipo.columns = [
        "tipo",
        "quantidade",
    ]

    figura_tipo = px.pie(
        demandas_por_tipo,
        names="tipo",
        values="quantidade",
        title="Distribuição por tipo de demanda",
        hole=0.35,
    )

    st.plotly_chart(
        figura_tipo,
        use_container_width=True,
    )


# -------------------------------------------------------------------
# GRÁFICOS: MÓDULO E MONTADORA
# -------------------------------------------------------------------

st.divider()
st.subheader("🔧 Demandas por módulo e montadora")

col_1, col_2 = st.columns(2)

with col_1:
    demandas_por_modulo = (
        df_filtrado["modulo"]
        .value_counts()
        .reset_index()
    )

    demandas_por_modulo.columns = [
        "modulo",
        "quantidade",
    ]

    figura_modulo = px.bar(
        demandas_por_modulo,
        x="modulo",
        y="quantidade",
        title="Demandas por módulo",
        labels={
            "modulo": "Módulo",
            "quantidade": "Quantidade",
        },
        color="quantidade",
        color_continuous_scale="Blues",
    )

    figura_modulo.update_layout(
        showlegend=False,
        xaxis_tickangle=-35,
    )

    st.plotly_chart(
        figura_modulo,
        use_container_width=True,
    )

with col_2:
    demandas_por_montadora = (
        df_filtrado["montadora"]
        .value_counts()
        .head(10)
        .reset_index()
    )

    demandas_por_montadora.columns = [
        "montadora",
        "quantidade",
    ]

    figura_montadora = px.bar(
        demandas_por_montadora,
        x="quantidade",
        y="montadora",
        orientation="h",
        title="Top 10 montadoras",
        labels={
            "montadora": "Montadora",
            "quantidade": "Quantidade",
        },
        color="quantidade",
        color_continuous_scale="Reds",
    )

    figura_montadora.update_layout(
        showlegend=False,
    )

    st.plotly_chart(
        figura_montadora,
        use_container_width=True,
    )


# -------------------------------------------------------------------
# GRÁFICO: MANUAIS
# -------------------------------------------------------------------

st.divider()
st.subheader("📚 Manuais mais utilizados")

top_manuais = (
    df_filtrado["manual"]
    .value_counts()
    .head(10)
    .reset_index()
)

top_manuais.columns = [
    "manual",
    "quantidade",
]

figura_manuais = px.bar(
    top_manuais,
    x="quantidade",
    y="manual",
    orientation="h",
    title="Top 10 manuais",
    labels={
        "manual": "Manual",
        "quantidade": "Quantidade",
    },
    color="quantidade",
    color_continuous_scale="Greens",
)

figura_manuais.update_layout(
    showlegend=False,
)

st.plotly_chart(
    figura_manuais,
    use_container_width=True,
)


# -------------------------------------------------------------------
# HEATMAP
# -------------------------------------------------------------------

st.divider()
st.subheader("🔥 Relação entre módulo e montadora")

heatmap_data = pd.crosstab(
    df_filtrado["modulo"],
    df_filtrado["montadora"],
)

if not heatmap_data.empty:
    figura_heatmap = px.imshow(
        heatmap_data,
        title="Demandas por módulo e montadora",
        labels={
            "x": "Montadora",
            "y": "Módulo",
            "color": "Quantidade",
        },
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )

    st.plotly_chart(
        figura_heatmap,
        use_container_width=True,
    )
else:
    st.info("Não há dados suficientes para o heatmap.")


# -------------------------------------------------------------------
# ANÁLISE TEMPORAL
# -------------------------------------------------------------------

st.divider()
st.subheader("📅 Evolução temporal")

df_temporal = df_filtrado.copy()

if "data_linkagem" in df_temporal.columns:
    df_temporal["data_convertida"] = pd.to_datetime(
        df_temporal["data_linkagem"],
        errors="coerce",
    )

    df_temporal = df_temporal.dropna(
        subset=["data_convertida"]
    )

    if not df_temporal.empty:
        quantidade_por_data = (
            df_temporal
            .groupby(
                df_temporal["data_convertida"].dt.date
            )
            .size()
            .reset_index(name="quantidade")
        )

        quantidade_por_data.columns = [
            "data",
            "quantidade",
        ]

        figura_tempo = px.line(
            quantidade_por_data,
            x="data",
            y="quantidade",
            markers=True,
            title="Demandas ao longo do tempo",
            labels={
                "data": "Data",
                "quantidade": "Demandas",
            },
        )

        st.plotly_chart(
            figura_tempo,
            use_container_width=True,
        )
    else:
        st.info(
            "Não foi possível interpretar as datas cadastradas."
        )


# -------------------------------------------------------------------
# TABELA DETALHADA
# -------------------------------------------------------------------

st.divider()
st.subheader("📋 Detalhes das demandas")

col_1, col_2 = st.columns([3, 1])

with col_1:
    termo = st.text_input(
        "🔍 Buscar nos registros filtrados",
        key="dashboard_busca_textual",
    ).strip().lower()

with col_2:
    limite = st.number_input(
        "Linhas a exibir",
        min_value=5,
        max_value=200,
        value=20,
        step=5,
        key="dashboard_limite",
    )


if termo:
    colunas_busca = [
        coluna
        for coluna in df_filtrado.columns
        if coluna not in [
            "id",
            "created_at",
            "updated_at",
        ]
    ]

    df_exibicao = df_filtrado[
        df_filtrado[colunas_busca]
        .astype(str)
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
else:
    df_exibicao = df_filtrado.copy()


df_exibicao = remover_colunas_internas(
    df_exibicao
)

st.write(
    f"**Registros encontrados:** {len(df_exibicao)}"
)

st.dataframe(
    df_exibicao.head(int(limite)),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Exibindo {min(int(limite), len(df_exibicao))} "
    f"de {len(df_exibicao)} registro(s)."
)


# -------------------------------------------------------------------
# EXPORTAÇÃO
# -------------------------------------------------------------------

st.divider()
st.subheader("📥 Exportar dados filtrados")

col_1, col_2 = st.columns(2)

with col_1:
    csv = df_exibicao.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        "📥 Baixar CSV",
        data=csv,
        file_name=(
            "dashboard_demandas_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".csv"
        ),
        mime="text/csv",
        key="download_csv_dashboard",
    )

with col_2:
    buffer_excel = io.BytesIO()

    with pd.ExcelWriter(
        buffer_excel,
        engine="openpyxl",
    ) as escritor:
        df_exibicao.to_excel(
            escritor,
            index=False,
            sheet_name="Demandas",
        )

    buffer_excel.seek(0)

    st.download_button(
        "📥 Baixar Excel",
        data=buffer_excel.getvalue(),
        file_name=(
            "dashboard_demandas_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        key="download_excel_dashboard",
    )