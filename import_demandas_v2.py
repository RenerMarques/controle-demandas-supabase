import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== FUNÇÃO PARA CONVERTER DATA ==========
def converter_data(data_str):
    """Converte data de DD/MM/YYYY para YYYY-MM-DD"""
    if not data_str or str(data_str).strip() == '':
        return None

    try:
        data_str = str(data_str).strip()

        # Se já está em formato YYYY-MM-DD, retorna
        if len(data_str) == 10 and data_str[4] == '-':
            return data_str

        # Tenta converter de DD/MM/YYYY
        if '/' in data_str:
            partes = data_str.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                # Valida se é data válida
                try:
                    int(dia)
                    int(mes)
                    int(ano)
                    return f"{ano.zfill(4)}-{mes.zfill(2)}-{dia.zfill(2)}"
                except:
                    return None

        return None
    except:
        return None

print("=" * 60)
print("IMPORTADOR DE DEMANDAS - GOOGLE SHEETS PARA SUPABASE")
print("=" * 60)

# ========== CREDENCIAIS SUPABASE - EDITE AQUI ==========
SUPABASE_URL = "https://evrgrcsczszmnltehhqn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2cmdyY3NjenN6bW5sdGVoaHFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2NzY1OTcsImV4cCI6MjEwMDI1MjU5N30.8-Zh3s2tX3zpyoyuyzWZEhXXbi0OAU_GOT3AOlpHGPQ"
NOME_TABELA = "demandas"
NOME_PLANILHA = "Controle de Demandas"

# ========== CARREGAR CREDENCIAIS DO ARQUIVO JSON ==========
print("\n🔗 Carregando credenciais do Google...")
try:
    with open('google-credentials.json', 'r') as f:
        GOOGLE_CREDENTIALS = json.load(f)
    print("✅ Credenciais carregadas!")
except FileNotFoundError:
    print("❌ Arquivo 'google-credentials.json' não encontrado!")
    exit(1)

# ========== CONECTAR AO GOOGLE SHEETS ==========
print("🔗 Conectando ao Google Sheets...")
try:
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_info(
        GOOGLE_CREDENTIALS,
        scopes=scope
    )

    client = gspread.authorize(credentials)
    print("✅ Conectado ao Google Sheets!")

except Exception as e:
    print(f"❌ Erro ao conectar ao Google Sheets: {str(e)}")
    exit(1)

# ========== IMPORTAR DEMANDAS ==========
print(f"\n📋 Importando DEMANDAS de '{NOME_PLANILHA}'...")
print("-" * 60)

try:
    # Abrir a planilha
    spreadsheet = client.open(NOME_PLANILHA)
    print(f"✅ Planilha aberta: {spreadsheet.title}")

    # Acessar Sheet1
    ws_demandas = spreadsheet.worksheet("Sheet1")
    print(f"✅ Aba encontrada: {ws_demandas.title}")

    # Obter todos os registros
    dados_demandas = ws_demandas.get_all_records()
    print(f"📊 Total de linhas na planilha: {len(dados_demandas)}")

    contador_importado = 0
    contador_erro = 0
    contador_duplicado = 0

    print("\nProcessando demandas...\n")

    # Preparar lista de dados para inserir
    dados_para_inserir = []

    for idx, row in enumerate(dados_demandas, 1):
        try:
            # Extrair dados
            demanda_raw = row.get('DEMANDA', '')
            demanda = str(demanda_raw).strip() if demanda_raw else ''

            # Pular linhas vazias
            if not demanda or demanda == '':
                continue

            # Preparar dados
            dados = {
                'demanda': demanda,
                'tipo': str(row.get('TIPO DEMANDA', '')).strip(),
                'modulo': str(row.get('MÓDULO', '')).strip(),
                'manual': str(row.get('MANUAL', '')).strip(),
                'data_linkagem': converter_data(row.get('DATA LINKAGEM', '')),
                'capitulo': str(row.get('CAPITULO', '')).strip(),
                'montadora': str(row.get('MONTADORA', '')).strip() if str(row.get('MONTADORA', '')).strip() else None,
                'versao': str(row.get('VERSÃO', '')).strip()
            }

            dados_para_inserir.append(dados)

            # Mostrar progresso a cada 100 linhas
            if idx % 100 == 0:
                print(f"  📍 Processadas {idx} linhas...")

        except Exception as e:
            contador_erro += 1
            logger.error(f"Erro na linha {idx}: {str(e)}")

    print(f"\n✅ {len(dados_para_inserir)} demandas preparadas para inserção")

    # ========== INSERIR NO SUPABASE ==========
    print(f"\n🚀 Inserindo dados no Supabase (tabela: {NOME_TABELA})...")
    print("-" * 60)

    if len(dados_para_inserir) > 0:
        url = f"{SUPABASE_URL}/rest/v1/{NOME_TABELA}"

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }

        try:
            # Inserir linha por linha (verificar se todos os campos são iguais)
            for idx, item in enumerate(dados_para_inserir, 1):
                try:
                    # Construir filtro para verificar se registro idêntico existe
                    filtro_parts = []
                    for chave, valor in item.items():
                        if valor is None:
                            filtro_parts.append(f"{chave}=is.null")
                        else:
                            # Escapar aspas e caracteres especiais
                            valor_escaped = str(valor).replace('"', '\\"')
                            filtro_parts.append(f'{chave}=eq."{valor_escaped}"')

                    filtro = ",".join(filtro_parts)

                    # Verificar se registro idêntico já existe
                    headers_check = headers.copy()
                    headers_check["Prefer"] = "count=exact"

                    response_check = requests.get(
                        f"{url}?{filtro}",
                        headers=headers_check,
                        timeout=10
                    )

                    # Se encontrou registro idêntico, pular
                    if response_check.status_code == 200:
                        content_range = response_check.headers.get("Content-Range", "0/0")
                        count = int(content_range.split("/")[1]) if "/" in content_range else 0

                        if count > 0:
                            contador_duplicado += 1
                            if idx % 100 == 0:
                                print(f"  📍 Processadas {idx} linhas... ({contador_importado} inseridas, {contador_duplicado} duplicadas)")
                            time.sleep(0.01)
                            continue

                    # Inserir se não encontrou idêntico
                    response = requests.post(url, json=[item], headers=headers, timeout=30)

                    if response.status_code in [200, 201]:
                        contador_importado += 1
                    else:
                        print(f"  ❌ Linha {idx}: ERRO {response.status_code}")
                        print(f"     Resposta: {response.text}")
                        contador_erro += 1

                    # Mostrar progresso a cada 100 linhas
                    if idx % 100 == 0:
                        print(f"  📍 Processadas {idx} linhas... ({contador_importado} inseridas, {contador_duplicado} duplicadas)")

                    time.sleep(0.01)  # Pequeno delay entre requisições

                except Exception as e:
                    print(f"  ❌ Linha {idx}: ERRO - {str(e)}")
                    contador_erro += 1

        except Exception as e:
            print(f"❌ Erro ao inserir dados: {str(e)}")
            contador_erro = len(dados_para_inserir)

    # ========== RESUMO ==========
    print("\n" + "=" * 60)
    print("RESUMO DA IMPORTAÇÃO")
    print("=" * 60)
    print(f"✅ Importadas: {contador_importado} demandas")
    print(f"⏭️  Duplicadas: {contador_duplicado} demandas")
    print(f"❌ Erros: {contador_erro} demandas")
    print(f"📊 Total processado: {contador_importado + contador_duplicado + contador_erro} linhas")
    print("=" * 60)

    if contador_importado > 0:
        print(f"\n🎉 Sucesso! {contador_importado} demandas foram importadas!")
    elif contador_duplicado > 0:
        print(f"\n⏭️  Todas as {contador_duplicado} demandas já existem na tabela.")
    else:
        print("\n⚠️  Nenhuma demanda foi importada.")

except Exception as e:
    print(f"\n❌ Erro geral: {str(e)}")
    logger.error(f"Erro geral: {str(e)}", exc_info=True)
    exit(1)