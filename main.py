import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from brain import process_ai_request
from auth import get_google_auth_flow, save_user_credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from memory import register_user 

load_dotenv()

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# --- FUNÇÕES AUXILIARES TELEGRAM ---
async def send_telegram_message(chat_id, text):
    """Envia mensagem com proteção contra falhas de rede."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML", 
                "disable_web_page_preview": True 
            })
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")

async def download_telegram_file(file_id):
    """Baixa arquivos detectando a extensão correta da API do Telegram."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Pega o caminho do arquivo
        resp = await client.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        if resp.status_code != 200: return None
        
        file_path_info = resp.json()['result']['file_path']
        
        # 2. Extrai a extensão real (ex: .jpg, .oga, .mp3)
        _, file_extension = os.path.splitext(file_path_info)
        
        # 3. Baixa o binário
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path_info}"
        file_content = await client.get(download_url)
        
        # 4. Salva temporariamente
        temp_filename = f"temp_{file_id}{file_extension}" 
        with open(temp_filename, "wb") as f:
            f.write(file_content.content)
            
        return temp_filename

# --- ROTAS ---

@app.get("/")
async def root():
    return {"status": "Agiliza Bot V3 (Multimodal) Online"}

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
        return "Erro: Parâmetros inválidos."

    try:
        flow = get_google_auth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        user_email = user_info.get('email')

        # Salva credenciais e usuário
        save_user_credentials(user_id, creds)
        register_user(user_id, user_email) 

        # --- MENSAGEM DE BOAS-VINDAS PERSONALIZADA ---
        msg_sucesso = (
            f"✅ <b>Conectado como:</b> {user_email}\n\n"
            "<b>Pronto para agilizar! Experimente agora:</b>\n\n"
            "1️⃣ <b>Agenda:</b> Pergunte <i>'Como está minha agenda amanhã?'</i>\n"
            "2️⃣ <b>Áudio:</b> Envie uma gravação longa e peça <i>'Faça uma ata disto.'</i>\n"
            "3️⃣ <b>Visão:</b> Mande foto de um documento e diga <i>'Transcreva para mim.'</i>"
        )
        # ---------------------------------------------

        await send_telegram_message(user_id, msg_sucesso)
        return f"Sucesso! Conectado como {user_email}. Pode fechar esta janela."

    except Exception as e:
        return f"Erro Auth: {str(e)}"

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error_json"}

    if "message" not in data: return {"status": "ignored"}
    
    message = data["message"]
    chat_id = message["chat"]["id"]
    user_text = message.get("text") or message.get("caption") or ""
    first_name = message.get("from", {}).get("first_name", "")

    # Detecção de Arquivos
    file_id = None
    if message.get("voice"):       file_id = message["voice"]["file_id"]
    elif message.get("audio"):     file_id = message["audio"]["file_id"]
    elif message.get("photo"):     file_id = message["photo"][-1]["file_id"] # Pega a maior resolução
    elif message.get("document"):  
        # Segurança: Só aceita documentos se forem imagem ou áudio
        mime = message["document"].get("mime_type", "")
        if "image" in mime or "audio" in mime:
            file_id = message["document"]["file_id"]

    temp_file = None
    
    try:
        # Avisa que está "escrevendo/gravando" para o usuário não achar que travou
        async with httpx.AsyncClient() as client:
            action = "upload_document" if file_id else "typing"
            await client.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": action})

        if file_id:
            temp_file = await download_telegram_file(file_id)
            if not user_text: user_text = "[Arquivo Anexado]"

        # Processamento Inteligente
        ai_response = process_ai_request(user_text, str(chat_id), first_name, temp_file)
        
        await send_telegram_message(chat_id, ai_response)

    except Exception as e:
        print(f"❌ Erro Webhook: {e}")
        await send_telegram_message(chat_id, "⚠️ Tive um problema técnico interno. Tente novamente em instantes.")
    
    finally:
        # Limpeza obrigatória para não encher o disco do Render
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

    return {"status": "ok"}
