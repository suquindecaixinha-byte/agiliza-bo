import google.generativeai as genai
from tools import create_calendar_event, create_google_doc 
from memory import save_message, get_chat_history, get_user_email, register_user
from auth import load_user_credentials # Para checar se já está logado
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# --- INICIALIZAÇÃO GEMINI ---
model = None
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    
    # Observe que removemos 'get_bot_email' das tools, pois não é mais necessário
    tools_config = [create_calendar_event, create_google_doc]
    
    agora = datetime.datetime.now()
    SYSTEM_PROMPT = f"""
    Você é a Agiliza. Hoje: {agora.strftime("%Y-%m-%d %H:%M")}.
    Seu foco: Ajudar o usuário gerenciando Agenda e Docs.
    Se o usuário pedir algo, use as ferramentas disponíveis.
Regra Email: Use o e-mail do usuário fornecido no contexto.
    Regra: Use sempre um tom professoral
    Regra: Não use emojis
    Regra: Lembre o usuário que ele pode mandar áudio. Exemplo: Olha, se estiver corrido por aí, pode me mandar um áudio também! :)
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
    # Tenta carregar as credenciais do banco
    creds = load_user_credentials(user_id)
    
    # Se não tem credenciais válidas, manda o link de login
    if not creds or not creds.valid:
        # Precisamos registrar o usuário no banco antes de gerar o link
        # para garantir que o ID exista quando o callback voltar.
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")

        # Pega a URL do Render (Configure isso nas Variáveis de Ambiente!)
        render_url = os.getenv("RENDER_EXTERNAL_URL") 
        if not render_url:
            return "❌ Erro: Variável RENDER_EXTERNAL_URL não configurada no painel."
            
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        return (
            "Olá! Para eu acessar sua Agenda e Drive, preciso da sua permissão.\n\n"
            "É rápido e seguro (login oficial do Google).\n\n"
            f"🔗 [Toque aqui para Conectar]({link_login})"
        )
    
    # --- SE JÁ ESTÁ LOGADO, SEGUE A VIDA ---
    try:
        # Recupera histórico e email (agora pegamos do banco, atualizado pelo callback)
        history = get_chat_history(user_id)
        user_email = get_user_email(user_id) # O callback atualizou isso
        
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
        return "Desculpe, tive um erro técnico ao processar seu pedido."