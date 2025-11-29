import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from auth import load_user_credentials

# --- FUNÇÃO AUXILIAR ---
def get_service(user_id, api_name, version):
    print(f"🔍 [TOOLS DEBUG] Tentando autenticar user_id: '{user_id}'")
    
    if not user_id or user_id == "user_id" or user_id == "SYSTEM_ID":
        print(f"❌ [TOOLS] Erro: ID inválido: {user_id}")
        return None

    creds = load_user_credentials(user_id)
    if not creds:
        return None
        
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            return None
            
    return build(api_name, version, credentials=creds)

# --- LISTAR EVENTOS ---
def list_calendar_events(user_id: str, date_str: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
        start_of_day = f"{date_str}T00:00:00-03:00"
        end_of_day = f"{date_str}T23:59:59-03:00"

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"Agenda livre para o dia {date_str}."

        agenda_str = f"Agenda para {date_str}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_time = start[11:16] if 'T' in start else "Dia todo"
            agenda_str += f"- {start_time}: {event['summary']}\n"
            
        return agenda_str

    except Exception as e:
        return f"Erro ao ler agenda: {str(e)}"

# --- CRIAR EVENTO (Correção de Fuso) ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None):
    """
    Cria evento. Datas devem estar em formato ISO.
    """
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    # Se a IA não mandar o fim, adiciona 1h (Isso causava o erro se ela esquecesse)
    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
    }

    if attendees_emails:
        attendees_list = [{'email': email.strip()} for email in attendees_emails]
        event_body['attendees'] = attendees_list

    try:
        # Pega info do calendario para confirmar onde foi salvo
        calendar_info = service.calendars().get(calendarId='primary').execute()
        saved_email = calendar_info.get('id', 'primary')

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        
        # Retorna mensagem detalhada para debug
        return f"Sucesso! Evento '{summary}' criado na conta {saved_email}. Link: {link}"
        
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"Erro do Google: {str(e)}"

# --- DOCS (Sem mudanças) ---
def create_google_doc(title: str, content: str, user_id: str):
    docs_service = get_service(user_id, 'docs', 'v1')
    if not docs_service: return "Erro autenticação Docs."

    try:
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        link = f"https://docs.google.com/document/d/{doc_id}"
        return f"Documento criado: {link}"
    except Exception as e:
        return f"Erro Doc: {str(e)}"
