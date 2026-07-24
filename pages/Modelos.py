import io
import logging
from datetime import datetime

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
    LISTA_MANUAIS,
    LISTA_MODULOS,
    LISTA_MONTADORAS,
    atualizar_modelo,
    carregar_dados_modelos,
    deletar_modelo,
    inserir_modelo,
)


logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Gestão de Modelos",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Controle de Modelos")


COLUNAS_ESPERADAS = [
    "modulo",
    "manual",
    "capitulo",
    "montadora",
    "modelo",
]


# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------

def normalizar_dataframe(df):
    """
    Normaliza nomes e valores do DataFrame recebido do Excel.
    """
    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    for coluna in df.columns:
        df[coluna] = (
            df[coluna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return df


def validar_modelo(
    modulo,
    manual,
    capitulo,
    montadora,
    modelo,
):
    """
    Valida os campos obrigatórios de um modelo.
    """
    erros = []

    campos = {
        "Módulo": modulo,
        "Manual": manual,
        "Capítulo": capitulo,
        "Montadora": montadora,
        "Modelo": modelo,
    }

    for nome, valor in campos.items():
        if not str(valor).strip():
            erros.append(f"{nome} é obrigatório.")

    if erros:
        st.error(
            "❌ Corrija os seguintes problemas:\n\n"
            + "\n".join(f"- {erro}" for erro in erros)
        )
        return False

    return True


def validar_dataframe_upload(df):
    """
    Verifica se o Excel possui as colunas esperadas.
    """
    if df.empty:
        st.error("❌ O arquivo está vazio.")
        return False

    df_normalizado = normalizar_dataframe(df)

    colunas_faltando = [
        coluna
        for coluna in COLUNAS_ESPERADAS
        if coluna not in df_normalizado.columns
    ]

    if colunas_faltando:
        st.error(
            "❌ Colunas faltando no arquivo:\n\n"
            + "\n".join(f"- {coluna}" for coluna in colunas_faltando)
        )
        return False

    df_validacao = df_normalizado[COLUNAS_ESPERADAS]

    linhas_vazias = df_validacao.eq("").all(axis=1)

    if linhas_vazias.any():
        st.error("❌ Existem linhas completamente vazias no arquivo.")
        return False

    if df_validacao["modelo"].eq("").any():
        st.error("❌ Existem modelos sem nome.")
        return False

    return True


def obter_opcao_registro(df, coluna_principal):
    """
    Cria opções de seleção usando o ID do banco.
    Evita editar o registro errado quando existem nomes repetidos.
    """
    opcoes = []

    for _, registro in df.iterrows():
        identificador = registro.get("id")
        nome = registro.get(coluna_principal, "")

        opcoes.append(
            f"{identificador} - {nome}"
        )

    return opcoes


def obter_id_da_opcao(opcao):
    """
    Extrai o ID da opção exibida no selectbox.
    """
    return int(str(opcao).split(" - ", 1)[0])


def gerar_pdf_modelos(df):
    """
    Gera um relatório PDF.
    """
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
    elementos = []

    elementos.append(
        Paragraph(
            "Relatório de Modelos",
            estilos["Heading1"],
        )
    )

    elementos.append(Spacer(1, 10))

    elementos.append(
        Paragraph(
            "Gerado em: "
            + datetime.now().strftime("%d/%m/%Y às %H:%M"),
            estilos["Normal"],
        )
    )

    elementos.append(Spacer(1, 15))

    if df.empty:
        elementos.append(
            Paragraph(
                "Nenhum registro encontrado.",
                estilos["Normal"],
            )
        )
    else:
        df_pdf = df.copy()

        dados = [
            list(df_pdf.columns)
        ] + df_pdf.astype(str).values.tolist()

        tabela = Table(
            dados,
            repeatRows=1,
        )

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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#EAF2F8")],
                    ),
                ]
            )
        )

        elementos.append(tabela)

    documento.build(elementos)
    buffer.seek(0)

    return buffer


def carregar_modelos_com_segurança():
    """
    Carrega os modelos sem interromper a página inteira.
    """
    try:
        return carregar_dados_modelos()
    except Exception:
        logger.exception("Erro ao carregar modelos")
        st.error("❌ Não foi possível carregar os modelos.")
        return pd.DataFrame()


# -------------------------------------------------------------------
# ABAS
# -------------------------------------------------------------------

tab_adicionar, tab_buscar, tab_editar, tab_excluir, tab_relatorios = st.tabs(
    [
        "➕ Adicionar",
        "🔍 Buscar",
        "📝 Editar",
        "🗑️ Excluir",
        "📊 Relatórios",
    ]
)


# -------------------------------------------------------------------
# ABA ADICIONAR
# -------------------------------------------------------------------

with tab_adicionar:
    st.subheader("➕ Adicionar modelo")

    modo = st.radio(
        "Método de cadastro:",
        [
            "Manual",
            "Upload em lote",
        ],
        horizontal=True,
    )

    if modo == "Manual":
        with st.form(
            "form_adicionar_modelo",
            clear_on_submit=True,
        ):
            coluna_1, coluna_2 = st.columns(2)

            with coluna_1:
                modulo = st.selectbox(
                    "Módulo",
                    LISTA_MODULOS,
                )

                manual = st.selectbox(
                    "Manual",
                    LISTA_MANUAIS,
                )

                capitulo = st.text_input(
                    "Capítulo",
                ).strip()

            with coluna_2:
                montadora = st.selectbox(
                    "Montadora",
                    LISTA_MONTADORAS,
                )

                modelo = st.text_input(
                    "Modelo",
                ).strip()

            salvar = st.form_submit_button(
                "💾 Salvar modelo"
            )

        if salvar:
            if validar_modelo(
                modulo,
                manual,
                capitulo,
                montadora,
                modelo,
            ):
                with st.spinner("Salvando modelo..."):
                    sucesso, mensagem = inserir_modelo(
                        modulo,
                        manual,
                        capitulo,
                        montadora,
                        modelo,
                    )

                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

    else:
        st.info(
            "O Excel deve conter as colunas: "
            "modulo, manual, capitulo, montadora, modelo"
        )

        arquivo = st.file_uploader(
            "Selecione um arquivo Excel",
            type=["xlsx"],
        )

        if arquivo is not None:
            try:
                df_upload = pd.read_excel(arquivo)
                df_upload = normalizar_dataframe(df_upload)
            except Exception:
                logger.exception("Erro ao ler o arquivo Excel")
                st.error("❌ Não foi possível ler o arquivo Excel.")
                df_upload = None

            if df_upload is not None:
                if validar_dataframe_upload(df_upload):
                    df_preview = (
                        df_upload[COLUNAS_ESPERADAS]
                        .copy()
                    )

                    st.write("Pré-visualização:")
                    st.dataframe(
                        df_preview.head(20),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(
                        f"{len(df_preview)} registro(s) encontrado(s)."
                    )

                    confirmar = st.button(
                        "✅ Confirmar importação",
                        key="confirmar_importacao_modelos",
                    )

                    if confirmar:
                        total_sucesso = 0
                        total_erro = 0

                        with st.spinner("Importando modelos..."):
                            for _, linha in df_preview.iterrows():
                                sucesso, _ = inserir_modelo(
                                    linha["modulo"],
                                    linha["manual"],
                                    linha["capitulo"],
                                    linha["montadora"],
                                    linha["modelo"],
                                )

                                if sucesso:
                                    total_sucesso += 1
                                else:
                                    total_erro += 1

                        if total_sucesso:
                            st.success(
                                f"✅ {total_sucesso} modelo(s) importado(s)."
                            )

                        if total_erro:
                            st.warning(
                                f"⚠️ {total_erro} modelo(s) não foram importados."
                            )

                        st.rerun()


# -------------------------------------------------------------------
# ABA BUSCAR
# -------------------------------------------------------------------

with tab_buscar:
    st.subheader("🔍 Buscar modelos")

    df_modelos = carregar_modelos_com_segurança()

    if df_modelos.empty:
        st.info("Nenhum modelo cadastrado.")
    else:
        colunas_dados = [
            coluna
            for coluna in df_modelos.columns
            if coluna not in ["id", "created_at", "updated_at"]
        ]

        modo_busca = st.radio(
            "Método de busca:",
            [
                "Filtros",
                "Busca textual",
            ],
            horizontal=True,
            key="modo_busca_modelos",
        )

        if modo_busca == "Filtros":
            col_1, col_2, col_3 = st.columns(3)

            with col_1:
                modulo_filtro = st.selectbox(
                    "Módulo",
                    ["Todos"]
                    + sorted(
                        df_modelos["modulo"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_modelo_modulo",
                )

            with col_2:
                manual_filtro = st.selectbox(
                    "Manual",
                    ["Todos"]
                    + sorted(
                        df_modelos["manual"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_modelo_manual",
                )

            with col_3:
                montadora_filtro = st.selectbox(
                    "Montadora",
                    ["Todas"]
                    + sorted(
                        df_modelos["montadora"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_modelo_montadora",
                )

            resultado = df_modelos.copy()

            if modulo_filtro != "Todos":
                resultado = resultado[
                    resultado["modulo"] == modulo_filtro
                ]

            if manual_filtro != "Todos":
                resultado = resultado[
                    resultado["manual"] == manual_filtro
                ]

            if montadora_filtro != "Todas":
                resultado = resultado[
                    resultado["montadora"] == montadora_filtro
                ]

            st.write(
                f"**Registros encontrados:** {len(resultado)}"
            )

            st.dataframe(
                resultado,
                use_container_width=True,
                hide_index=True,
            )

        else:
            coluna = st.selectbox(
                "Campo",
                colunas_dados,
                key="campo_busca_modelos",
            )

            termo = st.text_input(
                "Termo de busca",
                key="termo_busca_modelos",
            ).strip()

            if termo:
                resultado = df_modelos[
                    df_modelos[coluna]
                    .astype(str)
                    .str.contains(
                        termo,
                        case=False,
                        regex=False,
                        na=False,
                    )
                ]

                st.write(
                    f"**Registros encontrados:** {len(resultado)}"
                )

                st.dataframe(
                    resultado,
                    use_container_width=True,
                    hide_index=True,
                )


# -------------------------------------------------------------------
# ABA EDITAR
# -------------------------------------------------------------------

with tab_editar:
    st.subheader("📝 Editar modelo")

    df_modelos = carregar_modelos_com_segurança()

    if df_modelos.empty:
        st.info("Nenhum modelo cadastrado.")
    else:
        opcoes = obter_opcao_registro(
            df_modelos,
            "modelo",
        )

        opcao = st.selectbox(
            "Selecione o modelo:",
            opcoes,
            key="modelo_edicao",
        )

        id_modelo = obter_id_da_opcao(opcao)

        registro = df_modelos[
            df_modelos["id"] == id_modelo
        ].iloc[0]

        with st.form("form_editar_modelo"):
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

            novo_capitulo = st.text_input(
                "Capítulo",
                value=str(registro.get("capitulo", "")),
            ).strip()

            nova_montadora = st.selectbox(
                "Montadora",
                LISTA_MONTADORAS,
                index=(
                    LISTA_MONTADORAS.index(registro["montadora"])
                    if registro["montadora"] in LISTA_MONTADORAS
                    else 0
                ),
            )

            novo_modelo = st.text_input(
                "Modelo",
                value=str(registro.get("modelo", "")),
            ).strip()

            atualizar = st.form_submit_button(
                "💾 Atualizar modelo"
            )

        if atualizar:
            if validar_modelo(
                novo_modulo,
                novo_manual,
                novo_capitulo,
                nova_montadora,
                novo_modelo,
            ):
                with st.spinner("Atualizando modelo..."):
                    sucesso, mensagem = atualizar_modelo(
                        id_modelo,
                        novo_modulo,
                        novo_manual,
                        novo_capitulo,
                        nova_montadora,
                        novo_modelo,
                    )

                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)


# -------------------------------------------------------------------
# ABA EXCLUIR
# -------------------------------------------------------------------

with tab_excluir:
    st.subheader("🗑️ Excluir modelo")

    df_modelos = carregar_modelos_com_segurança()

    if df_modelos.empty:
        st.info("Nenhum modelo cadastrado.")
    else:
        opcoes = obter_opcao_registro(
            df_modelos,
            "modelo",
        )

        opcao = st.selectbox(
            "Selecione o modelo:",
            [""] + opcoes,
            key="modelo_exclusao",
        )

        if opcao:
            id_modelo = obter_id_da_opcao(opcao)

            registro = df_modelos[
                df_modelos["id"] == id_modelo
            ].iloc[0]

            st.warning(
                "Você está prestes a excluir o modelo: "
                f"**{registro['modelo']}**"
            )

            confirmar = st.checkbox(
                "Confirmo a exclusão permanente.",
                key="confirmar_exclusao_modelo",
            )

            if st.button(
                "🗑️ Excluir definitivamente",
                type="primary",
            ):
                if not confirmar:
                    st.error(
                        "❌ Confirme a exclusão antes de continuar."
                    )
                else:
                    with st.spinner("Excluindo modelo..."):
                        sucesso, mensagem = deletar_modelo(
                            id_modelo
                        )

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)


# -------------------------------------------------------------------
# ABA RELATÓRIOS
# -------------------------------------------------------------------

with tab_relatorios:
    st.subheader("📊 Relatórios")

    df_modelos = carregar_modelos_com_segurança()

    if df_modelos.empty:
        st.info("Nenhum modelo cadastrado.")
    else:
        colunas_exportacao = [
            coluna
            for coluna in df_modelos.columns
            if coluna not in ["id", "created_at", "updated_at"]
        ]

        df_exportacao = df_modelos[colunas_exportacao].copy()

        st.dataframe(
            df_exportacao,
            use_container_width=True,
            hide_index=True,
        )

        formato = st.radio(
            "Formato:",
            ["Excel", "PDF"],
            horizontal=True,
            key="formato_relatorio_modelos",
        )

        if formato == "Excel":
            buffer_excel = io.BytesIO()

            with pd.ExcelWriter(
                buffer_excel,
                engine="openpyxl",
            ) as escritor:
                df_exportacao.to_excel(
                    escritor,
                    index=False,
                    sheet_name="Modelos",
                )

            buffer_excel.seek(0)

            st.download_button(
                "📥 Baixar Excel",
                data=buffer_excel.getvalue(),
                file_name=(
                    "relatorio_modelos_"
                    + datetime.now().strftime("%Y%m%d_%H%M%S")
                    + ".xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
            )

        else:
            buffer_pdf = gerar_pdf_modelos(df_exportacao)

            st.download_button(
                "📥 Baixar PDF",
                data=buffer_pdf.getvalue(),
                file_name=(
                    "relatorio_modelos_"
                    + datetime.now().strftime("%Y%m%d_%H%M%S")
                    + ".pdf"
                ),
                mime="application/pdf",
            )