import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Erro Supabase Auth: {e}")

# Configuração do OAuth
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000") 
REDIRECT_URI = f"{RENDER_URL}/auth/callback"

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def get_google_auth_flow():
    """Cria o fluxo de autenticação."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("ERRO: Variáveis GOOGLE_CLIENT_ID ou SECRET não configuradas.")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
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
    
    creds_json = credentials.to_json()
    
    try:
        # --- CORREÇÃO: Usar 'upsert' de verdade ---
        data = {
            "user_id": str(user_id),
            "credentials_json": creds_json
        }
        # Upsert cria se não existe, atualiza se existe.
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Erro ao salvar credenciais: {e}")
        return False

def load_user_credentials(user_id: str):
    """Recupera as credenciais do usuário do banco."""
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
