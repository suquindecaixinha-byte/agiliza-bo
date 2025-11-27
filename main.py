import os
import httpx
from fastapi import FastAPI, Request
from brain import process_ai_request
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

async def send_telegram_message(chat_id, text):
    """Envia mensagem de texto de volta para o Telegram."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })

async def download_telegram_file(file_id):
    """Obtém o link e baixa o arquivo do Telegram"""
    async with httpx.AsyncClient() as client:
        # 1. Pega o caminho do arquivo
        resp = await client.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        file_path_info = resp.json()['result']['file_path']
        
        # 2. Baixa o binário
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path_info}"
        file_content = await client.get(download_url)
        
        # 3. Salva temporariamente
        temp_filename = f"temp_{file_id}.ogg" 
        with open(temp_filename, "wb") as f:
            f.write(file_content.content)
        return temp_filename

@app.get("/")
async def root():
    return {"message": "O Bot está rodando! Vá para o Telegram."}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Verifica se é uma mensagem válida
    if "message" not in data:
        return {"status": "ignored"}
    
    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")
    voice_info = data["message"].get("voice") or data["message"].get("audio")
    
    temp_file = None
    
    try:
        # Notifica usuário que está "escrevendo..." (UX básica)
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

        # Se tiver áudio, baixa
        if voice_info:
            temp_file = await download_telegram_file(voice_info["file_id"])
            if not user_text:
                user_text = "" # Garante que não é None

        # --- MÁGICA ACONTECE AQUI (ATUALIZADO COM MEMÓRIA) ---
        # Agora passamos o chat_id (convertido para string) para a IA saber quem é o dono da memória
        ai_response = process_ai_request(user_text, str(chat_id), temp_file)
        # -----------------------------------------------------

        await send_telegram_message(chat_id, ai_response)

    except Exception as e:
        print(f"❌ Erro no servidor: {e}")
        await send_telegram_message(chat_id, "Desculpe, tive um erro interno.")
    
    finally:
        # Limpeza do arquivo temporário sempre acontece, dando erro ou não
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)


    return {"status": "ok"}

# (Pseudocódigo da lógica nova)
def verificar_usuario(chat_id, texto_usuario):
    # 1. Busca no Supabase se esse chat_id já existe na tabela 'users'
    usuario = supabase.table("users").select("email").eq("telegram_id", str(chat_id)).execute()
    
    # 2. Se NÃO existir (Usuário Novo):
    if not usuario.data:
        # Verifica se o texto parece um email
        if "@" in texto_usuario and "." in texto_usuario:
            # Salva o novo usuário!
            supabase.table("users").insert({"telegram_id": str(chat_id), "email": texto_usuario}).execute()
            return f"Cadastro realizado! Agora vá na sua Agenda Google e compartilhe o acesso com o email do meu robô: {EMAIL_DO_ROBO_SERVICE_ACCOUNT}"
        else:
            return "Olá! Para começar, preciso saber qual é o seu e-mail do Google Agenda. Por favor, digite apenas o e-mail."

    # 3. Se JÁ existir:
    return "ok" # Deixa a IA processar normal
