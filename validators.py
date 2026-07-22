import re
import logging
import pandas as pd
from config_supabase import carregar_dados_demandas, carregar_dados_modelos, carregar_dados_capitulos

logger = logging.getLogger(__name__)

# --- VALIDADORES DE FORMATO ---

def validar_capitulo_formato(capitulo):
    """
    Valida formato do capítulo.
    Formato esperado: número + letra opcional (ex: 53, 53A, 53AB)
    """
    capitulo = str(capitulo).strip()

    if not capitulo:
        return False, "Capítulo não pode estar vazio"

    # Padrão: começa com número, pode ter letras depois
    if not re.match(r'^\d+[A-Z]*$', capitulo):
        return False, f"Formato inválido: '{capitulo}'. Use formato como '53' ou '53A'"

    return True, "✅ Formato válido"


def validar_versao_formato(versao):
    """
    Valida formato da versão.
    Formato esperado: AAAA/N ou AAAA/N X (ex: 2026/1, 2026/1 T, 2026/1 H&E)
    """
    versao = str(versao).strip()

    if not versao:
        return False, "Versão não pode estar vazia"

    # Padrão: AAAA/N ou AAAA/N X
    if not re.match(r'^\d{4}/[1-3](\s[A-Z&]+)?$', versao):
        return False, f"Formato inválido: '{versao}'. Use formato como '2026/1' ou '2026/1 T'"

    return True, "✅ Formato válido"


def validar_data_formato(data_str):
    """
    Valida formato de data.
    Aceita: DD/MM/YYYY ou YYYY-MM-DD
    """
    data_str = str(data_str).strip()

    if not data_str:
        return False, "Data não pode estar vazia"

    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y']

    for fmt in formatos:
        try:
            pd.to_datetime(data_str, format=fmt)
            return True, "✅ Data válida"
        except ValueError:
            continue

    return False, f"Formato de data inválido: '{data_str}'. Use DD/MM/YYYY ou YYYY-MM-DD"


# --- VALIDADORES DE CAMPO ---

def validar_campo_obrigatorio(valor, nome_campo):
    """
    Valida se um campo obrigatório está preenchido.
    """
    valor = str(valor).strip()

    if not valor or valor == "":
        return False, f"{nome_campo} é obrigatório"

    return True, "✅ Campo preenchido"


def validar_comprimento_campo(valor, min_length=1, max_length=255, nome_campo="Campo"):
    """
    Valida o comprimento de um campo.
    """
    valor = str(valor).strip()

    if len(valor) < min_length:
        return False, f"{nome_campo} deve ter no mínimo {min_length} caractere(s)"

    if len(valor) > max_length:
        return False, f"{nome_campo} deve ter no máximo {max_length} caractere(s)"

    return True, "✅ Comprimento válido"


# --- VALIDADORES GERAIS ---

def validar_demanda_completa(demanda, tipo, modulo, manual, data, capitulo, montadora, versao):
    """
    Valida todos os campos de uma demanda.
    """
    erros = []

    # Campos obrigatórios
    campos_obrigatorios = {
        "Demanda": demanda,
        "Tipo": tipo,
        "Módulo": modulo,
        "Manual": manual,
        "Data": data,
        "Capítulo": capitulo,
        "Montadora": montadora,
        "Versão": versao
    }

    for nome, valor in campos_obrigatorios.items():
        valido, msg = validar_campo_obrigatorio(valor, nome)
        if not valido:
            erros.append(msg)

    # Validações de formato
    valido, msg = validar_capitulo_formato(capitulo)
    if not valido:
        erros.append(msg)

    valido, msg = validar_versao_formato(versao)
    if not valido:
        erros.append(msg)

    valido, msg = validar_data_formato(data)
    if not valido:
        erros.append(msg)

    if erros:
        return False, erros

    return True, []


def validar_modelo_completo(modulo, manual, capitulo, montadora, modelo):
    """
    Valida todos os campos de um modelo.
    """
    erros = []

    # Campos obrigatórios
    campos_obrigatorios = {
        "Módulo": modulo,
        "Manual": manual,
        "Capítulo": capitulo,
        "Montadora": montadora,
        "Modelo": modelo
    }

    for nome, valor in campos_obrigatorios.items():
        valido, msg = validar_campo_obrigatorio(valor, nome)
        if not valido:
            erros.append(msg)

    # Validação de formato
    valido, msg = validar_capitulo_formato(capitulo)
    if not valido:
        erros.append(msg)

    if erros:
        return False, erros

    return True, []