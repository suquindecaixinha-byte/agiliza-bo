import google.generativeai as genai
from tools import create_calendar_event, create_google_doc, list_calendar_events
from memory import save_message, get_chat_history, get_user_email, register_user
from auth import load_user_credentials
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# --- INICIALIZAÇÃO GEMINI ---
model = None
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    
    tools_config = [create_calendar_event, create_google_doc, list_calendar_events]
    
    agora = datetime.datetime.now()
    data_hoje = agora.strftime("%Y-%m-%d")
    
    # --- PROMPT PARA HTML (MUITO MAIS SEGURO) ---
    SYSTEM_PROMPT = f"""
    Você é a Agiliza. Hoje: {agora.strftime("%Y-%m-%d %H:%M")}.
    Seu foco: Ajudar o usuário gerenciando Agenda e Docs.
    
    Poderes Disponíveis:
    1. create_calendar_event: Agendar.
    2. list_calendar_events: Ver horários.
    3. create_google_doc: Criar documentos.

    DIRETRIZES TÉCNICAS (FORMATO HTML):
    O Telegram espera formatação em HTML. Não use Markdown (* ou #).
    
    1. Negrito: Use a tag <b>exemplo</b>.
    2. Links: Use <a href="url">texto</a>.
    3. Itálico: Use <i>exemplo</i>.
    4. NÃO use tags complexas como <ul>, <li>, <p> ou <br>. Use apenas quebras de linha normais.
    
    DIRETRIZES DE COMPORTAMENTO:
    1. Regra Email: Use sempre o e-mail do usuário ({get_user_email} ou contexto).
    2. Regra Tom: Professoral, educado, didático.
    3. Regra Emojis: Não use emojis gráficos.
    4. Regra Áudio: Lembre que pode mandar áudio.
    5. Regra Formatação: Use quebras de linha para clareza.

    Regra Técnica Agenda: Use formato ISO '{data_hoje}T15:00:00'.
    """
    
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-001',
        tools=tools_config,
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    print(f"❌ Erro Brain: {e}")

# ----------------------------

def process_ai_request(user_text: str, user_id: str, file_path=None):
    print(f"🧠 [CÉREBRO] User {user_id}: {user_text}")
    
    creds = load_user_credentials(user_id)
    
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")

        render_url = os.getenv("RENDER_EXTERNAL_URL") 
        if not render_url:
            return "Erro Técnico: Variável RENDER_EXTERNAL_URL não configurada."
            
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        # Mensagem formatada manualmente em HTML
        mensagem_boas_vindas = (
            "<b>Agiliza IA: Sua rotina no piloto automático</b>\n\n"
            "Prezado(a) usuário(a), seja bem-vindo(a).\n\n"
            "Idealizada por <b>Deivlin Vale</b>, esta plataforma foi desenvolvida com um propósito claro: "
            "eliminar o atrito entre você e a sua produtividade.\n\n"
            "<b>Como posso auxiliá-lo de fato?</b>\n\n"
            "• <b>Agenda Blindada:</b> Agende reuniões e encontre horários livres.\n"
            "• <b>Da Ideia ao Documento:</b> Envie um áudio e eu transformarei sua fala em um Doc.\n"
            "• <b>Segurança:</b> Utilizo a conexão oficial do Google.\n\n"
            "Menos burocracia, mais realização. <b>Podemos iniciar?</b>\n\n"
            "Por favor, acesse o link abaixo para conectar sua conta Google:\n"
            f"<a href='{link_login}'>CONECTAR AGORA</a>"
        )
        return mensagem_boas_vindas
    
    try:
        history = get_chat_history(user_id)
        user_email = get_user_email(user_id)
        
        chat = model.start_chat(history=history, enable_automatic_function_calling=True)
        
        inputs = [f"CONTEXTO: Usuário logado: {user_email}"]
        if file_path:
            inputs.append(genai.upload_file(file_path))
        if user_text:
            inputs.append(user_text)

        response = chat.send_message(inputs)
        text_response = response.text
        
        save_message(user_id, "user", user_text or "[Audio]")
        save_message(user_id, "model", text_response)
        
        return text_response

    except Exception as e:
        print(f"❌ Erro Execução: {e}")
        return "Peço desculpas, erro técnico. Contacte o administrador."
