import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# Configuração do OAuth
# ATENÇÃO: A URL de callback deve ser EXATAMENTE igual à cadastrada no Google Cloud
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000") # Render define essa var automaticamente
REDIRECT_URI = f"{RENDER_URL}/auth/callback"

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]
# No arquivo auth.py

def get_google_auth_flow():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    # --- DEBUG (O Dedo-Duro) ---
    # Isso vai mostrar no log do Render se ele está lendo ou não
    # Ele mostra só os 5 primeiros caracteres para não vazar a senha toda
    print(f"🕵️ DEBUG AUTH: ID lido? {client_id[:5]}... | Secret lido? {client_secret[:5]}...")
    
    if not client_id or not client_secret:
        raise ValueError("ERRO: As variáveis GOOGLE_CLIENT_ID ou SECRET estão vazias/None!")
    # ---------------------------

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    # ... resto do código igual ...

def get_google_auth_flow():
    """Cria o fluxo de autenticação com as credenciais do ambiente."""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def save_user_credentials(user_id: str, credentials):
    """Salva as credenciais (token) do usuário no Supabase."""
    if not supabase: return False
    
    # Transforma o objeto Credentials em JSON string para salvar no banco
    creds_json = credentials.to_json()
    
    try:
        # Atualiza o usuário existente com as novas credenciais
        supabase.table("users").upsert({"credentials_json": creds_json}).eq("user_id", str(user_id)).execute()
        return True
    except Exception as e:
        print(f"Erro ao salvar credenciais: {e}")
        return False

def load_user_credentials(user_id: str):
    """Recupera as credenciais do usuário do banco e renova se necessário."""
    if not supabase: return None
    
    try:
        response = supabase.table("users").select("credentials_json").eq("user_id", str(user_id)).execute()
        if not response.data or not response.data[0]["credentials_json"]:
            return None
            
        creds_data = json.loads(response.data[0]["credentials_json"])
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        return creds
    except Exception as e:
        print(f"Erro ao carregar credenciais: {e}")

        return None
