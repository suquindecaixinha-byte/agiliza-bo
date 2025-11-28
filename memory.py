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
    # O .strip() remove espaços invisíveis que causam erro
    supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
except Exception as e:
    print(f"❌ Erro fatal ao conectar no Supabase: {e}")
    supabase = None

# --- FUNÇÕES DE AUTENTICAÇÃO OAUTH (NOVO) ---

def register_user_token(telegram_id: str, creds_json: dict, email: str = "autenticado_via_oauth"):
    """
    Salva as credenciais OAuth do Google (Token) no banco de dados.
    Isso permite que o bot acesse a agenda em nome do usuário.
    """
    if not supabase: return False
    try:
        # Prepara os dados para salvar/atualizar
        data = {
            "telegram_id": str(telegram_id),
            "google_token": creds_json, # O Supabase salva o dict como JSONB automaticamente
            "email": email 
        }
        
        # Upsert: Se já existe, atualiza o token. Se não, cria novo.
        supabase.table("users").upsert(data).execute()
        print(f"🔐 [AUTH] Token salvo para o usuário {telegram_id}")
        return True
    except Exception as e:
        print(f"⚠️ Erro ao salvar token OAuth: {e}")
        return False

def get_user_token(telegram_id: str):
    """
    Recupera o JSON do token OAuth para reconstruir as credenciais.
    """
    if not supabase: return None
    try:
        response = supabase.table("users")\
            .select("google_token")\
            .eq("telegram_id", str(telegram_id))\
            .execute()
            
        if response.data and len(response.data) > 0:
            # Retorna o dicionário do token
            return response.data[0]['google_token']
        return None
    except Exception as e:
        print(f"⚠️ Erro ao buscar token: {e}")
        return None

# --- FUNÇÕES DE MEMÓRIA (MANTIDAS) ---

def save_message(user_id: str, role: str, content: str):
    """Salva o histórico da conversa."""
    if not supabase: return
    try:
        data = {
            "user_id": str(user_id),
            "role": role, 
            "content": content
        }
        supabase.table("memory").insert(data).execute()
    except Exception as e:
        print(f"⚠️ Erro ao salvar memória: {e}")

def get_chat_history(user_id: str, limit=10):
    """Recupera o contexto para o Gemini."""
    if not supabase: return []
    try:
        response = supabase.table("memory")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        formatted_history = []
        # Inverte para ordem cronológica (Antigo -> Novo)
        for msg in response.data[::-1]:
            formatted_history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [msg["content"]]
            })
        return formatted_history
    except Exception as e:
        print(f"⚠️ Erro ao buscar histórico: {e}")
        return []