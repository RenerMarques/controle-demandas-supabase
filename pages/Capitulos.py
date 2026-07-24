import logging

import streamlit as st

from config_supabase import (
    LISTA_MANUAIS,
    atualizar_capitulo,
    carregar_dados_capitulos,
    deletar_capitulo,
    inserir_capitulo,
)


logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Gestão de Capítulos",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Capítulos - Controle de Sobras")


# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------

def validar_capitulo(manual, capitulo, usado_na_demanda):
    """
    Valida os campos obrigatórios.
    """
    erros = []

    if not str(manual).strip():
        erros.append("Manual é obrigatório.")

    if not str(capitulo).strip():
        erros.append("Capítulo é obrigatório.")

    if erros:
        st.error(
            "❌ Corrija os seguintes problemas:\n\n"
            + "\n".join(f"- {erro}" for erro in erros)
        )
        return False

    return True


def obter_opcoes(df):
    """
    Cria opções de seleção contendo o ID do registro.
    """
    opcoes = []

    for _, registro in df.iterrows():
        opcoes.append(
            f"{registro['id']} - "
            f"{registro.get('capitulo', '')} - "
            f"{registro.get('manual', '')}"
        )

    return opcoes


def obter_id(opcao):
    """
    Extrai o ID do registro selecionado.
    """
    return int(str(opcao).split(" - ", 1)[0])


# -------------------------------------------------------------------
# ABAS
# -------------------------------------------------------------------

tab_cadastrar, tab_editar = st.tabs(
    [
        "➕ Cadastrar e listar",
        "📝 Editar e excluir",
    ]
)


# -------------------------------------------------------------------
# ABA CADASTRAR
# -------------------------------------------------------------------

with tab_cadastrar:
    st.subheader("➕ Novo capítulo")

    with st.form(
        "form_adicionar_capitulo",
        clear_on_submit=True,
    ):
        coluna_1, coluna_2, coluna_3 = st.columns(3)

        with coluna_1:
            manual = st.selectbox(
                "Manual",
                LISTA_MANUAIS,
            )

        with coluna_2:
            capitulo = st.text_input(
                "Capítulo",
            ).strip()

        with coluna_3:
            usado_na_demanda = st.text_input(
                "Usado na demanda",
            ).strip()

        salvar = st.form_submit_button(
            "💾 Salvar capítulo"
        )

    if salvar:
        if validar_capitulo(
            manual,
            capitulo,
            usado_na_demanda,
        ):
            with st.spinner("Salvando capítulo..."):
                sucesso, mensagem = inserir_capitulo(
                    manual,
                    capitulo,
                    usado_na_demanda,
                )

            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)

    st.divider()
    st.subheader("📋 Capítulos cadastrados")

    try:
        df_capitulos = carregar_dados_capitulos()
    except Exception:
        logger.exception("Erro ao carregar capítulos")
        st.error("❌ Não foi possível carregar os capítulos.")
        df_capitulos = None

    if df_capitulos is None:
        st.stop()

    if df_capitulos.empty:
        st.info("Nenhum capítulo cadastrado.")
    else:
        termo = st.text_input(
            "🔍 Buscar capítulo ou manual",
        ).strip().lower()

        if termo:
            resultado = df_capitulos[
                df_capitulos.astype(str)
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
            resultado = df_capitulos

        st.write(
            f"**Registros encontrados:** {len(resultado)}"
        )

        st.dataframe(
            resultado,
            use_container_width=True,
            hide_index=True,
        )


# -------------------------------------------------------------------
# ABA EDITAR E EXCLUIR
# -------------------------------------------------------------------

with tab_editar:
    st.subheader("📝 Editar ou excluir capítulo")

    df_capitulos = carregar_dados_capitulos()

    if df_capitulos.empty:
        st.info("Nenhum capítulo cadastrado.")
    else:
        opcoes = obter_opcoes(df_capitulos)

        opcao = st.selectbox(
            "Selecione o capítulo:",
            [""] + opcoes,
            key="capitulo_selecionado",
        )

        if opcao:
            id_capitulo = obter_id(opcao)

            registro = df_capitulos[
                df_capitulos["id"] == id_capitulo
            ].iloc[0]

            manual_atual = registro.get("manual", "")
            capitulo_atual = registro.get("capitulo", "")
            demanda_atual = registro.get("usado_na_demanda", "")

            with st.form("form_editar_capitulo"):
                novo_manual = st.selectbox(
                    "Manual",
                    LISTA_MANUAIS,
                    index=(
                        LISTA_MANUAIS.index(manual_atual)
                        if manual_atual in LISTA_MANUAIS
                        else 0
                    ),
                )

                novo_capitulo = st.text_input(
                    "Capítulo",
                    value=str(capitulo_atual),
                ).strip()

                nova_demanda = st.text_input(
                    "Usado na demanda",
                    value=str(demanda_atual),
                ).strip()

                atualizar = st.form_submit_button(
                    "💾 Atualizar capítulo"
                )

            if atualizar:
                if validar_capitulo(
                    novo_manual,
                    novo_capitulo,
                    nova_demanda,
                ):
                    with st.spinner("Atualizando capítulo..."):
                        sucesso, mensagem = atualizar_capitulo(
                            id_capitulo,
                            novo_manual,
                            novo_capitulo,
                            nova_demanda,
                        )

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)

            st.divider()

            st.warning(
                f"Registro selecionado: **{capitulo_atual}**"
            )

            confirmar = st.checkbox(
                "Confirmo a exclusão permanente.",
                key="confirmar_exclusao_capitulo",
            )

            if st.button(
                "🗑️ Excluir capítulo",
                type="primary",
            ):
                if not confirmar:
                    st.error(
                        "❌ Confirme a exclusão antes de continuar."
                    )
                else:
                    with st.spinner("Excluindo capítulo..."):
                        sucesso, mensagem = deletar_capitulo(
                            id_capitulo
                        )

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)