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
    
    # --- CONTEXTO DE DATA E HORA ---
    agora = datetime.datetime.now()
    data_hoje_iso = agora.strftime("%Y-%m-%d")
    data_hoje_human = agora.strftime("%d-%m-%y")
    hora_atual = agora.strftime("%H:%M")
    dia_semana = agora.strftime("%A")
    
    SYSTEM_PROMPT = f"""
    Você é a Agiliza. 
    Hoje é: {data_hoje_human} ({dia_semana}) e agora são {hora_atual}.
    
    Poderes Disponíveis:
    1. create_calendar_event: Agendar.
    2. list_calendar_events: Ver horários.
    3. create_google_doc: Criar documentos.

    DIRETRIZES TÉCNICAS (HTML):
    O Telegram usa HTML. Use <b>negrito</b>, <i>itálico</i> e <a href="url">links</a>. Não use Markdown.

    DIRETRIZES DE NOME:
    Use o NOME DO USUÁRIO (fornecido no contexto como 'USER_NAME') para ser pessoal.
    Exemplo: "Olá Deivlin, tudo bem?" em vez de "Olá usuário".
    Se não houver nome, não invente, seja neutro.

    DIRETRIZES DE FORMATAÇÃO DE DATA (CHAT):
    Ao falar com o usuário, use ESTRITAMENTE o formato: DD-MM-AA, às HH:MM.
    Exemplo: "Agendado para 28-11-25, às 14:00".

    DIRETRIZES DE FUSO HORÁRIO E AGENDA (CRÍTICO):
    1. A data interna para a ferramenta (create_calendar_event) DEVE ser ISO (YYYY-MM-DDTHH:MM:SS).
    2. O horário é sempre 'America/Sao_Paulo'.
    3. Se o usuário pedir "Das 7h às 20h", você DEVE preencher o 'start_datetime' (07:00) E o 'end_datetime' (20:00). Se você omitir o final, o sistema colocará apenas 1 hora de duração, o que causará erro.
    4. Argumento 'user_id' é obrigatório (Use o SYSTEM_ID do contexto).

    DIRETRIZES DE COMPORTAMENTO:
    1. Regra Email: Use sempre o e-mail do usuário.
    2. Regra Tom: Professoral, educado, didático.
    3. Regra Emojis: Sem emojis gráficos.
    4. Regra Áudio: Lembre que pode mandar áudio.
    """
    
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-001',
        tools=tools_config,
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    print(f"❌ Erro Brain: {e}")

# ----------------------------

# Nova assinatura recebe user_name
def process_ai_request(user_text: str, user_id: str, user_name: str, file_path=None):
    print(f"🧠 [CÉREBRO] User {user_id} ({user_name}): {user_text}")
    
    creds = load_user_credentials(user_id)
    
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")

        render_url = os.getenv("RENDER_EXTERNAL_URL") 
        if not render_url:
            return "Erro Técnico: Variável RENDER_EXTERNAL_URL não configurada."
            
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        saudacao = f"Prezado(a) <b>{user_name}</b>" if user_name else "Prezado(a) usuário(a)"

        mensagem_boas_vindas = (
            "<b>Agiliza IA: Sua rotina no piloto automático</b>\n\n"
            f"{saudacao}, seja bem-vindo(a).\n\n"
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
        
        contexto_sistema = (
            f"--- DADOS DE SISTEMA ---\n"
            f"USER_NAME: {user_name}\n"
            f"E-mail do Usuário: {user_email}\n"
            f"SYSTEM_ID: '{user_id}'\n"
            f"(Ao usar ferramentas, user_id = '{user_id}')\n"
            f"------------------------"
        )
        
        inputs = [contexto_sistema]

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
