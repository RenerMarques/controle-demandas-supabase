import logging
from datetime import datetime

import pandas as pd
import streamlit as st
from supabase import Client, create_client


logger = logging.getLogger(__name__)


# ================================================================
# CONEXÃO
# ================================================================

SUPABASE_URL = st.secrets.get("supabase_url")
SUPABASE_KEY = st.secrets.get("supabase_key")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "❌ Configure supabase_url e supabase_key "
        "nos secrets do Streamlit."
    )
    st.stop()


@st.cache_resource
def conectar_supabase() -> Client:
    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )
    except Exception as erro:
        logger.exception("Erro ao conectar ao Supabase")
        st.error(f"❌ Erro ao conectar ao Supabase: {erro}")
        st.stop()


supabase = conectar_supabase()


# ================================================================
# FUNÇÕES AUXILIARES
# ================================================================

def limpar_texto(valor):
    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass

    return str(valor).strip()


def invalidar_cache():
    st.cache_data.clear()


def _carregar_todos_registros(
    tabela,
    tamanho_pagina=1000,
):
    """
    Carrega todos os registros da tabela usando paginação.

    Demandas:
        created_at DESC
        ordem_origem DESC
        id DESC

    Outras tabelas:
        created_at DESC
        id DESC
    """
    registros_finais = []
    inicio = 0

    while True:
        fim = inicio + tamanho_pagina - 1

        consulta = (
            supabase
            .table(tabela)
            .select("*")
        )

        if tabela == "demandas":
            consulta = (
                consulta
                .order("created_at", desc=True)
                .order("ordem_origem", desc=True)
                .order("id", desc=True)
            )
        else:
            consulta = (
                consulta
                .order("created_at", desc=True)
                .order("id", desc=True)
            )

        resposta = (
            consulta
            .range(inicio, fim)
            .execute()
        )

        pagina = resposta.data or []

        if not pagina:
            break

        registros_finais.extend(pagina)

        if len(pagina) < tamanho_pagina:
            break

        inicio += tamanho_pagina

    return pd.DataFrame(registros_finais)


# ================================================================
# CARREGAMENTO
# ================================================================

@st.cache_data(ttl=600)
def carregar_dados_demandas():
    try:
        return _carregar_todos_registros("demandas")
    except Exception as erro:
        logger.exception("Erro ao carregar demandas")
        st.error(f"❌ Erro ao carregar demandas: {erro}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def carregar_dados_modelos():
    try:
        return _carregar_todos_registros("modelos")
    except Exception as erro:
        logger.exception("Erro ao carregar modelos")
        st.error(f"❌ Erro ao carregar modelos: {erro}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def carregar_dados_capitulos():
    try:
        return _carregar_todos_registros("capitulos")
    except Exception as erro:
        logger.exception("Erro ao carregar capítulos")
        st.error(f"❌ Erro ao carregar capítulos: {erro}")
        return pd.DataFrame()


# ================================================================
# ORDEM DAS DEMANDAS
# ================================================================

def obter_proxima_ordem_demanda():
    """
    Retorna maior ordem_origem + 1.
    """
    resposta = (
        supabase
        .table("demandas")
        .select("ordem_origem")
        .order("ordem_origem", desc=True)
        .limit(1)
        .execute()
    )

    registros = resposta.data or []

    if not registros:
        return 1

    maior = registros[0].get("ordem_origem")

    if maior is None:
        return 1

    return int(maior) + 1


# ================================================================
# DEMANDAS
# ================================================================

def inserir_demanda(
    demanda,
    tipo,
    modulo,
    manual,
    data_linkagem,
    capitulo,
    montadora,
    versao,
):
    try:
        dados = {
            "demanda": limpar_texto(demanda),
            "tipo": limpar_texto(tipo),
            "modulo": limpar_texto(modulo),
            "manual": limpar_texto(manual),
            "data_linkagem": data_linkagem,
            "capitulo": limpar_texto(capitulo),
            "montadora": limpar_texto(montadora),
            "versao": limpar_texto(versao),
            "ordem_origem": obter_proxima_ordem_demanda(),
        }

        supabase.table("demandas").insert(dados).execute()
        invalidar_cache()

        return True, "✅ Demanda salva com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao inserir demanda")
        return False, f"❌ Erro ao salvar demanda: {erro}"


def inserir_demandas_lote(
    registros,
    tamanho_lote=500,
):
    """
    Insere demandas em lotes.

    Se ordem_origem não vier no arquivo, ela será gerada.
    """
    if not registros:
        return False, "❌ Nenhum registro para importar.", 0, 0

    registros = [
        dict(registro)
        for registro in registros
    ]

    proxima_ordem = obter_proxima_ordem_demanda()

    for indice, registro in enumerate(registros):
        valor = registro.get("ordem_origem")

        if valor in (None, "") or pd.isna(valor):
            registro["ordem_origem"] = (
                proxima_ordem + indice
            )
        else:
            registro["ordem_origem"] = int(valor)

        registro.pop("id", None)
        registro.pop("created_at", None)
        registro.pop("updated_at", None)

    total_inserido = 0
    total_erros = 0
    erros = []

    for inicio in range(
        0,
        len(registros),
        tamanho_lote,
    ):
        fim = inicio + tamanho_lote
        lote = registros[inicio:fim]

        try:
            resposta = (
                supabase
                .table("demandas")
                .insert(lote)
                .execute()
            )

            total_inserido += len(resposta.data or [])

        except Exception as erro:
            total_erros += len(lote)
            erros.append(
                f"Lote {inicio + 1}-{min(fim, len(registros))}: "
                f"{erro}"
            )
            logger.exception("Erro ao inserir lote")

    invalidar_cache()

    if total_erros == 0:
        return (
            True,
            f"✅ {total_inserido} demanda(s) importada(s).",
            total_inserido,
            0,
        )

    mensagem = (
        f"⚠️ Importação parcial. "
        f"Inseridas: {total_inserido}. "
        f"Erros: {total_erros}."
    )

    if erros:
        mensagem += "\n" + "\n".join(erros[:3])

    return (
        total_inserido > 0,
        mensagem,
        total_inserido,
        total_erros,
    )


def atualizar_demanda(
    id_demanda,
    demanda,
    tipo,
    modulo,
    manual,
    data_linkagem,
    capitulo,
    montadora,
    versao,
):
    try:
        dados = {
            "demanda": limpar_texto(demanda),
            "tipo": limpar_texto(tipo),
            "modulo": limpar_texto(modulo),
            "manual": limpar_texto(manual),
            "data_linkagem": data_linkagem,
            "capitulo": limpar_texto(capitulo),
            "montadora": limpar_texto(montadora),
            "versao": limpar_texto(versao),
            "updated_at": datetime.now().isoformat(),
        }

        (
            supabase
            .table("demandas")
            .update(dados)
            .eq("id", id_demanda)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Demanda atualizada com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao atualizar demanda")
        return False, f"❌ Erro ao atualizar demanda: {erro}"


def deletar_demanda(id_demanda):
    try:
        (
            supabase
            .table("demandas")
            .delete()
            .eq("id", id_demanda)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Demanda excluída com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao excluir demanda")
        return False, f"❌ Erro ao excluir demanda: {erro}"


# ================================================================
# MODELOS
# ================================================================

def inserir_modelo(
    modulo,
    manual,
    capitulo,
    montadora,
    modelo,
):
    try:
        dados = {
            "modulo": limpar_texto(modulo),
            "manual": limpar_texto(manual),
            "capitulo": limpar_texto(capitulo),
            "montadora": limpar_texto(montadora),
            "modelo": limpar_texto(modelo),
        }

        supabase.table("modelos").insert(dados).execute()
        invalidar_cache()

        return True, "✅ Modelo salvo com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao inserir modelo")
        return False, f"❌ Erro ao salvar modelo: {erro}"


def atualizar_modelo(
    id_modelo,
    modulo,
    manual,
    capitulo,
    montadora,
    modelo,
):
    try:
        dados = {
            "modulo": limpar_texto(modulo),
            "manual": limpar_texto(manual),
            "capitulo": limpar_texto(capitulo),
            "montadora": limpar_texto(montadora),
            "modelo": limpar_texto(modelo),
            "updated_at": datetime.now().isoformat(),
        }

        (
            supabase
            .table("modelos")
            .update(dados)
            .eq("id", id_modelo)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Modelo atualizado com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao atualizar modelo")
        return False, f"❌ Erro ao atualizar modelo: {erro}"


def deletar_modelo(id_modelo):
    try:
        (
            supabase
            .table("modelos")
            .delete()
            .eq("id", id_modelo)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Modelo excluído com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao excluir modelo")
        return False, f"❌ Erro ao excluir modelo: {erro}"


# ================================================================
# CAPÍTULOS
# ================================================================

def inserir_capitulo(
    manual,
    capitulo,
    usado_na_demanda,
):
    try:
        dados = {
            "manual": limpar_texto(manual),
            "capitulo": limpar_texto(capitulo),
            "usado_na_demanda": limpar_texto(
                usado_na_demanda
            ),
        }

        supabase.table("capitulos").insert(dados).execute()
        invalidar_cache()

        return True, "✅ Capítulo salvo com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao inserir capítulo")
        return False, f"❌ Erro ao salvar capítulo: {erro}"


def atualizar_capitulo(
    id_capitulo,
    manual,
    capitulo,
    usado_na_demanda,
):
    try:
        dados = {
            "manual": limpar_texto(manual),
            "capitulo": limpar_texto(capitulo),
            "usado_na_demanda": limpar_texto(
                usado_na_demanda
            ),
            "updated_at": datetime.now().isoformat(),
        }

        (
            supabase
            .table("capitulos")
            .update(dados)
            .eq("id", id_capitulo)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Capítulo atualizado com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao atualizar capítulo")
        return False, f"❌ Erro ao atualizar capítulo: {erro}"


def deletar_capitulo(id_capitulo):
    try:
        (
            supabase
            .table("capitulos")
            .delete()
            .eq("id", id_capitulo)
            .execute()
        )

        invalidar_cache()

        return True, "✅ Capítulo excluído com sucesso!"

    except Exception as erro:
        logger.exception("Erro ao excluir capítulo")
        return False, f"❌ Erro ao excluir capítulo: {erro}"

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
    "MASSEY FERGUSON", "NEW HOLLAND", "MAXION-PERKINS", "CASE", "IVECO/VOLKSWAGEN", "HYUNDAI/KIA",
    "AUDI/VOLKSWAGEN", "LAND ROVER/JAGUAR", "CITROEN/PEUGEOT", "RAM/JEEP", "CITROEN/FIAT/JEEP/PEUGEOT",
    "FIAT/CITROEN/PEUGEOT", "FIAT/JEEP", "FORD/VOLKSVAGEN", "FIAT/RAM", "FIAT/PEUGEOT"
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