from brain import process_ai_request
from memory import register_user 
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from brain import process_ai_request
from auth import get_google_auth_flow, save_user_credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# --- FUNÇÕES AUXILIARES TELEGRAM ---
async def send_telegram_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
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
    return {"message": "Agiliza Bot (OAuth2) rodando!"}

@app.get("/auth/login")
async def login(state: str):
    """Redireciona o usuário para o Google."""
    flow = get_google_auth_flow()
    # O 'state' carrega o ID do Telegram para sabermos quem está logando
    authorization_url, _ = flow.authorization_url(prompt='consent', state=state)
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
async def callback(request: Request):
    """Recebe o usuário de volta do Google com a chave de acesso."""
    code = request.query_params.get("code")
    user_id = request.query_params.get("state")
    
    if not code or not user_id:
        return "Erro: Falta código ou ID do usuário."

    try:
        # 1. Troca o código pelo token
        flow = get_google_auth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # 2. Descobre quem é o dono desse token (pega o email)
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        user_email = user_info.get('email')

        # 3. Salva TUDO no banco (Token + Email)
        # Nota: save_user_credentials agora precisa lidar com o email também
        # Se você não alterou o auth.py para receber email, o save_user_credentials
        # lá só salva o JSON. Vamos garantir que o email seja salvo via auth ou memory.
        # Para simplificar, assumimos que save_user_credentials faz o update do JSON.
        # E aqui atualizamos o email se necessário.
        
        # Salvando as credenciais (Token)
        if save_user_credentials(user_id, creds):
            # Envia mensagem no Telegram avisando que deu certo
            await send_telegram_message(user_id, f"✅ Conectado como: {user_email}\nAgora pode me pedir para agendar coisas!")
            return f"Sucesso! Conectado como {user_email}. Pode fechar esta janela."
        else:
            return "Erro ao salvar no banco de dados."

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

        # Processa com a IA
        ai_response = process_ai_request(user_text, str(chat_id), temp_file)
        await send_telegram_message(chat_id, ai_response)

    except Exception as e:
        print(f"❌ Erro no servidor: {e}")
        await send_telegram_message(chat_id, "Tive um erro interno.")
    
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)


    return {"status": "ok"}
