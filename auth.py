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

# Blindagem contra erro de conexão no Supabase
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Erro Supabase Auth: {e}")

# Configuração do OAuth
# ATENÇÃO: A URL deve ser exata (sem barra no final se configurou assim no Google)
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000") 
REDIRECT_URI = f"{RENDER_URL}/auth/callback"

# --- A CORREÇÃO ESTÁ AQUI EMBAIXO ---
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.email' # <--- O ESCOPO QUE FALTAVA
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
        # Usamos upsert para garantir que crie ou atualize
        # Nota: Aqui salvamos apenas o token. O email salvamos no main.py via register_user
        supabase.table("users").update({"credentials_json": creds_json}).eq("user_id", str(user_id)).execute()
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
