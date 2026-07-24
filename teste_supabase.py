import os

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise RuntimeError(
        "Defina SUPABASE_URL e SUPABASE_KEY no arquivo .env"
    )

url = url.strip().rstrip("/")

if "/rest/v1" in url:
    raise RuntimeError(
        "A URL não pode conter /rest/v1"
    )

cliente = create_client(url, key)

resposta = (
    cliente
    .table("demandas")
    .select("*")
    .limit(1)
    .execute()
)

print("Conexão realizada com sucesso.")
print(f"Registros encontrados: {len(resposta.data or [])}")