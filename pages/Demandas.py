import io
import logging
from datetime import date, datetime

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config_supabase import (
    carregar_dados_demandas,
    inserir_demanda,
    inserir_demandas_lote,
    atualizar_demanda,
    deletar_demanda,
    LISTA_TIPOS,
    LISTA_MODULOS,
    LISTA_MANUAIS,
    LISTA_MONTADORAS,
    LISTA_VERSOES,
)


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Controle de Demandas",
    page_icon="📋",
    layout="wide",
)


COLUNAS_DEMANDAS = [
    "demanda",
    "tipo",
    "modulo",
    "manual",
    "data_linkagem",
    "capitulo",
    "montadora",
    "versao",
]


def texto(valor):
    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass

    return str(valor).strip()


def converter_data(valor):
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")

    valor = texto(valor)

    if not valor:
        return ""

    for formato in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
    ):
        try:
            return datetime.strptime(
                valor,
                formato,
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    convertido = pd.to_datetime(
        valor,
        errors="coerce",
        dayfirst=True,
    )

    if pd.isna(convertido):
        return ""

    return convertido.strftime("%Y-%m-%d")


def validar_demanda(
    demanda,
    tipo,
    modulo,
    manual,
    data_linkagem,
    capitulo,
    montadora,
    versao,
):
    campos = {
        "Demanda": demanda,
        "Tipo": tipo,
        "Módulo": modulo,
        "Manual": manual,
        "Data de linkagem": data_linkagem,
        "Capítulo": capitulo,
        "Montadora": montadora,
        "Versão": versao,
    }

    vazios = [
        nome
        for nome, valor in campos.items()
        if not texto(valor)
    ]

    if vazios:
        st.error(
            "❌ Preencha os campos:\n\n"
            + "\n".join(f"- {campo}" for campo in vazios)
        )
        return False

    return True


def normalizar_upload(df):
    mapa = {
        "DEMANDA": "demanda",
        "TIPO DEMANDA": "tipo",
        "TIPO": "tipo",
        "MÓDULO": "modulo",
        "MODULO": "modulo",
        "MANUAL": "manual",
        "DATA LINKAGEM": "data_linkagem",
        "DATA_LINKAGEM": "data_linkagem",
        "CAPITULO": "capitulo",
        "CAPÍTULO": "capitulo",
        "MONTADORA": "montadora",
        "VERSÃO": "versao",
        "VERSAO": "versao",
        "ORDEM_ORIGEM": "ordem_origem",
        "ordem_origem": "ordem_origem",
    }

    df = df.copy()

    renomear = {}

    for coluna in df.columns:
        chave = str(coluna).strip()
        renomear[coluna] = mapa.get(
            chave,
            mapa.get(chave.upper(), chave.lower()),
        )

    df = df.rename(columns=renomear)

    faltantes = [
        coluna
        for coluna in COLUNAS_DEMANDAS
        if coluna not in df.columns
    ]

    if faltantes:
        st.error(
            "❌ Colunas faltantes:\n\n"
            + "\n".join(f"- {coluna}" for coluna in faltantes)
        )
        return None

    colunas_opcionais = [
        *COLUNAS_DEMANDAS,
        "ordem_origem",
    ]

    df = df[
        [
            coluna
            for coluna in colunas_opcionais
            if coluna in df.columns
        ]
    ].copy()

    for coluna in COLUNAS_DEMANDAS:
        if coluna == "data_linkagem":
            df[coluna] = df[coluna].apply(converter_data)
        else:
            df[coluna] = df[coluna].apply(texto)

    if "ordem_origem" in df.columns:
        df["ordem_origem"] = pd.to_numeric(
            df["ordem_origem"],
            errors="coerce",
        )

    df = df[
        df["demanda"].astype(str).str.strip() != ""
    ]

    if df.empty:
        st.error("❌ Nenhuma demanda válida foi encontrada.")
        return None

    datas_invalidas = df["data_linkagem"].eq("")

    if datas_invalidas.any():
        st.error(
            "❌ Existem datas inválidas ou vazias."
        )
        return None

    return df


def chave_demanda(registro):
    return "|".join(
        texto(registro.get(coluna))
        for coluna in COLUNAS_DEMANDAS
    )


def preparar_importacao(df_upload, df_existente):
    df_novo = df_upload.copy()
    df_atual = df_existente.copy()

    for coluna in COLUNAS_DEMANDAS:
        if coluna not in df_atual.columns:
            df_atual[coluna] = ""

        df_novo[coluna] = df_novo[coluna].apply(texto)
        df_atual[coluna] = df_atual[coluna].apply(texto)

    df_novo["_chave"] = df_novo.apply(
        chave_demanda,
        axis=1,
    )

    df_atual["_chave"] = df_atual.apply(
        chave_demanda,
        axis=1,
    )

    antes = len(df_novo)

    df_novo = df_novo.drop_duplicates(
        subset="_chave",
        keep="first",
    )

    duplicados_arquivo = antes - len(df_novo)

    chaves_existentes = set(
        df_atual["_chave"].tolist()
    )

    duplicados_banco = df_novo[
        df_novo["_chave"].isin(chaves_existentes)
    ]

    df_novo = df_novo[
        ~df_novo["_chave"].isin(chaves_existentes)
    ]

    df_novo = df_novo.drop(
        columns=["_chave"],
        errors="ignore",
    )

    return (
        df_novo.to_dict(orient="records"),
        duplicados_arquivo,
        len(duplicados_banco),
    )


def gerar_pdf(df):
    buffer = io.BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph(
            "Relatório de Demandas",
            estilos["Heading1"],
        ),
        Spacer(1, 10),
    ]

    dados = [
        list(df.columns)
    ]

    for _, linha in df.iterrows():
        dados.append(
            [
                texto(linha[coluna])
                for coluna in df.columns
            ]
        )

    tabela = Table(dados, repeatRows=1)

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1F4E78"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#EAF2F8"),
                    ],
                ),
            ]
        )
    )

    elementos.append(tabela)
    documento.build(elementos)

    buffer.seek(0)
    return buffer


st.title("📋 Controle de Demandas")

tab_adicionar, tab_buscar, tab_editar, tab_excluir, tab_relatorios = st.tabs(
    [
        "➕ Adicionar",
        "🔍 Buscar",
        "📝 Editar",
        "🗑️ Excluir",
        "📊 Relatórios",
    ]
)


# ================================================================
# ADICIONAR
# ================================================================

with tab_adicionar:
    modo = st.radio(
        "Método de cadastro:",
        [
            "Cadastro manual",
            "Importação em lote",
        ],
        horizontal=True,
    )

    if modo == "Cadastro manual":
        with st.form(
            "form_nova_demanda",
            clear_on_submit=True,
        ):
            col1, col2 = st.columns(2)

            with col1:
                demanda = st.text_input("Demanda")
                tipo = st.selectbox("Tipo", LISTA_TIPOS)
                modulo = st.selectbox("Módulo", LISTA_MODULOS)
                manual = st.selectbox("Manual", LISTA_MANUAIS)

            with col2:
                data = st.date_input(
                    "Data de linkagem",
                    value=date.today(),
                )
                capitulo = st.text_input("Capítulo")
                montadora = st.selectbox(
                    "Montadora",
                    LISTA_MONTADORAS,
                )
                versao = st.selectbox(
                    "Versão",
                    LISTA_VERSOES,
                )

            salvar = st.form_submit_button(
                "💾 Salvar demanda"
            )

        if salvar:
            data_linkagem = data.strftime("%Y-%m-%d")

            if validar_demanda(
                demanda,
                tipo,
                modulo,
                manual,
                data_linkagem,
                capitulo,
                montadora,
                versao,
            ):
                sucesso, mensagem = inserir_demanda(
                    demanda,
                    tipo,
                    modulo,
                    manual,
                    data_linkagem,
                    capitulo,
                    montadora,
                    versao,
                )

                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

    else:
        arquivo = st.file_uploader(
            "Envie CSV ou Excel",
            type=["csv", "xlsx"],
        )

        if arquivo is not None:
            try:
                if arquivo.name.lower().endswith(".csv"):
                    df_original = pd.read_csv(
                        arquivo,
                        sep=None,
                        engine="python",
                        encoding="utf-8-sig",
                    )
                else:
                    df_original = pd.read_excel(arquivo)

                df_upload = normalizar_upload(
                    df_original
                )

            except Exception as erro:
                logger.exception("Erro ao ler upload")
                st.error(f"❌ Erro ao ler arquivo: {erro}")
                df_upload = None

            if df_upload is not None:
                st.dataframe(
                    df_upload.head(20),
                    use_container_width=True,
                    hide_index=True,
                )

                if st.button(
                    "🔎 Verificar duplicidades",
                    key="verificar_lote_demandas",
                ):
                    df_existente = carregar_dados_demandas()

                    (
                        registros,
                        duplicados_arquivo,
                        duplicados_banco,
                    ) = preparar_importacao(
                        df_upload,
                        df_existente,
                    )

                    st.session_state[
                        "lote_demandas"
                    ] = registros

                    st.session_state[
                        "dup_arquivo_demandas"
                    ] = duplicados_arquivo

                    st.session_state[
                        "dup_banco_demandas"
                    ] = duplicados_banco

                if "lote_demandas" in st.session_state:
                    registros = st.session_state[
                        "lote_demandas"
                    ]

                    st.metric(
                        "Novos registros",
                        len(registros),
                    )

                    st.write(
                        "Duplicados no arquivo: "
                        + str(
                            st.session_state.get(
                                "dup_arquivo_demandas",
                                0,
                            )
                        )
                    )

                    st.write(
                        "Já existentes no banco: "
                        + str(
                            st.session_state.get(
                                "dup_banco_demandas",
                                0,
                            )
                        )
                    )

                    confirmar = st.checkbox(
                        "Confirmo a importação.",
                        key="confirmar_lote_demandas",
                    )

                    if st.button(
                        "🚀 Importar demandas",
                        type="primary",
                        key="importar_lote_demandas",
                    ):
                        if not confirmar:
                            st.error(
                                "❌ Confirme a importação."
                            )
                        else:
                            resultado = inserir_demandas_lote(
                                registros
                            )

                            sucesso, mensagem, _, _ = resultado

                            if sucesso:
                                st.success(mensagem)
                            else:
                                st.warning(mensagem)

                            for chave in (
                                "lote_demandas",
                                "dup_arquivo_demandas",
                                "dup_banco_demandas",
                            ):
                                st.session_state.pop(
                                    chave,
                                    None,
                                )

                            st.rerun()

    st.divider()
    st.subheader("📋 Demandas recentes")

    df = carregar_dados_demandas()

    if df.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True,
        )


# ================================================================
# BUSCAR
# ================================================================

with tab_buscar:
    df = carregar_dados_demandas()

    if df.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        campo = st.selectbox(
            "Campo",
            COLUNAS_DEMANDAS,
        )

        termo = st.text_input(
            "Pesquisar"
        ).strip()

        resultado = df.copy()

        if termo:
            resultado = resultado[
                resultado[campo]
                .astype(str)
                .str.contains(
                    termo,
                    case=False,
                    regex=False,
                    na=False,
                )
            ]

        st.write(f"**Registros encontrados:** {len(resultado)}")

        st.dataframe(
            resultado,
            use_container_width=True,
            hide_index=True,
        )


# ================================================================
# EDITAR
# ================================================================

with tab_editar:
    df = carregar_dados_demandas()

    if df.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        opcoes = df.apply(
            lambda linha: (
                f"{linha['id']} | "
                f"{linha['demanda']}"
            ),
            axis=1,
        ).tolist()

        escolhido = st.selectbox(
            "Selecione a demanda",
            opcoes,
        )

        id_demanda = int(
            escolhido.split("|", 1)[0].strip()
        )

        registro = df[
            df["id"] == id_demanda
        ].iloc[0]

        with st.form("form_editar_demanda"):
            novo_demanda = st.text_input(
                "Demanda",
                value=texto(registro["demanda"]),
            )

            novo_tipo = st.selectbox(
                "Tipo",
                LISTA_TIPOS,
                index=(
                    LISTA_TIPOS.index(registro["tipo"])
                    if registro["tipo"] in LISTA_TIPOS
                    else 0
                ),
            )

            novo_modulo = st.selectbox(
                "Módulo",
                LISTA_MODULOS,
                index=(
                    LISTA_MODULOS.index(registro["modulo"])
                    if registro["modulo"] in LISTA_MODULOS
                    else 0
                ),
            )

            novo_manual = st.selectbox(
                "Manual",
                LISTA_MANUAIS,
                index=(
                    LISTA_MANUAIS.index(registro["manual"])
                    if registro["manual"] in LISTA_MANUAIS
                    else 0
                ),
            )

            nova_data = st.date_input(
                "Data de linkagem",
                value=pd.to_datetime(
                    registro["data_linkagem"]
                ).date(),
            )

            novo_capitulo = st.text_input(
                "Capítulo",
                value=texto(registro["capitulo"]),
            )

            nova_montadora = st.selectbox(
                "Montadora",
                LISTA_MONTADORAS,
                index=(
                    LISTA_MONTADORAS.index(
                        registro["montadora"]
                    )
                    if registro["montadora"]
                    in LISTA_MONTADORAS
                    else 0
                ),
            )

            nova_versao = st.selectbox(
                "Versão",
                LISTA_VERSOES,
                index=(
                    LISTA_VERSOES.index(
                        registro["versao"]
                    )
                    if registro["versao"]
                    in LISTA_VERSOES
                    else 0
                ),
            )

            atualizar = st.form_submit_button(
                "💾 Atualizar"
            )

        if atualizar:
            sucesso, mensagem = atualizar_demanda(
                id_demanda,
                novo_demanda,
                novo_tipo,
                novo_modulo,
                novo_manual,
                nova_data.strftime("%Y-%m-%d"),
                novo_capitulo,
                nova_montadora,
                nova_versao,
            )

            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)


# ================================================================
# EXCLUIR
# ================================================================

with tab_excluir:
    df = carregar_dados_demandas()

    if df.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        opcoes = [
            f"{linha['id']} | {linha['demanda']}"
            for _, linha in df.iterrows()
        ]

        escolhido = st.selectbox(
            "Selecione a demanda",
            [""] + opcoes,
        )

        if escolhido:
            id_demanda = int(
                escolhido.split("|", 1)[0].strip()
            )

            confirmar = st.checkbox(
                "Confirmo a exclusão permanente.",
                key="confirmar_exclusao_demanda",
            )

            if st.button(
                "🗑️ Excluir",
                type="primary",
            ):
                if not confirmar:
                    st.error("❌ Confirme a exclusão.")
                else:
                    sucesso, mensagem = deletar_demanda(
                        id_demanda
                    )

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)


# ================================================================
# RELATÓRIOS
# ================================================================

with tab_relatorios:
    df = carregar_dados_demandas()

    if df.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(
            index=False,
            encoding="utf-8-sig",
        )

        st.download_button(
            "📥 Baixar CSV",
            data=csv,
            file_name="demandas.csv",
            mime="text/csv",
        )

        excel = io.BytesIO()

        with pd.ExcelWriter(
            excel,
            engine="openpyxl",
        ) as escritor:
            df.to_excel(
                escritor,
                index=False,
                sheet_name="Demandas",
            )

        st.download_button(
            "📥 Baixar Excel",
            data=excel.getvalue(),
            file_name="demandas.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        )