import google.generativeai as genai
from tools import (
    create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event,
    create_google_doc, read_google_doc,
    search_drive_file,
    create_task, list_tasks,
    get_unread_emails, create_email_draft
)
from memory import save_message, get_chat_history, get_user_email, register_user
from auth import load_user_credentials
import os
import datetime
import time
from dotenv import load_dotenv

load_dotenv()

# --- INICIALIZAÇÃO GEMINI ---
model = None

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERRO CRÍTICO: GOOGLE_API_KEY não encontrada no .env")
    else:
        genai.configure(api_key=api_key)
        
        # Ferramentas que a IA pode usar
        tools_config = [
            create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event,
            create_google_doc, read_google_doc,
            search_drive_file,
            create_task, list_tasks,
            get_unread_emails, create_email_draft
        ] # <--- O ERRO ESTAVA AQUI (FALTAVA FECHAR A LISTA)
        
        # --- DEFINIÇÃO DE DATAS ---
        agora = datetime.datetime.now()
        data_hoje = agora.strftime("%d-%m-%Y")       
        data_hoje_iso = agora.strftime("%Y-%m-%d")   
        hora_atual = agora.strftime("%H:%M")
        dia_semana = agora.strftime("%A")
        
        # --- PROMPT DO SISTEMA ---
        SYSTEM_PROMPT = f"""
        Você é a Agiliza, uma assistente executiva de altíssima eficiência.
        Data atual: {data_hoje} ({dia_semana}) - Hora: {hora_atual}.

        PROTOCOLO OBRIGATÓRIO (ANTI-RECUSA):
        1. Você TEM capacidade nativa de VER imagens e OUVIR áudios enviados.
        2. NUNCA responda "não consigo acessar arquivos" ou "não consigo ouvir".
        3. Se receber um arquivo, assuma imediatamente que você consegue processá-lo.
        
        CAPACIDADES MULTIMODAIS:
        1. Você pode ouvir áudios longos e ver imagens.
        2. Se receber áudio longo e pedirem "Resumo" ou "Ata": Identifique falantes, liste tópicos e action items.
        3. Imagem de texto: Transcreva.
    
        FERRAMENTAS DISPONÍVEIS:
        1. list_calendar_events(date_str, days):
           - Se perguntarem "fim de semana", calcule a data do sábado e use days=2.
        2. create_calendar_event: Data em ISO (YYYY-MM-DDTHH:MM:SS).
        3. create_google_doc: Para atas e resumos longos.
    
        DIRETRIZES:
        - Use HTML (<b>, <i>).
        - Use formato DD-MM-AA, às HH:MM no chat.
        - Data interna sempre ISO.
        - Argumento 'user_id' é obrigatório.
        - Não use emojis gráficos, apenas texto :).
        """
        
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-001',
            tools=tools_config,
            system_instruction=SYSTEM_PROMPT
        )
        print("✅ [BRAIN] Modelo Gemini inicializado com sucesso.")

except Exception as e:
    print(f"❌ Erro Fatal Brain Init: {e}")


def process_ai_request(user_text: str, user_id: str, user_name: str, file_path=None):
    """Processa texto + arquivo (imagem/audio) usando Gemini."""
    print(f"🧠 [PROCESS] User: {user_id} | File: {file_path}")
    
    if model is None:
        return "⚠️ Erro Crítico: O cérebro da IA não foi inicializado."

    creds = load_user_credentials(user_id)
    
    # Verifica Login
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")
        
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        if not render_url: render_url = "https://seu-app.onrender.com" 
        
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        return (
            f"Olá <b>{user_name}</b>!\n\n"
            "Para gerenciar sua agenda, conecte sua conta Google.\n\n"
            f"👉 <a href='{link_login}'>CLIQUE AQUI PARA CONECTAR</a>"
        )
    
    try:
        history = get_chat_history(user_id)
        user_email = get_user_email(user_id)
        
        chat = model.start_chat(history=history, enable_automatic_function_calling=True)
        
        system_context = (
            f"CONTEXTO DO USUÁRIO:\n"
            f"- Nome: {user_name}\n"
            f"- Email: {user_email}\n"
            f"- ID Sistema: '{user_id}' (Use este ID nas ferramentas)\n"
        )
        
        inputs = [system_context]
        
        if file_path:
            print(f"📤 Uploading file: {file_path}")
            uploaded_file = genai.upload_file(file_path)
            
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)
                
            inputs.append(uploaded_file)
            inputs.append("⚠️ O arquivo acima é a mensagem do usuário. Processe-o.")

        if user_text:
            inputs.append(user_text)

        response = chat.send_message(inputs)
        text_response = response.text
        
        log_content = f"[Arquivo] {user_text}" if file_path else user_text
        save_message(user_id, "user", log_content)
        save_message(user_id, "model", text_response)
        
        return text_response

    except Exception as e:
        print(f"❌ Erro AI: {e}")
        return "Tive um problema técnico ao processar sua solicitação. Tente novamente."