import google.generativeai as genai
# 1. ADICIONE O get_bot_email NA IMPORTAÇÃO ABAIXO:
from tools import create_calendar_event, create_google_doc, get_bot_email 
from memory import save_message, get_chat_history, get_user_email, register_user
import os
import datetime
import re
from dotenv import load_dotenv

load_dotenv()

# --- BLINDAGEM DE INICIALIZAÇÃO ---
# Se der erro aqui, o servidor não cai, apenas registra o erro.
model = None
erro_inicializacao = None

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("A variável GOOGLE_API_KEY não foi encontrada no Render.")

    genai.configure(api_key=api_key)

    tools_config = [create_calendar_event, create_google_doc]

    # Contexto Temporal
    agora = datetime.datetime.now()
    data_hoje = agora.strftime("%Y-%m-%d")
    hora_atual = agora.strftime("%H:%M")
    dia_semana = agora.strftime("%A")

    SYSTEM_PROMPT = f"""
    Você é a Agiliza.
    Hoje é: {data_hoje} ({dia_semana}) - {hora_atual}.
    Poderes: Agenda (create_calendar_event), Docs (create_google_doc), Memória.
    Regra Agenda: Use formato ISO '{data_hoje}T15:00:00'.
    Regra Email: Use o e-mail do usuário fornecido no contexto.
    """

    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-001',
        tools=tools_config,
        system_instruction=SYSTEM_PROMPT
    )
    print("✅ [CÉREBRO] Gemini inicializado com sucesso!")

except Exception as e:
    print(f"❌ [CÉREBRO] Erro Fatal na Inicialização: {e}")
    erro_inicializacao = str(e)
    model = None

# ----------------------------------

def is_valid_email(text):
    return re.match(r"[^@]+@[^@]+\.[^@]+", text)

def process_ai_request(user_text: str, user_id: str, file_path=None):
    if erro_inicializacao:
        return f"🚨 O Bot está online, mas o cérebro falhou: {erro_inicializacao}"

    print(f"🧠 [CÉREBRO] Usuário {user_id} disse: {user_text}")
    
    # --- PASSO 1: VERIFICAÇÃO DE USUÁRIO (Cadastro) ---
    try:
        user_email = get_user_email(user_id)
    except Exception as e:
        return f"Erro ao conectar no banco de memória: {e}"

    if not user_email:
        if user_text and is_valid_email(user_text.strip()):
            email_candidato = user_text.strip()
            register_user(user_id, email_candidato)
            save_message(user_id, "user", user_text)
            
            # --- 2. AQUI ESTÁ A MUDANÇA NA MENSAGEM ---
            bot_email = get_bot_email() # Pega o email automaticamente
            
            mensagem_instrucoes = (
                f"✅ **Cadastro realizado com sucesso!**\n"
                f"E-mail registrado: {email_candidato}\n\n"
                f"⚠️ **PARA EU FUNCIONAR, FAÇA ISSO AGORA:**\n\n"
                f"Preciso que você compartilhe sua agenda comigo para que eu possa criar reuniões.\n"
                f"1. Abra o Google Agenda (calendar.google.com)\n"
                f"2. Vá em Configurações > Compartilhar com pessoas específicas\n"
                f"3. Adicione este meu e-mail abaixo:\n\n"
                f"`{bot_email}`\n\n"
                f"4. 🚨 **MUITO IMPORTANTE:** Mude a permissão para **'Fazer alterações em eventos'**.\n\n"
                f"Assim que fizer isso, me avise dizendo 'Pronto'!"
            )
            return mensagem_instrucoes
            # ------------------------------------------
            
        else:
            return "Olá! Sou a Agiliza. Não identifiquei seu cadastro. Por favor, digite o e-mail da sua conta Google (ex: joao@gmail.com) para começarmos."

    # --- PASSO 2: EXECUÇÃO NORMAL ---
    try:
        history = get_chat_history(user_id, limit=10)
        chat = model.start_chat(history=history, enable_automatic_function_calling=True)
        
        inputs = []
        inputs.append(f"CONTEXTO DO USUÁRIO: O e-mail autenticado é '{user_email}'.")

        if file_path:
            audio_file = genai.upload_file(file_path)
            inputs.append(audio_file)
        
        if user_text:
            inputs.append(user_text)

        response = chat.send_message(inputs)
        text_response = response.text
        
        save_message(user_id, "user", user_text or "[Audio]")
        save_message(user_id, "model", text_response)
        
        return text_response

    except Exception as e:
        print(f"❌ [ERRO EXECUÇÃO]: {e}")

        return f"Erro técnico durante a resposta: {e}"
