import os
from supabase import create_client, Client

# --- COLE SUAS CHAVES DO SUPABASE AQUI (DIRETO NO CÓDIGO) ---
# Copie do site do Supabase > Project Settings > API
SUPABASE_URL = "https://siojuuwsskjscdxgrtea.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNpb2p1dXdzc2tqc2NkeGdydGVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwNzY4MTMsImV4cCI6MjA3OTY1MjgxM30.ps94duCBq_7h09e1_s4VXINh1yJmbI9yFyO3dPYXDes"
# ------------------------------------------------------------

# Tratamento de erro caso você esqueça de preencher
if "SEU_PROJETO" in SUPABASE_URL:
    print("❌ ERRO: Você esqueceu de colar a URL do Supabase no arquivo memory.py!")

try:
    # O .strip() remove espaços invisíveis que causam erro
    supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
except Exception as e:
    print(f"❌ Erro fatal ao conectar no Supabase: {e}")
    # Cria um cliente 'falso' só para o código não quebrar na importação, 
    # mas avisará no terminal se tentar usar.
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