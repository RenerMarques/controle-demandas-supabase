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
    LISTA_MANUAIS,
    LISTA_MODULOS,
    LISTA_MONTADORAS,
    LISTA_TIPOS,
    LISTA_VERSOES,
    atualizar_demanda,
    carregar_dados_demandas,
    deletar_demanda,
    inserir_demanda,
)


logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Controle de Demandas",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Controle de Demandas")


# -------------------------------------------------------------------
# CONSTANTES
# -------------------------------------------------------------------

COLUNAS_DADOS = [
    "demanda",
    "tipo",
    "modulo",
    "manual",
    "data_linkagem",
    "capitulo",
    "montadora",
    "versao",
]


# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------

def texto_seguro(valor):
    """
    Converte valores nulos ou não textuais em texto seguro.
    """
    if pd.isna(valor):
        return ""

    return str(valor).strip()


def obter_indice_seguro(lista, valor):
    """
    Retorna o índice de um valor na lista.
    Se o valor não existir, retorna 0.
    """
    valor = texto_seguro(valor)

    try:
        return lista.index(valor)
    except ValueError:
        return 0


def converter_para_date(valor):
    """
    Converte valores do Supabase para datetime.date.
    Aceita:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - datetime
    - date
    """
    if valor is None or pd.isna(valor):
        return date.today()

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    valor = str(valor).strip()

    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for formato in formatos:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue

    convertido = pd.to_datetime(valor, errors="coerce")

    if not pd.isna(convertido):
        return convertido.date()

    return date.today()


def formatar_data_supabase(valor):
    """
    Converte uma data para o formato esperado pelo PostgreSQL.
    """
    if isinstance(valor, str):
        valor = converter_para_date(valor)

    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")

    return ""


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
    """
    Valida os campos obrigatórios da demanda.
    """
    erros = []

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

    for nome, valor in campos.items():
        if not texto_seguro(valor):
            erros.append(f"{nome} é obrigatório.")

    if erros:
        st.error(
            "❌ Corrija os seguintes problemas:\n\n"
            + "\n".join(f"- {erro}" for erro in erros)
        )
        return False

    return True


def carregar_demandas():
    """
    Carrega os dados sem interromper a página em caso de erro.
    """
    try:
        df = carregar_dados_demandas()

        if df is None:
            return pd.DataFrame()

        return df.copy()

    except Exception:
        logger.exception("Erro ao carregar demandas")
        st.error("❌ Não foi possível carregar as demandas.")
        return pd.DataFrame()


def colunas_visiveis(df):
    """
    Remove colunas internas da visualização.
    """
    colunas_remover = {
        "id",
        "created_at",
        "updated_at",
    }

    return [
        coluna
        for coluna in df.columns
        if coluna not in colunas_remover
    ]


def criar_opcoes_registros(df):
    """
    Cria opções usando o ID para evitar confusão entre registros
    com nomes iguais.
    """
    opcoes = []

    for _, registro in df.iterrows():
        identificador = registro.get("id")
        demanda = texto_seguro(registro.get("demanda"))
        data_linkagem = texto_seguro(
            registro.get("data_linkagem")
        )
        capitulo = texto_seguro(
            registro.get("capitulo")
        )

        opcoes.append(
            f"{identificador} | "
            f"{demanda} | "
            f"{data_linkagem} | "
            f"Capítulo: {capitulo}"
        )

    return opcoes


def extrair_id_opcao(opcao):
    """
    Obtém o ID a partir da opção exibida no selectbox.
    """
    return int(str(opcao).split("|", 1)[0].strip())


def gerar_pdf_demandas(df):
    """
    Gera um relatório PDF com os dados filtrados.
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
            "Relatório de Demandas",
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
                "Nenhuma demanda encontrada.",
                estilos["Normal"],
            )
        )
    else:
        colunas = list(df.columns)

        dados = [
            [Paragraph(str(coluna), estilos["Normal"]) for coluna in colunas]
        ]

        for _, linha in df.iterrows():
            dados.append(
                [
                    Paragraph(
                        texto_seguro(linha.get(coluna)),
                        estilos["Normal"],
                    )
                    for coluna in colunas
                ]
            )

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
                        "TOP",
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


# -------------------------------------------------------------------
# CARREGAMENTO INICIAL
# -------------------------------------------------------------------

df_demandas = carregar_demandas()


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
    st.subheader("➕ Nova Demanda")

    with st.form(
        "form_adicionar_demanda",
        clear_on_submit=True,
    ):
        coluna_1, coluna_2 = st.columns(2)

        with coluna_1:
            demanda = st.text_input("Demanda").strip()

            tipo = st.selectbox(
                "Tipo",
                LISTA_TIPOS,
            )

            modulo = st.selectbox(
                "Módulo",
                LISTA_MODULOS,
            )

            manual = st.selectbox(
                "Manual",
                LISTA_MANUAIS,
            )

        with coluna_2:
            data_obj = st.date_input(
                "Data de linkagem",
                value=date.today(),
            )

            capitulo = st.text_input(
                "Capítulo"
            ).strip()

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
        data_linkagem = formatar_data_supabase(data_obj)

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
            with st.spinner("Salvando demanda..."):
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
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(mensagem)

    st.divider()
    st.subheader("📋 Demandas cadastradas")

    if df_demandas.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        colunas = colunas_visiveis(df_demandas)

        st.dataframe(
            df_demandas[colunas].head(10),
            use_container_width=True,
            hide_index=True,
        )


# -------------------------------------------------------------------
# ABA BUSCAR
# -------------------------------------------------------------------

with tab_buscar:
    st.subheader("🔍 Buscar demandas")

    if df_demandas.empty:
        st.info("Nenhuma demanda cadastrada.")
    else:
        modo_busca = st.radio(
            "Método de busca:",
            [
                "Filtros",
                "Busca textual",
            ],
            horizontal=True,
            key="modo_busca_demandas",
        )

        if modo_busca == "Filtros":
            col_1, col_2, col_3 = st.columns(3)

            with col_1:
                filtro_modulo = st.selectbox(
                    "Módulo",
                    ["Todos"]
                    + sorted(
                        df_demandas["modulo"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_modulo",
                )

                filtro_tipo = st.selectbox(
                    "Tipo",
                    ["Todos"]
                    + sorted(
                        df_demandas["tipo"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_tipo",
                )

            with col_2:
                filtro_manual = st.selectbox(
                    "Manual",
                    ["Todos"]
                    + sorted(
                        df_demandas["manual"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_manual",
                )

                filtro_montadora = st.selectbox(
                    "Montadora",
                    ["Todas"]
                    + sorted(
                        df_demandas["montadora"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_montadora",
                )

            with col_3:
                filtro_versao = st.selectbox(
                    "Versão",
                    ["Todas"]
                    + sorted(
                        df_demandas["versao"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_versao",
                )

                filtro_capitulo = st.selectbox(
                    "Capítulo",
                    ["Todos"]
                    + sorted(
                        df_demandas["capitulo"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="filtro_demanda_capitulo",
                )

            resultado = df_demandas.copy()

            if filtro_modulo != "Todos":
                resultado = resultado[
                    resultado["modulo"] == filtro_modulo
                ]

            if filtro_tipo != "Todos":
                resultado = resultado[
                    resultado["tipo"] == filtro_tipo
                ]

            if filtro_manual != "Todos":
                resultado = resultado[
                    resultado["manual"] == filtro_manual
                ]

            if filtro_montadora != "Todas":
                resultado = resultado[
                    resultado["montadora"] == filtro_montadora
                ]

            if filtro_versao != "Todas":
                resultado = resultado[
                    resultado["versao"] == filtro_versao
                ]

            if filtro_capitulo != "Todos":
                resultado = resultado[
                    resultado["capitulo"] == filtro_capitulo
                ]

            st.write(
                f"**Registros encontrados:** {len(resultado)}"
            )

            st.dataframe(
                resultado[colunas_visiveis(resultado)],
                use_container_width=True,
                hide_index=True,
            )

        else:
            col_1, col_2 = st.columns([1, 2])

            with col_1:
                colunas_busca = colunas_visiveis(
                    df_demandas
                )

                coluna_alvo = st.selectbox(
                    "Campo",
                    colunas_busca,
                    key="campo_busca_demanda",
                )

            with col_2:
                termo = st.text_input(
                    "Termo de busca",
                    key="termo_busca_demanda",
                ).strip()

            if termo:
                resultado = df_demandas[
                    df_demandas[coluna_alvo]
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
                    resultado[colunas_visiveis(resultado)],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Digite um termo para iniciar a busca.")


# -------------------------------------------------------------------
# ABA EDITAR
# -------------------------------------------------------------------

with tab_editar:
    st.subheader("📝 Editar demanda")

    if df_demandas.empty:
        st.info("Nenhuma demanda disponível para editar.")
    else:
        opcoes = criar_opcoes_registros(df_demandas)

        opcao = st.selectbox(
            "Selecione o registro:",
            opcoes,
            key="demanda_editar_opcao",
        )

        id_demanda = extrair_id_opcao(opcao)

        registro = df_demandas[
            df_demandas["id"] == id_demanda
        ].iloc[0]

        with st.form("form_editar_demanda"):
            coluna_1, coluna_2 = st.columns(2)

            with coluna_1:
                nova_demanda = st.text_input(
                    "Demanda",
                    value=texto_seguro(
                        registro.get("demanda")
                    ),
                ).strip()

                novo_tipo = st.selectbox(
                    "Tipo",
                    LISTA_TIPOS,
                    index=obter_indice_seguro(
                        LISTA_TIPOS,
                        registro.get("tipo"),
                    ),
                )

                novo_modulo = st.selectbox(
                    "Módulo",
                    LISTA_MODULOS,
                    index=obter_indice_seguro(
                        LISTA_MODULOS,
                        registro.get("modulo"),
                    ),
                )

                novo_manual = st.selectbox(
                    "Manual",
                    LISTA_MANUAIS,
                    index=obter_indice_seguro(
                        LISTA_MANUAIS,
                        registro.get("manual"),
                    ),
                )

            with coluna_2:
                nova_data = st.date_input(
                    "Data de linkagem",
                    value=converter_para_date(
                        registro.get("data_linkagem")
                    ),
                )

                novo_capitulo = st.text_input(
                    "Capítulo",
                    value=texto_seguro(
                        registro.get("capitulo")
                    ),
                ).strip()

                nova_montadora = st.selectbox(
                    "Montadora",
                    LISTA_MONTADORAS,
                    index=obter_indice_seguro(
                        LISTA_MONTADORAS,
                        registro.get("montadora"),
                    ),
                )

                nova_versao = st.selectbox(
                    "Versão",
                    LISTA_VERSOES,
                    index=obter_indice_seguro(
                        LISTA_VERSOES,
                        registro.get("versao"),
                    ),
                )

            atualizar = st.form_submit_button(
                "💾 Atualizar demanda"
            )

        if atualizar:
            nova_data_str = formatar_data_supabase(nova_data)

            if validar_demanda(
                nova_demanda,
                novo_tipo,
                novo_modulo,
                novo_manual,
                nova_data_str,
                novo_capitulo,
                nova_montadora,
                nova_versao,
            ):
                with st.spinner("Atualizando demanda..."):
                    sucesso, mensagem = atualizar_demanda(
                        id_demanda,
                        nova_demanda,
                        novo_tipo,
                        novo_modulo,
                        novo_manual,
                        nova_data_str,
                        novo_capitulo,
                        nova_montadora,
                        nova_versao,
                    )

                if sucesso:
                    st.success(mensagem)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(mensagem)


# -------------------------------------------------------------------
# ABA EXCLUIR
# -------------------------------------------------------------------

with tab_excluir:
    st.subheader("🗑️ Excluir demanda")

    if df_demandas.empty:
        st.info("Nenhuma demanda disponível para excluir.")
    else:
        opcoes = criar_opcoes_registros(df_demandas)

        opcao = st.selectbox(
            "Selecione o registro:",
            [""] + opcoes,
            key="demanda_excluir_opcao",
        )

        if opcao:
            id_demanda = extrair_id_opcao(opcao)

            registro = df_demandas[
                df_demandas["id"] == id_demanda
            ].iloc[0]

            nome_demanda = texto_seguro(
                registro.get("demanda")
            )

            st.warning(
                f"Você está prestes a excluir a demanda "
                f"**{nome_demanda}**."
            )

            confirmar = st.checkbox(
                "Confirmo a exclusão permanente.",
                key="confirmar_exclusao_demanda",
            )

            if st.button(
                "🗑️ Excluir definitivamente",
                type="primary",
                key="botao_excluir_demanda",
            ):
                if not confirmar:
                    st.error(
                        "❌ Confirme a exclusão antes de continuar."
                    )
                else:
                    with st.spinner("Excluindo demanda..."):
                        sucesso, mensagem = deletar_demanda(
                            id_demanda
                        )

                    if sucesso:
                        st.success(mensagem)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(mensagem)


# -------------------------------------------------------------------
# ABA RELATÓRIOS
# -------------------------------------------------------------------

with tab_relatorios:
    st.subheader("📊 Relatórios de demandas")

    if df_demandas.empty:
        st.info("Nenhuma demanda disponível para relatório.")
    else:
        resultado = df_demandas.copy()

        col_1, col_2, col_3 = st.columns(3)

        with col_1:
            filtro_versao_relatorio = st.selectbox(
                "Versão",
                ["Todas"]
                + sorted(
                    resultado["versao"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                ),
                key="relatorio_demanda_versao",
            )

        with col_2:
            filtro_modulo_relatorio = st.selectbox(
                "Módulo",
                ["Todos"]
                + sorted(
                    resultado["modulo"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                ),
                key="relatorio_demanda_modulo",
            )

        with col_3:
            formato = st.radio(
                "Formato",
                [
                    "Excel (.xlsx)",
                    "PDF (.pdf)",
                ],
                key="formato_relatorio_demanda",
            )

        if filtro_versao_relatorio != "Todas":
            resultado = resultado[
                resultado["versao"]
                == filtro_versao_relatorio
            ]

        if filtro_modulo_relatorio != "Todos":
            resultado = resultado[
                resultado["modulo"]
                == filtro_modulo_relatorio
            ]

        resultado_exportacao = resultado[
            colunas_visiveis(resultado)
        ].copy()

        st.write(
            f"**Registros encontrados:** "
            f"{len(resultado_exportacao)}"
        )

        st.dataframe(
            resultado_exportacao,
            use_container_width=True,
            hide_index=True,
        )

        if not resultado_exportacao.empty:
            if formato == "Excel (.xlsx)":
                buffer_excel = io.BytesIO()

                with pd.ExcelWriter(
                    buffer_excel,
                    engine="openpyxl",
                ) as escritor:
                    resultado_exportacao.to_excel(
                        escritor,
                        index=False,
                        sheet_name="Demandas",
                    )

                buffer_excel.seek(0)

                st.download_button(
                    "📥 Baixar Excel",
                    data=buffer_excel.getvalue(),
                    file_name=(
                        "relatorio_demandas_"
                        + datetime.now().strftime(
                            "%Y%m%d_%H%M%S"
                        )
                        + ".xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet"
                    ),
                    key="download_excel_demandas",
                )

            else:
                buffer_pdf = gerar_pdf_demandas(
                    resultado_exportacao
                )

                st.download_button(
                    "📥 Baixar PDF",
                    data=buffer_pdf.getvalue(),
                    file_name=(
                        "relatorio_demandas_"
                        + datetime.now().strftime(
                            "%Y%m%d_%H%M%S"
                        )
                        + ".pdf"
                    ),
                    mime="application/pdf",
                    key="download_pdf_demandas",
                )
        else:
            st.warning(
                "⚠️ Nenhum registro encontrado para exportar."
            )