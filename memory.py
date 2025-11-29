import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ AVISO: Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas.")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Erro fatal ao conectar no Supabase: {e}")
        supabase = None

# --- FUNÇÕES DE MEMÓRIA (MENSAGENS) ---

def save_message(user_id: str, role: str, content: str):
    """Salva uma mensagem no histórico."""
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
    """Busca as últimas mensagens para contexto."""
    if not supabase: return []
    try:
        response = supabase.table("memory")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        messages = response.data[::-1] # Inverte para ordem cronológica
        
        formatted_history = []
        for msg in messages:
            formatted_history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [msg["content"]]
            })
            
        return formatted_history
    except Exception as e:
        print(f"⚠️ Erro ao buscar memória: {e}")
        return []

# --- FUNÇÕES DE USUÁRIO (AS QUE ESTAVAM FALTANDO) ---

def get_user_email(user_id: str):
    """Verifica qual e-mail está atrelado a este usuário."""
    if not supabase: return None
    try:
        response = supabase.table("users").select("email").eq("user_id", str(user_id)).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["email"]
        return None
    except Exception as e:
        print(f"⚠️ Erro ao buscar usuário: {e}")
        return None

def register_user(user_id: str, email: str):
    """
    Cadastra ou ATUALIZA um usuário.
    Crucial para quando o usuário sai de 'pendente_login' para o email real.
    """
    if not supabase: return
    try:
        # 'upsert' cria se não existir, ou atualiza se já existir
        data = {"user_id": str(user_id), "email": email}
        supabase.table("users").upsert(data).execute()
        print(f"👤 [USER] Usuário salvo/atualizado: {email}")
    except Exception as e:
        print(f"⚠️ Erro ao registrar usuário: {e}")
        
def clear_memory(user_id: str):
    """Apaga o histórico de conversa do usuário."""
    if not supabase: return
    try:
        supabase.table("memory").delete().eq("user_id", str(user_id)).execute()
    except Exception as e:
        print(f"Erro ao limpar memória: {e}")

