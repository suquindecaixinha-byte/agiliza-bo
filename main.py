import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from brain import process_ai_request
from auth import get_google_auth_flow, save_user_credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from memory import register_user # Importação necessária

load_dotenv()

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# --- FUNÇÕES AUXILIARES TELEGRAM ---
async def send_telegram_message(chat_id, text):
    """Envia mensagem de texto de volta para o Telegram usando MarkdownV2."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2", # <--- AQUI ESTÁ A MUDANÇA
            "disable_web_page_preview": True # Evita prévia de links do Google
        })

async def download_telegram_file(file_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        file_path_info = resp.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path_info}"
        file_content = await client.get(download_url)
        
        temp_filename = f"temp_{file_id}.ogg" 
        with open(temp_filename, "wb") as f:
            f.write(file_content.content)
        return temp_filename

# --- ROTAS DO SISTEMA ---

@app.get("/")
async def root():
    return {"message": "Agiliza Bot (OAuth2 + MarkdownV2) rodando!"}

@app.get("/auth/login")
async def login(state: str):
    flow = get_google_auth_flow()
    authorization_url, _ = flow.authorization_url(prompt='consent', state=state)
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    user_id = request.query_params.get("state")
    
    if not code or not user_id:
        return "Erro: Falta código ou ID do usuário."

    try:
        flow = get_google_auth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        user_email = user_info.get('email')

        save_user_credentials(user_id, creds)
        register_user(user_id, user_email) 

        # Mensagem de sucesso escapada para MarkdownV2
        msg_sucesso = f"✅ *Conectado como:* {user_email}\nAgora pode me pedir para agendar coisas\!"
        await send_telegram_message(user_id, msg_sucesso)
        
        return f"Sucesso! Conectado como {user_email}. Pode fechar esta janela."

    except Exception as e:
        return f"Erro na autenticação: {str(e)}"

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    if "message" not in data: return {"status": "ignored"}
    
    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")
    voice_info = data["message"].get("voice") or data["message"].get("audio")
    
    temp_file = None
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

        if voice_info:
            temp_file = await download_telegram_file(voice_info["file_id"])
            user_text = user_text or ""

        ai_response = process_ai_request(user_text, str(chat_id), temp_file)
        await send_telegram_message(chat_id, ai_response)

    except Exception as e:
        print(f"❌ Erro no servidor: {e}")
        # Mensagem de erro simples sem caracteres especiais para não quebrar
        await send_telegram_message(chat_id, "Tive um erro interno no servidor")
    
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

    return {"status": "ok"}
