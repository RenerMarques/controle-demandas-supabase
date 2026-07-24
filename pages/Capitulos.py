import streamlit as st

from config_supabase import (
    carregar_dados_capitulos,
    inserir_capitulo,
    atualizar_capitulo,
    deletar_capitulo,
    LISTA_MANUAIS,
)


st.set_page_config(
    page_title="Gestão de Capítulos",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Controle de Capítulos")


def indice_seguro(lista, valor):
    try:
        return lista.index(valor)
    except ValueError:
        return 0


tab_adicionar, tab_editar = st.tabs(
    [
        "➕ Adicionar",
        "📝 Editar / Excluir",
    ]
)


with tab_adicionar:
    with st.form(
        "form_capitulo",
        clear_on_submit=True,
    ):
        manual = st.selectbox(
            "Manual",
            LISTA_MANUAIS,
        )

        capitulo = st.text_input(
            "Capítulo"
        )

        usado_na_demanda = st.text_input(
            "Usado na demanda"
        )

        salvar = st.form_submit_button(
            "💾 Salvar capítulo"
        )

    if salvar:
        if not capitulo.strip():
            st.error("❌ O capítulo é obrigatório.")
        else:
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

    df = carregar_dados_capitulos()

    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )


with tab_editar:
    df = carregar_dados_capitulos()

    if df.empty:
        st.info("Nenhum capítulo cadastrado.")
    else:
        opcoes = [
            f"{linha['id']} | {linha['capitulo']}"
            for _, linha in df.iterrows()
        ]

        escolhido = st.selectbox(
            "Selecione o capítulo",
            opcoes,
        )

        id_capitulo = int(
            escolhido.split("|", 1)[0].strip()
        )

        registro = df[
            df["id"] == id_capitulo
        ].iloc[0]

        with st.form("form_editar_capitulo"):
            novo_manual = st.selectbox(
                "Manual",
                LISTA_MANUAIS,
                index=indice_seguro(
                    LISTA_MANUAIS,
                    registro["manual"],
                ),
            )

            novo_capitulo = st.text_input(
                "Capítulo",
                value=str(registro["capitulo"]),
            )

            novo_usado = st.text_input(
                "Usado na demanda",
                value=str(
                    registro["usado_na_demanda"]
                ),
            )

            atualizar = st.form_submit_button(
                "💾 Atualizar"
            )

        if atualizar:
            sucesso, mensagem = atualizar_capitulo(
                id_capitulo,
                novo_manual,
                novo_capitulo,
                novo_usado,
            )

            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)

        st.divider()

        confirmar = st.checkbox(
            "Confirmo a exclusão.",
            key="confirmar_exclusao_capitulo",
        )

        if st.button(
            "🗑️ Excluir capítulo",
            type="primary",
        ):
            if not confirmar:
                st.error("❌ Confirme a exclusão.")
            else:
                sucesso, mensagem = deletar_capitulo(
                    id_capitulo
                )

                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)