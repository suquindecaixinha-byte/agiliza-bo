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
        
        tools_config = [
            create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event,
            create_google_doc, read_google_doc,
            search_drive_file,
            create_task, list_tasks,
            get_unread_emails, create_email_draft
        ]
        
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

        🛑 PROTOCOLO DE EXECUÇÃO (IMPORTANTE):
        1. Se o usuário pedir para criar algo (reunião, doc, tarefa) e você já tiver os dados necessários:
           - NÃO responda "Vou agendar" ou "Ok, criando".
           - EXECUTE A FUNÇÃO SILENCIOSAMENTE.
        2. Só responda DEPOIS que a ferramenta devolver o resultado (SYSTEM_INSTRUCTION).
        
        🚫 PROIBIDO ALUCINAR LINKS:
        1. Você é PROIBIDA de inventar links.
        2. Se você não executou a função 'create_calendar_event' (ou similar), O LINK NÃO EXISTE.
        3. Se você disser "Aqui está o link" sem ter rodado a ferramenta, você falhou.

        🔗 REGRA DE RETORNO:
        - Quando a ferramenta rodar, ela te dará um link real.
        - Copie e cole esse link na resposta final.

        📍 REGRA DE OURO - LINKS E URLS:
        1. Sempre que você criar algo (evento, doc, tarefa, rascunho), a ferramenta retornará um LINK.
        2. Você é OBRIGADA a mostrar esse LINK para o usuário na resposta final.
        3. NÃO diga apenas "Criei o documento". Diga: "Criei o documento. Aqui está o link: [LINK]".
        4. O link é a parte mais importante da sua resposta. === 3. REGRAS TÉCNICAS CRÍTICAS ===
        6. DATAS INTERNAS: Para chamar funções, converta SEMPRE para ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        7. DATAS NO CHAT: Ao falar com o usuário, use formato amigável: DD/MM, às HH:mm.
        8. CONVITES: Só adicione 'attendees' se o usuário fornecer o e-mail explicitamente. Caso contrário, deixe a lista vazia.

        CAPACIDADES:
        1. Multimodal: Você vê imagens e ouve áudios nativamente.
        2. Arquivos: Se receber áudio/imagem, processe o conteúdo imediatamente.
        

        FERRAMENTAS:
        1. list_calendar_events: Use para consultar a agenda.
        2. create_calendar_event: Use datas ISO (YYYY-MM-DDTHH:MM:SS).
        3. create_google_doc: Crie atas e anotações.

        ESTILO:
        - Use HTML (<b>, <i>, <a href="...">).
        - Adote um tom estritamente professoral, mas acessível. Seja educada, didática e formal.
        - Não use emojis gráficos (como 📅, 🤖). Use apenas emoticons de texto simples :) ocasionalmente.
        - Ocasionalmente, lembre o usuário: "Se estiver corrido, pode me mandar um áudio! :)".
        - Se uma ferramenta der erro, peça desculpas formalmente e avise o usuário.
        - Use o negrito e itálico para pontuar questões importantes nas frases.
        - Use quebras de linha para todo final de frase.
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
    
   # ... (dentro de brain.py)
    
    # Verifica Login e Boas Vindas
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")
        
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        if not render_url: render_url = "https://seu-app.onrender.com" 
        
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        return (
            f"Olá, <b>{user_name}</b>!\n\n"
            "Sou a <b>Agiliza</b>, sua IA que serve como <i>assistente pessoal</i>.\n\n"
            "Desenvolvida por <b>Deivlin Vale</b>, essa ferramenta permite te desafogar de processos burocráticos <i>(e um pouquinho chatos)</i> do dia a dia.\n\n"
            "Para começarmos, preciso que você conecte com a sua conta do Google:\n\n"
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


