import google.generativeai as genai
from tools import create_calendar_event, create_google_doc
from memory import save_message, get_chat_history
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERRO: Chave do Google não encontrada no brain.py")

genai.configure(api_key=api_key)

tools_config = [create_calendar_event, create_google_doc]

# --- INJETANDO A DATA ATUAL NO CÉREBRO ---
# A IA precisa saber que dia é hoje para calcular "amanhã" ou "quinta-feira"
agora = datetime.datetime.now()
data_hoje = agora.strftime("%Y-%m-%d") # Ex: 2024-11-27
hora_atual = agora.strftime("%H:%M")   # Ex: 14:30
dia_semana = agora.strftime("%A")      # Ex: Wednesday

SYSTEM_PROMPT = f"""
Você é a Agiliza, uma assistente executiva eficiente.

CONTEXTO TEMPORAL (MUITO IMPORTANTE):
- Hoje é: {data_hoje} ({dia_semana})
- Hora atual: {hora_atual}

SEUS PODERES:
1. Gerenciar Agenda (create_calendar_event).
2. Criar Relatórios/Docs (create_google_doc).
3. Lembrar de tudo (Memória).

REGRAS DE FORMATAÇÃO CRÍTICAS:
- Ao chamar 'create_calendar_event', o campo 'start_datetime' DEVE ser no formato ISO 8601 COMPLETO: YYYY-MM-DDTHH:MM:SS.
- Exemplo: Para hoje às 15h, envie '{data_hoje}T15:00:00'.
- NUNCA envie apenas a hora (ex: '15:00' causará erro).

REGRAS GERAIS:
- Sempre verifique o histórico da conversa antes de responder.
- Se o usuário pedir um resumo de reunião, crie um Google Doc.
- Seja proativa e breve.
- Não use emojis.
- Tenha um tom de voz professoral
"""

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash-001',
    tools=tools_config,
    system_instruction=SYSTEM_PROMPT
)

def process_ai_request(user_text: str, user_id: str, file_path=None):
    print(f"🧠 [CÉREBRO] Usuário {user_id} disse: {user_text}")
    
    history = get_chat_history(user_id, limit=10)
    
    # Inicia o chat com histórico
    chat = model.start_chat(history=history, enable_automatic_function_calling=True)
    
    inputs = []
    
    if file_path:
        print(f"🎤 Processando áudio: {file_path}")
        audio_file = genai.upload_file(file_path)
        inputs.append(audio_file)
        inputs.append("Transcreva ou execute a ordem dada neste áudio. Se for uma reunião, faça um resumo.")
    
    if user_text:
        inputs.append(user_text)

    try:
        response = chat.send_message(inputs)
        text_response = response.text
        
        # Salva na Memória
        content_to_save = user_text if user_text else "[Arquivo de Áudio Enviado]"
        save_message(user_id, "user", content_to_save)
        save_message(user_id, "model", text_response)
        
        return text_response

    except Exception as e:
        print(f"❌ [ERRO CÉREBRO]: {e}")
        # Retorna mensagem amigável ao usuário em vez de quebrar
        return f"Tive um problema técnico com a data. Tente dizer 'Agende para o dia {data_hoje} às 15h'."