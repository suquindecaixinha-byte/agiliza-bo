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
    
    # Lista de ferramentas
    tools_config = [create_calendar_event, create_google_doc, list_calendar_events]
    
    agora = datetime.datetime.now()
    data_hoje = agora.strftime("%Y-%m-%d")
    
    # --- NOVAS REGRAS IMPLEMENTADAS NO PROMPT ---
    SYSTEM_PROMPT = f"""
    Você é a Agiliza. Hoje: {agora.strftime("%Y-%m-%d %H:%M")}.
    Seu foco: Ajudar o usuário gerenciando Agenda e Docs.
    
    Poderes Disponíveis:
    1. create_calendar_event: Agendar (pode incluir lista de emails de convidados).
    2. list_calendar_events: Ver o que está ocupado num dia para achar horários livres.
    3. create_google_doc: Criar documentos.

    DIRETRIZES DE COMPORTAMENTO (RÍGIDAS):
    1. Regra Email: Use sempre o e-mail do usuário fornecido no contexto para qualquer ação.
    2. Regra Tom: Adote um tom estritamente professoral. Seja educado, didático, formal, mas acessível.
    3. Regra Emojis: Não utilize emojis gráficos (como 👍, 📅, 🤖). O uso de emoticons de texto simples (como :) ) é permitido com parcimônia.
    4. Regra Áudio: Ocasionalmente, lembre o usuário da possibilidade de envio de áudio. Exemplo: "Olha, se estiver corrido por aí, pode me mandar um áudio também! :)"
    5. Regra Formatação: Utilize quebras de linha frequentes para garantir a plena visualização das informações. Use **negrito** e *itálico* estrategicamente para destacar termos cruciais.
    6. Regra de Falha: Caso uma função solicitada não esteja disponível ou falhe, peça desculpas formalmente e instrua o usuário a contactar o administrador da IA.

    Regra Técnica Agenda: Use sempre o formato ISO '{data_hoje}T15:00:00'.
    Sempre verifique disponibilidade (list_calendar_events) antes de agendar.
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
    
    # --- CHECAGEM DE LOGIN (OAUTH2) ---
    creds = load_user_credentials(user_id)
    
    # Se NÃO tem credenciais (ou se mandou /start), mostra a Apresentação + Login
    if not creds or not creds.valid or user_text == "/start":
        
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")

        render_url = os.getenv("RENDER_EXTERNAL_URL") 
        if not render_url:
            return "Erro Técnico: Variável RENDER_EXTERNAL_URL não configurada. Contacte o administrador."
            
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        # --- MENSAGEM DE BOAS-VINDAS (ADEQUADA AO NOVO TOM SEM EMOJIS) ---
        mensagem_boas_vindas = (
            "**Agiliza IA: Sua rotina no piloto automático**\n\n"
            "Seja bem-vindo(a).\n\n"
            "Idealizada por **Deivlin Vale**, esta plataforma foi desenvolvida com um propósito claro: "
            "eliminar o atrito entre você e a sua produtividade.\n\n"
            "**Como posso auxiliá-lo de fato?**\n\n"
            "* **Agenda Blindada:** Agende reuniões e encontre horários livres com apenas uma frase.\n"
            "* **Da ideia ao documento:** Envie um áudio e eu transformarei sua fala em um documento organizado no seu Drive.\n"
            "* **Segurança:** Seus dados pertencem a você. Utilizo a conexão oficial do Google para garantir a privacidade.\n\n"
            "Menos burocracia, mais realização. **Vamos iniciar?**\n\n"
            "Por favor, toque no link abaixo para conectar sua conta Google:\n"
            f"[CONECTAR AGORA]({link_login})"
        )
        return mensagem_boas_vindas
    
    # --- SE JÁ ESTÁ LOGADO, PROCESSA O PEDIDO ---
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
        return "Peço desculpas, mas ocorreu um erro técnico ao processar seu pedido. Por favor, contacte o administrador da IA."