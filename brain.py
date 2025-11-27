import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO: Chaves do Supabase não encontradas no .env")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro fatal ao conectar no Supabase: {e}")
    supabase = None

# --- FUNÇÕES DE USUÁRIO (NOVO) ---
def get_user_email(telegram_id: str):
    """Busca o email do usuário pelo ID do Telegram."""
    if not supabase: return None
    try:
        # Cria a tabela users se não existir (apenas segurança)
        # Idealmente rode o SQL no painel do Supabase:
        # create table users (telegram_id text primary key, email text);
        
        response = supabase.table("users").select("email").eq("telegram_id", str(telegram_id)).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]['email']
        return None
    except Exception as e:
        print(f"⚠️ Erro ao buscar usuário: {e}")
        return None

def register_user(telegram_id: str, email: str):
    """Salva um novo usuário no banco."""
    if not supabase: return False
    try:
        data = {"telegram_id": str(telegram_id), "email": email.strip().lower()}
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        print(f"⚠️ Erro ao registrar usuário: {e}")
        return False

# --- FUNÇÕES DE MEMÓRIA (MANTIDAS) ---
def save_message(user_id: str, role: str, content: str):
    if not supabase: return
    try:
        data = {"user_id": str(user_id), "role": role, "content": content}
        supabase.table("memory").insert(data).execute()
    except Exception as e:
        print(f"⚠️ Erro ao salvar memória: {e}")

def get_chat_history(user_id: str, limit=10):
    if not supabase: return []
    try:
        response = supabase.table("memory")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        formatted_history = []
        for msg in response.data[::-1]:
            formatted_history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [msg["content"]]
            })
        return formatted_history
    except Exception as e:
        return []
