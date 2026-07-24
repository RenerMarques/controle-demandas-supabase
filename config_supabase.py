import logging
from datetime import datetime

import pandas as pd
import streamlit as st
from supabase import Client, create_client


logger = logging.getLogger(__name__)


SUPABASE_URL = st.secrets.get("supabase_url")
SUPABASE_KEY = st.secrets.get("supabase_key")


def validar_configuracao():
    """
    Valida as credenciais e a URL antes de criar o cliente.
    """
    if not SUPABASE_URL:
        st.error("❌ supabase_url não foi configurada.")
        st.stop()

    if not SUPABASE_KEY:
        st.error("❌ supabase_key não foi configurada.")
        st.stop()

    url = str(SUPABASE_URL).strip().rstrip("/")

    if "/rest/v1" in url:
        st.error(
            "❌ A supabase_url não deve conter '/rest/v1'. "
            "Use somente a URL raiz do projeto."
        )
        st.stop()

    if not url.startswith("https://"):
        st.error(
            "❌ A supabase_url deve começar com https://."
        )
        st.stop()

    return url


SUPABASE_URL = validar_configuracao()


@st.cache_resource
def conectar_supabase() -> Client:
    """
    Cria e reutiliza a conexão com o Supabase.
    """
    try:
        cliente = create_client(
            SUPABASE_URL,
            str(SUPABASE_KEY).strip(),
        )

        logger.info("Conexão com o Supabase criada.")
        return cliente

    except Exception:
        logger.exception("Erro ao criar conexão com o Supabase.")
        st.error(
            "❌ Não foi possível criar a conexão com o Supabase."
        )
        st.stop()


supabase = conectar_supabase()

# --- FUNÇÕES DE CARREGAMENTO ---

@st.cache_data(ttl=3600)
def carregar_dados_demandas():
    """Carrega demandas do Supabase."""
    try:
        response = supabase.table('demandas').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            logger.info(f"Demandas carregadas: {len(df)} registros")
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao carregar demandas: {e}")
        st.error(f"❌ Erro ao carregar demandas: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dados_modelos():
    """Carrega modelos do Supabase."""
    try:
        response = supabase.table('modelos').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            logger.info(f"Modelos carregados: {len(df)} registros")
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao carregar modelos: {e}")
        st.error(f"❌ Erro ao carregar modelos: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def carregar_dados_capitulos():
    """Carrega capítulos do Supabase."""
    try:
        response = supabase.table('capitulos').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            logger.info(f"Capítulos carregados: {len(df)} registros")
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao carregar capítulos: {e}")
        st.error(f"❌ Erro ao carregar capítulos: {str(e)}")
        return pd.DataFrame()

# --- FUNÇÕES DE INSERÇÃO ---

def inserir_demanda(demanda, tipo, modulo, manual, data_linkagem, capitulo, montadora, versao):
    """Insere nova demanda."""
    try:
        demanda_dict = {
            'demanda': demanda,
            'tipo': tipo,
            'modulo': modulo,
            'manual': manual,
            'data_linkagem': data_linkagem,
            'capitulo': capitulo,
            'montadora': montadora,
            'versao': versao
        }
        response = supabase.table('demandas').insert(demanda_dict).execute()
        st.cache_data.clear()
        logger.info(f"Demanda inserida: {demanda}")
        return True, "✅ Demanda salva com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao inserir demanda: {e}")
        return False, f"❌ Erro ao salvar: {str(e)}"

def inserir_modelo(modulo, manual, capitulo, montadora, modelo):
    """Insere novo modelo."""
    try:
        modelo_dict = {
            'modulo': modulo,
            'manual': manual,
            'capitulo': capitulo,
            'montadora': montadora,
            'modelo': modelo
        }
        response = supabase.table('modelos').insert(modelo_dict).execute()
        st.cache_data.clear()
        logger.info(f"Modelo inserido: {modelo}")
        return True, "✅ Modelo salvo com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao inserir modelo: {e}")
        return False, f"❌ Erro ao salvar: {str(e)}"

def inserir_capitulo(manual, capitulo, usado_na_demanda):
    """Insere novo capítulo."""
    try:
        capitulo_dict = {
            'manual': manual,
            'capitulo': capitulo,
            'usado_na_demanda': usado_na_demanda
        }
        response = supabase.table('capitulos').insert(capitulo_dict).execute()
        st.cache_data.clear()
        logger.info(f"Capítulo inserido: {capitulo}")
        return True, "✅ Capítulo salvo com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao inserir capítulo: {e}")
        return False, f"❌ Erro ao salvar: {str(e)}"

# --- FUNÇÕES DE ATUALIZAÇÃO ---

def atualizar_demanda(id_demanda, demanda, tipo, modulo, manual, data_linkagem, capitulo, montadora, versao):
    """Atualiza demanda existente."""
    try:
        demanda_dict = {
            'demanda': demanda,
            'tipo': tipo,
            'modulo': modulo,
            'manual': manual,
            'data_linkagem': data_linkagem,
            'capitulo': capitulo,
            'montadora': montadora,
            'versao': versao,
            'updated_at': datetime.now().isoformat()
        }
        response = supabase.table('demandas').update(demanda_dict).eq('id', id_demanda).execute()
        st.cache_data.clear()
        logger.info(f"Demanda atualizada: ID {id_demanda}")
        return True, "✅ Demanda atualizada com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao atualizar demanda: {e}")
        return False, f"❌ Erro ao atualizar: {str(e)}"

def atualizar_modelo(id_modelo, modulo, manual, capitulo, montadora, modelo):
    """Atualiza modelo existente."""
    try:
        modelo_dict = {
            'modulo': modulo,
            'manual': manual,
            'capitulo': capitulo,
            'montadora': montadora,
            'modelo': modelo,
            'updated_at': datetime.now().isoformat()
        }
        response = supabase.table('modelos').update(modelo_dict).eq('id', id_modelo).execute()
        st.cache_data.clear()
        logger.info(f"Modelo atualizado: ID {id_modelo}")
        return True, "✅ Modelo atualizado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao atualizar modelo: {e}")
        return False, f"❌ Erro ao atualizar: {str(e)}"

def atualizar_capitulo(id_capitulo, manual, capitulo, usado_na_demanda):
    """Atualiza capítulo existente."""
    try:
        capitulo_dict = {
            'manual': manual,
            'capitulo': capitulo,
            'usado_na_demanda': usado_na_demanda,
            'updated_at': datetime.now().isoformat()
        }
        response = supabase.table('capitulos').update(capitulo_dict).eq('id', id_capitulo).execute()
        st.cache_data.clear()
        logger.info(f"Capítulo atualizado: ID {id_capitulo}")
        return True, "✅ Capítulo atualizado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao atualizar capítulo: {e}")
        return False, f"❌ Erro ao atualizar: {str(e)}"

# --- FUNÇÕES DE EXCLUSÃO ---

def deletar_demanda(id_demanda):
    """Deleta demanda."""
    try:
        response = supabase.table('demandas').delete().eq('id', id_demanda).execute()
        st.cache_data.clear()
        logger.info(f"Demanda deletada: ID {id_demanda}")
        return True, "✅ Demanda deletada com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao deletar demanda: {e}")
        return False, f"❌ Erro ao deletar: {str(e)}"

def deletar_modelo(id_modelo):
    """Deleta modelo."""
    try:
        response = supabase.table('modelos').delete().eq('id', id_modelo).execute()
        st.cache_data.clear()
        logger.info(f"Modelo deletado: ID {id_modelo}")
        return True, "✅ Modelo deletado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao deletar modelo: {e}")
        return False, f"❌ Erro ao deletar: {str(e)}"

def deletar_capitulo(id_capitulo):
    """Deleta capítulo."""
    try:
        response = supabase.table('capitulos').delete().eq('id', id_capitulo).execute()
        st.cache_data.clear()
        logger.info(f"Capítulo deletado: ID {id_capitulo}")
        return True, "✅ Capítulo deletado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao deletar capítulo: {e}")
        return False, f"❌ Erro ao deletar: {str(e)}"

# --- LISTAS GLOBAIS ---
LISTA_TIPOS = ["NOVA", "CORREÇÃO", "UPGRADE"]
LISTA_MODULOS = ["SIMPLO", "ELETRICOS", "HIBRIDOS", "TRACTOR", "MOTOS"]
LISTA_MANUAIS = [
    "ABS/ASR/ESP", "CÂMBIO", "CÂMBIO TRUCK", "TABELA DE GÁS TRUCK", "TABELA DE GÁS",
    "CLIMA CAR", "CLIMA TRUCK", "CÓDIGO DE FALHAS", "ELECTRA", "ELECTRA TRUCK",
    "HIBRIDOS", "INJEÇÃO", "DIESEL", "ARLA", "LOCAR", "LOCAR TRUCK", "LUBRITEC",
    "MIX", "MIX - AIRBAG", "MIX - ALARMES", "MIX - IMOBILIZADOR", "MIX - RESETS",
    "MOTORES", "MOTORES - LINHA LEVE", "MOTORES - LINHA PESADA", "MT PRO",
    "PICO SCOPE", "REVISA CAR", "TABELA DE TORQUES DAS RODAS", "TORKS - DIREÇÃO",
    "TORKS TRUCK - DIREÇÃO", "TORKS - FREIOS", "TORKS TRUCK - FREIOS",
    "TORKS - SUSPENSÃO", "TORKS TRUCK - SUSPENSÃO", "TORKS TRUCK",
    "SCOPE TRUCK (MT PRO)", "SCOPE TRUCK (PICO SCOPE)", "SINCRO",
    "SINCRO - CORREIAS", "SINCRO - CORRENTES", "SINCRO - POLY-V",
    "MOTORES TRACTOR", "CLIMA TRACTOR", "SINCRO TRACTOR", "ELECTRA TRACTOR",
    "INJEÇÃO TRACTOR", "CÂMBIO TRACTOR", "MT PRO TRACTOR", "PICO SCOPE TRACTOR",
    "CODIGO DE FALHAS TRACTOR", "LUBRITEC MOTOS", "CODIGO DE FALHAS MOTOS",
    "INJEÇÃO MOTOS", "ELECTRA MOTOS", "ABS MOTOS", "MOTORES MOTOS", "ELETRICOS",
    "ELETRICOS - TORKS", "ELETRICOS - LUBRITEC", "ELETRICOS - REVISA",
    "ELETRICOS - LOCAR", "ELETRICOS - RESETS", "ELETRICOS - ABS", "ELETRICOS - AC",
    "ELETRICOS - INTERLOCK", "ELETRICOS - CÓDIGO DE FALHAS", "H&E - TORKS",
    "H&E - CÓDIGO DE FALHAS", "H&E - ELECTRA", "H&E - SINCRO", "H&E - LOCAR",
    "H&E - RESETS", "H&E - MT PRO", "H&E - ABS", "H&E - AC", "H&E - INTERLOCK",
    "H&E", "H&E - INJEÇÃO", "H&E - MOTORES", "H&E - LUBRITEC", "H&E - REVISA CAR", "TORKS"
]
LISTA_MONTADORAS = [
    "  ", "AGRALE", "ALFA ROMEO", "AUDI", "BMW", "BYD", "CHERY", "CHEVROLET",
    "CHRYSLER", "CITROEN", "DAEWOO", "DAF", "DAIHATSU", "DODGE", "DUCATI", "EFFA",
    "FIAT", "FORD", "FOTON", "GWM", "HARLEY DAVIDSON", "HONDA", "HUMMER", "HYUNDAI",
    "INTERNATIONAL", "ISUZU", "IVECO", "JAC MOTORS", "JAECOO", "JAGUAR", "JEEP",
    "KAWASAKI", "KIA", "LAND ROVER", "LEXUS", "LIFAN", "MAN", "MASERATI", "MAZDA",
    "MERCEDES-BENZ TRUCK", "MERCEDES-BENZ", "MG MOTORS", "MINI", "MITSUBISHI",
    "NISSAN", "PEUGEOT", "PORSCHE", "RAM", "RENAULT", "SCANIA", "SEAT", "SMART",
    "SSANGYONG", "SUBARU", "SUZUKI", "TROLLER", "TOYOTA", "VOLVO", "VOLVO TRUCK",
    "VOLKSWAGEN", "VOLKSWAGEN TRUCK", "YAMAHA", "JOHN DEERE", "VALTRA",
    "MASSEY FERGUSON", "NEW HOLLAND", "MAXION-PERKINS", "CASE"
]
LISTA_VERSOES = [
    "2024/1", "2024/2", "2024/3", "2025/1", "2025/2", "2025/3", "2026/1", "2026/2",
    "2026/3", "2027/1", "2027/2", "2027/3", "2024/1 T", "2024/2 T", "2024/3 T",
    "2025/1 T", "2025/2 T", "2025/3 T", "2026/1 T", "2026/2 T", "2026/3 T",
    "2027/1 T", "2027/2 T", "2027/3 T", "2024/1 H&E", "2024/2 H&E", "2024/3 H&E",
    "2025/1 H&E", "2025/2 H&E", "2025/3 H&E", "2026/1 H&E", "2026/2 H&E",
    "2026/3 H&E", "2027/1 H&E", "2027/2 H&E", "2027/3 H&E", "2024/1 M", "2024/2 M",
    "2024/3 M", "2025/1 M", "2025/2 M", "2025/3 M", "2026/1 M", "2026/2 M",
    "2026/3 M", "2027/1 M", "2027/2 M", "2027/3 M"
]