import streamlit as st
import logging
from config_supabase import (
    carregar_dados_capitulos,
    inserir_capitulo,
    atualizar_capitulo,
    deletar_capitulo,
    LISTA_MANUAIS
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Gestão de Capítulos", layout="wide")
st.title("📚 Capítulos - Controle de Sobras")

# --- FUNÇÕES AUXILIARES ---
def get_selectbox_index(lista, valor, nome_campo):
    """Retorna o índice seguro para selectbox."""
    try:
        return lista.index(valor)
    except ValueError:
        st.warning(f"⚠️ '{valor}' não está na lista de {nome_campo}. Usando padrão.")
        logger.warning(f"Valor '{valor}' não encontrado em {nome_campo}")
        return 0


def validar_capitulo(manual, capitulo, demanda):
    """Valida campos obrigatórios."""
    erros = []
    if not capitulo.strip():
        erros.append("Capítulo é obrigatório")

    if erros:
        st.error("❌ Erros de validação:\n" + "\n".join(f"• {e}" for e in erros))
        return False
    return True


# --- ABAS ---
tab1, tab2 = st.tabs(["➕ Cadastrar & Listar", "✏️ Editar/Excluir"])

with tab1:
    # FORMULÁRIO DE CADASTRO
    with st.expander("📝 Nova Entrada", expanded=True):
        with st.form("form_add_cap", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                c_manual = st.selectbox("Manual", LISTA_MANUAIS)
            with col2:
                c_capitulo = st.text_input("Capítulo").strip()
            with col3:
                c_demanda = st.text_input("USADO NA DEMANDA").strip()

            if st.form_submit_button("💾 Salvar Capítulo"):
                if validar_capitulo(c_manual, c_capitulo, c_demanda):
                    with st.spinner("Salvando..."):
                        sucesso, msg = inserir_capitulo(c_manual, c_capitulo, c_demanda)
                        if sucesso:
                            st.success(msg)
                            logger.info(f"Capítulo criado: {c_manual} - {c_capitulo}")
                        else:
                            st.error(msg)

    # LISTA ABAIXO DO CADASTRO
    st.subheader("📋 Registros Cadastrados")
    df_cap = carregar_dados_capitulos()

    if df_cap.empty:
        st.info("Nenhum capítulo cadastrado ainda.")
    else:
        # Busca simples
        busca = st.text_input("🔍 Buscar no cadastro (Filtro por título/manual)").strip().lower()

        if busca:
            df_show = df_cap[
                df_cap.astype(str)
                .apply(lambda x: x.str.contains(busca, case=False, regex=False, na=False))
                .any(axis=1)
            ]
        else:
            df_show = df_cap

        st.write(f"**Total de registros:** {len(df_show)}")
        st.dataframe(df_show, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("✏️ Alterar ou Remover Registro")
    df_edit = carregar_dados_capitulos()

    if df_edit.empty:
        st.info("Nenhum capítulo cadastrado ainda.")
    else:
        # Seleção do registro pelo nome do capítulo
        cap_lista = df_edit["capitulo"].tolist()
        cap_sel = st.selectbox("Selecione o capítulo para editar/excluir:", [""] + cap_lista)

        if cap_sel:
            dados = df_edit[df_edit["capitulo"] == cap_sel].iloc[0]
            id_capitulo = dados["id"]

            with st.form("form_edit"):
                try:
                    idx = LISTA_MANUAIS.index(dados["manual"])
                except ValueError:
                    st.warning(f"⚠️ Manual '{dados['manual']}' não está na lista padrão.")
                    idx = 0

                e_man = st.selectbox("Manual", LISTA_MANUAIS, index=idx)
                e_cap = st.text_input("Título do Capítulo", value=str(dados["capitulo"])).strip()
                e_dem = st.text_input("USADO NA DEMANDA", value=str(dados["usado_na_demanda"])).strip()

                if st.form_submit_button("💾 Atualizar Dados"):
                    if validar_capitulo(e_man, e_cap, e_dem):
                        with st.spinner("Atualizando..."):
                            sucesso, msg = atualizar_capitulo(id_capitulo, e_man, e_cap, e_dem)
                            if sucesso:
                                st.success(msg)
                                logger.info(f"Capítulo atualizado: {e_man} - {e_cap}")
                            else:
                                st.error(msg)

            st.divider()
            confirmar_exclusao = st.checkbox(
                "Confirmo que quero excluir este registro permanentemente.",
                key="confirma_del_cap"
            )
            if st.button("🗑️ Excluir Permanentemente", type="primary"):
                if not confirmar_exclusao:
                    st.error("❌ Marque a confirmação antes de excluir.")
                else:
                    with st.spinner("Excluindo..."):
                        sucesso, msg = deletar_capitulo(id_capitulo)
                        if sucesso:
                            st.success(msg)
                            logger.info(f"Capítulo deletado: linha {id_capitulo}")
                        else:
                            st.error(msg)