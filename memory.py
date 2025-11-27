import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# BUSCA AS CHAVES DAS VARIÁVEIS DE AMBIENTE (MAIS SEGURO)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas.")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Erro fatal ao conectar no Supabase: {e}")
        supabase = None

def save_message(user_id: str, role: str, content: str):
    """Salva uma mensagem no banco."""
    if not supabase: return
    try:
        data = {
            "user_id": str(user_id),
            "role": role, 
            "content": content
        }
        supabase.table("memory").insert(data).execute()
        print(f"💾 [MEMÓRIA] Mensagem salva ({role})")
    except Exception as e:
        print(f"⚠️ Erro ao salvar memória: {e}")

def get_chat_history(user_id: str, limit=10):
    """Busca as últimas mensagens."""
    if not supabase: return []
    try:
        response = supabase.table("memory")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        messages = response.data[::-1]
        
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