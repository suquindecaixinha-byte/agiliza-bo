import datetime
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Escopos necessários (Agenda, Docs e Drive)
SCOPES = [
    'https://www.googleapis.com/auth/calendar', 
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

# --- AUTENTICAÇÃO INTELIGENTE (Nuvem ou Local) ---
json_credentials = os.getenv("GOOGLE_CREDENTIALS_JSON")

def get_creds():
    """
    Tenta autenticar usando a Variável de Ambiente (Render/Nuvem).
    Se não encontrar, tenta usar o arquivo credentials.json (PC Local).
    """
    if json_credentials:
        # Modo Nuvem (Render)
        creds_dict = json.loads(json_credentials)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
    else:
        # Modo Local (Seu Computador)
        # Verifica se o arquivo existe para evitar erro confuso
        if not os.path.exists('credentials.json'):
            raise FileNotFoundError("ERRO: Não achei 'credentials.json' nem a variável GOOGLE_CREDENTIALS_JSON.")
            
        return service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES)

# -------------------------------------------------

# --- Ferramenta 1: Criar Evento na Agenda (AGORA MULTI-USUÁRIO) ---
def create_calendar_event(summary: str, start_datetime: str, user_email: str, end_datetime: str = None):
    """
    Cria evento na agenda Google do e-mail especificado.
    Args:
        summary: Título do evento.
        start_datetime: Data de início (ISO Format).
        user_email: O e-mail do dono da agenda (Fundamental para multi-usuário).
        end_datetime: Data de fim (Opcional).
    """
    print(f"🔧 [TOOLS] Agendando para {user_email}: '{summary}'")
    
    if not user_email or "@" not in user_email:
        return "Erro: Preciso de um e-mail válido para agendar. O usuário precisa se cadastrar."

    try:
        creds = get_creds()
        service = build('calendar', 'v3', credentials=creds)
        
        if not end_datetime:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()

        event_body = {
            'summary': summary,
            'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
        }

        # O segredo do Multi-Usuário: Usamos o email passado como parâmetro, não mais um fixo
        event = service.events().insert(calendarId=user_email, body=event_body).execute()
        
        link = event.get('htmlLink')
        print(f"✅ [TOOLS] Agenda Sucesso: {link}")
        return f"Agendado com sucesso na conta {user_email}! Link: {link}"

    except Exception as e:
        error_msg = str(e)
        print(f"❌ [TOOLS] Erro Agenda: {error_msg}")
        
        if "404" in error_msg:
            return f"Erro: Não encontrei a agenda de {user_email}. Verifique se o e-mail está certo."
        if "403" in error_msg:
            return f"Erro de Permissão: O usuário {user_email} precisa compartilhar a agenda com o meu robô (service account) com permissão de 'Fazer Alterações'."
            
        return f"Erro técnico ao agendar: {error_msg}"

# --- Ferramenta 2: Criar Doc + Link Público ---
def create_google_doc(title: str, content: str):
    """
    Cria Doc e deixa público para quem tem o link.
    (Não precisa do e-mail do usuário pois o arquivo fica no Drive do Robô e é compartilhado via link).
    """
    print(f"🔧 [TOOLS] Criando Doc: '{title}'")
    
    try:
        creds = get_creds()
        service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 1. Cria o Doc
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')

        # 2. Insere o conteúdo
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        # 3. PERMISSÃO PÚBLICA (Qualquer um com o link pode ler)
        print(f"🔧 [TOOLS] Liberando link público...")
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()

        link = f"https://docs.google.com/document/d/{doc_id}"
        print(f"✅ [TOOLS] Doc Finalizado: {link}")
        return f"Relatório criado: {link}"

    except Exception as e:
        print(f"❌ [TOOLS] Erro Doc: {e}")
        return f"Erro ao criar documento: {str(e)}"

# Lista de ferramentas disponíveis para o Cérebro
available_tools = {
    'create_calendar_event': create_calendar_event,
    'create_google_doc': create_google_doc
