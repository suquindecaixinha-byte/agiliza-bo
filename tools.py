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

# --- MODIFICAÇÃO DE SEGURANÇA ---
# Tenta pegar da variável de ambiente (Nuvem). Se não tiver, tenta arquivo (Local).
json_credentials = os.getenv("GOOGLE_CREDENTIALS_JSON")

def get_creds():
    if json_credentials:
        # Se estamos na nuvem (Render), lê da variável
        creds_dict = json.loads(json_credentials)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
    else:
        # Se estamos no PC local, lê do arquivo
        return service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES)

# --------------------------------

def get_creds():
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

def create_calendar_event(summary: str, start_datetime: str, end_datetime: str = None):
    """Cria evento na agenda (sem convite para evitar erro 403)."""
    print(f"🔧 [TOOLS] Agendando: '{summary}'")
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

    try:
        event = service.events().insert(calendarId=ID_DA_SUA_AGENDA, body=event_body).execute()
        link = event.get('htmlLink')
        print(f"✅ [TOOLS] Agenda Sucesso: {link}")
        return f"Agendado! Link: {link}"
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"Erro ao agendar: {str(e)}"

# --- Ferramenta 2: Criar Doc + COMPARTILHAR (A Correção) ---
def create_google_doc(title: str, content: str):
    """Cria Doc e deixa público para quem tem o link (evita erro de permissão)."""
    print(f"🔧 [TOOLS] Criando Doc: '{title}'")
    
    creds = get_creds()
    service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    try:
        # 1. Cria o Doc
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')

        # 2. Insere o conteúdo
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        # 3. PERMISSÃO PÚBLICA (Qualquer um com o link pode ler)
        # Isso resolve o erro "Arquivo não existe"
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
