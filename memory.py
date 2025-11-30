import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None

print(f"🔌 [MEMORY] Iniciando conexão Supabase...")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ [MEMORY] ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas no .env")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ [MEMORY] Cliente Supabase criado.")
    except Exception as e:
        print(f"❌ [MEMORY] Erro fatal ao conectar no Supabase: {e}")
        supabase = None

# --- FUNÇÕES DE MEMÓRIA (MENSAGENS) ---

def save_message(user_id: str, role: str, content: str):
    """Salva uma mensagem no histórico."""
    # Debug para saber se a função foi chamada
    print(f"💾 [MEMORY] Tentando salvar mensagem de {user_id} ({role})...")
    
    if not supabase: 
        print("❌ [MEMORY] Erro: Cliente Supabase não está conectado. Mensagem perdida.")
        return

    try:
        data = {
            "user_id": str(user_id),
            "role": role, 
            "content": content
        }
        # Tenta inserir e captura resposta
        response = supabase.table("memory").insert(data).execute()
        print(f"✅ [MEMORY] Mensagem salva com sucesso! ID: {user_id}")
    except Exception as e:
        print(f"❌ [MEMORY] Erro ao salvar no banco: {e}")

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
            # Proteção contra conteúdo vazio
            content = msg.get("content") or ""
            formatted_history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [content]
            })
            
        return formatted_history
    except Exception as e:
        print(f"⚠️ [MEMORY] Erro ao buscar memória: {e}")
        return []

# --- FUNÇÕES DE USUÁRIO ---

def get_user_email(user_id: str):
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
    if not supabase: return
    try:
        data = {"user_id": str(user_id), "email": email}
        supabase.table("users").upsert(data).execute()
        print(f"👤 [USER] Usuário salvo/atualizado: {email}")
    except Exception as e:
        print(f"⚠️ Erro ao registrar usuário: {e}")
