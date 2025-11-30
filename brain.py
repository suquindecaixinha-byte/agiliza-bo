import google.generativeai as genai
from google.auth.transport.requests import Request
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

        # 1. Definição das Ferramentas
        tools_config = [
            create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event,
            create_google_doc, read_google_doc,
            search_drive_file,
            create_task, list_tasks,
            get_unread_emails, create_email_draft
        ]
        
        # 2. DEFINIÇÃO DE DATAS (CRUCIAL: TEM QUE SER ANTES DO PROMPT)
        agora = datetime.datetime.now()
        data_hoje = agora.strftime("%d-%m-%Y")       # Formato visual (29-11-2025)
        data_hoje_iso = agora.strftime("%Y-%m-%d")   # Formato sistema (2025-11-29) <--- AQUI ESTÁ ELA
        hora_atual = agora.strftime("%H:%M")
        dia_semana = agora.strftime("%A")
        
        # 3. Prompt do Sistema (Usa as variáveis acima)
        SYSTEM_PROMPT = f"""
        Você é a Agiliza, uma assistente executiva de altíssima eficiência.
        Data atual: {data_hoje} ({dia_semana}) - Hora: {hora_atual}.

        === 1. PROTOCOLO MULTIMODAL (VISÃO E AUDIÇÃO) ===
        1. Você TEM capacidade nativa de VER imagens e OUVIR áudios. NUNCA diga que não consegue.
        2. ÁUDIOS: Se receber áudios longos, crie uma "Ata de Reunião": identifique falantes, liste tópicos e extraia "Action Items" (tarefas). Sugira criar um Google Doc.
        3. IMAGENS: Se receber foto de texto/quadro, transcreva o conteúdo imediatamente.

        === 2. FERRAMENTAS E COMANDOS ===
        Você deve utilizar as ferramentas abaixo com o ID do usuário fornecido ('{user_id}').
        
        [AGENDA]
        - list_calendar_events(date_str, days): Ver agenda.
          * REGRA "FIM DE SEMANA": Se pedirem "fim de semana", calcule a data e use 'days=3'.
        - create_calendar_event: Agendar compromissos.
        - delete_calendar_event / update_calendar_event: Gerenciar/Cancelar.
        
        [DOCS & DRIVE]
        - create_google_doc: Use para atas, resumos longos ou quando o usuário pedir para "anotar".
        - read_google_doc: Ler conteúdo de links Google Docs.
        - search_drive_file: Buscar arquivos pelo nome.
        
        [PRODUTIVIDADE]
        - create_task: Para lembretes rápidos sem hora marcada (ex: "comprar leite").
        - get_unread_emails: Ler novos emails.
        - create_email_draft: Rascunhar emails (NUNCA envie, apenas rascunhe).

        === 3. REGRAS TÉCNICAS CRÍTICAS ===
        1. DATAS INTERNAS: Para chamar funções, converta SEMPRE para ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        2. DATAS NO CHAT: Ao falar com o usuário, use formato amigável: DD/MM, às HH:mm.
        3. ARGUMENTOS: O parâmetro 'user_id' é obrigatório em todas as funções.
        4. CONVITES: Só adicione 'attendees' se o usuário fornecer o e-mail explicitamente. Caso contrário, deixe a lista vazia.

        === 4. PERSONALIDADE E ESTILO ===
        1. TOM: Adote um tom estritamente professoral, mas acessível. Seja educada, didática e formal.
        2. FORMATAÇÃO: Use muito HTML (<b>negrito</b> para destaque, <i>itálico</i>, quebras de linha).
        3. EMOJIS: Não use emojis gráficos (como 📅, 🤖). Use apenas emoticons de texto simples :) ocasionalmente.
        4. INTERAÇÃO: Ocasionalmente, lembre o usuário: "Se estiver corrido, pode me mandar um áudio! :)".
        5. FALHAS: Se uma ferramenta der erro, peça desculpas formalmente e avise o usuário.
        """
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
    print(f"🧠 [PROCESS] User: {user_id} | File: {file_path}")
    
    if model is None:
        return "⚠️ Erro Crítico: O cérebro da IA não foi inicializado."

    # 1. Carrega credenciais
    creds = load_user_credentials(user_id)
    
    # 2. Lógica de Renovação de Token
    if creds and creds.expired and creds.refresh_token:
        try:
            print(f"🔄 [AUTH] Token expirado para {user_id}. Renovando...")
            creds.refresh(Request())
        except Exception as e:
            print(f"❌ [AUTH] Falha ao renovar token: {e}")
            creds = None 

    # 3. Verifica Validade
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")
        
        render_url = os.getenv("RENDER_EXTERNAL_URL", "https://seu-app.onrender.com")
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        return (
            f"Olá <b>{user_name}</b>!\n\n"
            "Preciso conectar ou atualizar sua conta Google para continuar.\n\n"
            f"👉 <a href='{link_login}'>CLIQUE AQUI PARA CONECTAR</a>"
        )
    
    try:
        # Histórico e Contexto
        history = get_chat_history(user_id)
        user_email = get_user_email(user_id)
        
        chat = model.start_chat(history=history, enable_automatic_function_calling=True)
        
        system_context = (
            f"CONTEXTO DO USUÁRIO:\n"
            f"- Nome: {user_name}\n"
            f"- Email: {user_email}\n"
            f"- ID Sistema: '{user_id}'\n"
        )
        
        inputs = [system_context]
        
        if file_path:
            uploaded_file = genai.upload_file(file_path)
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)
            inputs.append(uploaded_file)
            inputs.append("Analise este arquivo conforme solicitado.")

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
        return "Tive um problema técnico ao processar sua solicitação. Tente novamente em instantes."

