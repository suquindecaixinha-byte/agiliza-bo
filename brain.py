import google.generativeai as genai
from tools import create_calendar_event, create_google_doc, list_calendar_events
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
        tools_config = [create_calendar_event, create_google_doc, list_calendar_events]
        
        # --- DEFINIÇÃO DE DATAS (CRUCIAL PARA NÃO DAR ERRO) ---
        agora = datetime.datetime.now()
        data_hoje = agora.strftime("%d-%m-%Y")       # Formato visual (29-11-2025)
        data_hoje_iso = agora.strftime("%Y-%m-%d")   # Formato sistema (2025-11-29) - NECESSÁRIO
        hora_atual = agora.strftime("%H:%M")
        dia_semana = agora.strftime("%A")
        
        # --- PROMPT DO SISTEMA ---
        SYSTEM_PROMPT = f"""
        Você é a Agiliza, uma assistente executiva de altíssima eficiência.
        Data atual: {data_hoje} ({dia_semana}) - Hora: {hora_atual}.
        
        CAPACIDADES MULTIMODAIS (VISÃO E AUDIÇÃO):
        1. Você pode ouvir áudios longos (reuniões, notas de voz) e ver imagens.
        2. Se receber um áudio longo e o usuário pedir "Resumo" ou "Ata":
           - Identifique os falantes (se possível).
           - Liste os tópicos principais.
           - Extraia "Action Items" (tarefas a fazer).
           - SUGIRA criar um Google Doc com esse conteúdo se o texto for longo.
        3. Se receber imagem de texto (papel, quadro branco): Transcreva o conteúdo.
    
        FERRAMENTAS DISPONÍVEIS E REGRAS:
        
        1. **list_calendar_events(date_str, days)**:
           - Use para ver a agenda.
           - 'days': Número de dias a verificar.
           - **REGRA DE OURO (FIM DE SEMANA)**: Se o usuário perguntar "Como está meu fim de semana" ou "Minha semana", NÃO pergunte a data. Calcule a data do próximo sábado (ou hoje) e chame a função com 'days=2' (para fim de semana) ou 'days=5' (para semana).
           - Exemplo: Hoje é Sábado. User: "Como tá o fim de semana?". Ação: list_calendar_events(date_str='{data_hoje_iso}', days=2).
        
        2. **create_calendar_event**: Agendar.
           - A data DEVE estar em ISO (YYYY-MM-DDTHH:MM:SS).
        
        3. **create_google_doc**: CRIAR DOCUMENTOS. 
           - USE ESTA FUNÇÃO se o usuário pedir para "anotar", "criar ata", "resumir reunião" ou se a resposta for muito longa.
    
        DIRETRIZES DE ESTILO:
        - Use HTML (<b>negrito</b>, <i>itálico</i>).
        - Seja formal, direta e didática.
        - Se algo falhar, peça desculpas educadamente.

         DIRETRIZES DE NOME E CONVITES:
    1. Se o usuário disser "Reunião com João", e NÃO der o e-mail:
       - Título: "Reunião com João"
       - Descrição: "Encontro com João"
       - Attendees: VAZIO (Não invente e-mails).
    2. Se o usuário der o e-mail:
       - Attendees: ['joao@email.com']

    DIRETRIZES DE FORMATAÇÃO DE DATA (CHAT):
    Ao falar com o usuário, use ESTRITAMENTE o formato: DD-MM-AA, às HH:MM.

    DIRETRIZES DE FUSO HORÁRIO E AGENDA (CRÍTICO):
    1. A data interna DEVE ser ISO (YYYY-MM-DDTHH:MM:SS).
    2. Se o usuário pedir "Das 7h às 20h", preencha 'start_datetime' e 'end_datetime'.
    3. Argumento 'user_id' é obrigatório (Use o SYSTEM_ID do contexto).

    DIRETRIZES DE COMPORTAMENTO:
    1. Regra Email: Use sempre o e-mail do usuário fornecido no contexto para qualquer ação.
    2. Regra Tom: Adote um tom estritamente professoral. Seja educado, didático, formal, mas acessível.
    3. Regra Emojis: Não utilize emojis gráficos (como 👍, 📅, 🤖). O uso de emoticons de texto simples (como :) ) é permitido com parcimônia.
    4. Regra Áudio: Ocasionalmente, lembre o usuário da possibilidade de envio de áudio. Exemplo: "Olha, se estiver corrido por aí, pode me mandar um áudio também! :)"
    5. Regra Formatação: Utilize quebras de linha frequentes para garantir a plena visualização das informações. Use negrito e itálico estrategicamente para destacar termos cruciais.
    6. Regra de Falha: Caso uma função solicitada não esteja disponível ou falhe, peça desculpas formalmente e instrua o usuário a contactar o administrador da IA.
    7. Regra: Utilize com parcimônia o primeiro nome da pessoa quando for da uma resposta.
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
    
    # --- VERIFICAÇÃO DE SEGURANÇA SE O MODELO FALHOU ---
    if model is None:
        return "⚠️ Erro Crítico: O cérebro da IA não foi inicializado. Verifique os logs do servidor (Erro: Model is None)."

    creds = load_user_credentials(user_id)
    
    # Verifica Login e Boas Vindas
    if not creds or not creds.valid or user_text == "/start":
        if not get_user_email(user_id):
            register_user(user_id, "pendente_login")
        
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        # Fallback se a variável não estiver definida, para não quebrar o link
        if not render_url: render_url = "https://seu-app.onrender.com" 
        
        link_login = f"{render_url}/auth/login?state={user_id}"
        
        return (
            f"Olá <b>{user_name}</b>!\n\n"
            "Para que eu possa gerenciar sua agenda e criar documentos, "
            "preciso que você conecte sua conta Google.\n\n"
            f"👉 <a href='{link_login}'>CLIQUE AQUI PARA CONECTAR</a>"
        )
    
    try:
        # Histórico do Supabase
        history = get_chat_history(user_id)
        user_email = get_user_email(user_id)
        
        # Prepara Chat
        chat = model.start_chat(history=history, enable_automatic_function_calling=True)
        
        # Monta o prompt do sistema para essa rodada
        system_context = (
            f"CONTEXTO DO USUÁRIO:\n"
            f"- Nome: {user_name}\n"
            f"- Email: {user_email}\n"
            f"- ID Sistema: '{user_id}' (Use este ID nas ferramentas)\n"
        )
        
        # Lista de inputs para o Gemini (Texto + Arquivo se houver)
        inputs = [system_context]
        
        if file_path:
            print(f"📤 Uploading file: {file_path}")
            uploaded_file = genai.upload_file(file_path)
            
            # Espera ativa para garantir que o arquivo foi processado
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)
                
            inputs.append(uploaded_file)
            inputs.append("Analise este arquivo conforme solicitado.")

        if user_text:
            inputs.append(user_text)

        # Envia para a IA
        response = chat.send_message(inputs)
        text_response = response.text
        
        # Salva apenas o texto no Supabase
        log_content = f"[Arquivo enviado] {user_text}" if file_path else user_text
        save_message(user_id, "user", log_content)
        save_message(user_id, "model", text_response)
        
        return text_response

    except Exception as e:
        print(f"❌ Erro Execução AI: {e}")
        return "Peço desculpas. Ocorreu um erro técnico ao processar sua solicitação."
