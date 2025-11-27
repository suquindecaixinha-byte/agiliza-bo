# tools.py CORRIGIDO
import datetime
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/calendar', 
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def get_creds():
    """
    Obtém credenciais:
    1. Tenta via Variável de Ambiente (Render/Nuvem).
    2. Se falhar, tenta via arquivo local (Teste no PC).
    """
    json_credentials = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if json_credentials:
        # Nuvem
        creds_dict = json.loads(json_credentials)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
    else:
        # Local
        if os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=SCOPES)
        else:
            raise FileNotFoundError("Credenciais não encontradas (Nem ENV, nem arquivo).")

def create_calendar_event(summary: str, start_datetime: str, user_email: str, end_datetime: str = None):
    """
    Cria evento na agenda do usuário (via Service Account).
    O user_email é obrigatório para saber em qual agenda salvar.
    """
    print(f"🔧 [TOOLS] Agendando: '{summary}' para {user_email}")
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

        # Usa o e-mail do usuário como calendarId (funciona se ele compartilhou a agenda com o robô)
        event = service.events().insert(calendarId=user_email, body=event_body).execute()
        link = event.get('htmlLink')
        print(f"✅ [TOOLS] Agenda Sucesso: {link}")
        return f"Agendado com sucesso! Link: {link}"
        
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"Erro ao agendar. Verifique se o usuário {user_email} compartilhou a agenda com o e-mail do robô (client_email). Detalhe: {str(e)}"

def create_google_doc(title: str, content: str):
    """Cria Doc e deixa público para leitura (quem tem o link)."""
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
        
        # 3. Permissão de Leitura para Todos (Link Público)
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()

        link = f"https://docs.google.com/document/d/{doc_id}"
        print(f"✅ [TOOLS] Doc Finalizado: {link}")
        return f"Documento criado: {link}"

    except Exception as e:
        print(f"❌ [TOOLS] Erro Doc: {e}")

        return f"Erro ao criar documento: {str(e)}"

# --- Adicione isso no final do arquivo tools.py ---

def get_bot_email():
    """Retorna o email do robô para ser mostrado ao usuário."""
    try:
        creds = get_creds()
        return creds.service_account_email
    except:
        return "[Erro ao obter e-mail do robô]"
