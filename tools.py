import datetime
import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from auth import load_user_credentials

# --- AUTH SERVICE ---
def get_service(user_id, api_name, version):
    if not user_id or user_id in ["user_id", "SYSTEM_ID"]:
        print(f"❌ [TOOLS] ID inválido: {user_id}")
        return None

    creds = load_user_credentials(user_id)
    if not creds: return None
        
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            return None
            
    return build(api_name, version, credentials=creds)

# --- 1. AGENDA: LISTAR ---
def list_calendar_events(user_id: str, date_str: str = None, days: int = 1):
    """Lista eventos. 'days' define quantos dias à frente verificar."""
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
        # Lógica para verificar múltiplos dias (ex: fim de semana)
        start_date_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        end_date_dt = start_date_dt + datetime.timedelta(days=days)
        
        start_of_period = f"{date_str}T00:00:00-03:00"
        end_of_period = f"{end_date_dt.strftime('%Y-%m-%d')}T23:59:59-03:00"

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_of_period,
            timeMax=end_of_period,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"Agenda livre entre {date_str} e {end_date_dt.strftime('%Y-%m-%d')}."

        agenda_str = f"📅 Agenda ({date_str} a {end_date_dt.strftime('%d/%m')}):\n"
        seen_events = set()
        
        for event in events:
            event_id = event['id']
            if event_id in seen_events: continue
            seen_events.add(event_id)
            
            summary = event.get('summary', 'Sem título')
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_time = start[11:16] if 'T' in start else "Dia todo"
            date_event = start[:10] if 'T' in start else start
            
            # Mostra a data se for uma listagem de vários dias
            date_prefix = f"[{date_event[8:10]}/{date_event[5:7]}] " if days > 1 else ""
            
            agenda_str += f"- {date_prefix}{start_time}: {summary} (ID: {event_id})\n"
            
        return agenda_str
    except Exception as e:
        return f"Erro ao ler agenda: {str(e)}"

# --- 2. AGENDA: CRIAR ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido (Use ISO)."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
    }

    if description: event_body['description'] = description

    if attendees_emails:
        valid_attendees = [{'email': e.strip()} for e in attendees_emails if "@" in e]
        if valid_attendees: event_body['attendees'] = valid_attendees

    try:
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"✅ Evento criado: {summary}. Link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Erro Google: {str(e)}"

# --- 3. AGENDA: DELETAR E ATUALIZAR ---
def delete_calendar_event(user_id: str, event_id: str):
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "🗑️ Evento removido com sucesso."
    except Exception as e:
        return f"Erro ao deletar: {e}"

def update_calendar_event(user_id: str, event_id: str, new_summary: str = None, new_start_time: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    event_patch = {}
    if new_summary: event_patch['summary'] = new_summary
    if new_start_time:
        try:
            dt = datetime.datetime.fromisoformat(new_start_time)
            end_time = (dt + datetime.timedelta(hours=1)).isoformat()
            event_patch['start'] = {'dateTime': new_start_time, 'timeZone': 'America/Sao_Paulo'}
            event_patch['end'] = {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'}
        except: return "Erro data."
    try:
        service.events().patch(calendarId='primary', eventId=event_id, body=event_patch).execute()
        return "✏️ Evento atualizado."
    except Exception as e: return f"Erro update: {e}"

# --- 4. DOCS E DRIVE ---
def create_google_doc(title: str, content: str, user_id: str):
    service = get_service(user_id, 'docs', 'v1')
    try:
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        return f"📄 Doc criado: https://docs.google.com/document/d/{doc_id}"
    except Exception as e: return f"Erro Doc: {e}"

def read_google_doc(user_id: str, doc_id: str):
    service = get_service(user_id, 'docs', 'v1')
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        full_text = ""
        for content in doc.get('body').get('content'):
            if 'paragraph' in content:
                for elem in content['paragraph']['elements']:
                    full_text += elem.get('textRun', {}).get('content', '')
        return f"Conteúdo:\n{full_text[:3000]}..."
    except Exception as e: return f"Erro Ler Doc: {e}"

def search_drive_file(user_id: str, query_name: str):
    service = get_service(user_id, 'drive', 'v3')
    try:
        q = f"name contains '{query_name}' and trashed = false"
        results = service.files().list(q=q, pageSize=5, fields="files(id, name, webViewLink)").execute()
        items = results.get('files', [])
        if not items: return "Nenhum arquivo encontrado."
        return "\n".join([f"- {i['name']} ({i['webViewLink']})" for i in items])
    except Exception as e: return f"Erro Drive: {e}"

# --- 5. TASKS E GMAIL ---
def create_task(user_id: str, title: str, notes: str = None):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        service.tasks().insert(tasklist='@default', body={'title': title, 'notes': notes}).execute()
        return f"☑️ Tarefa '{title}' criada."
    except Exception as e: return f"Erro Task: {e}"

def list_tasks(user_id: str):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=False).execute()
        items = results.get('items', [])
        if not items: return "Sem tarefas pendentes."
        return "Minhas Tarefas:\n" + "\n".join([f"☐ {i['title']}" for i in items])
    except Exception as e: return f"Erro List Task: {e}"

def get_unread_emails(user_id: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
        if not results.get('messages'): return "Zero emails novos."
        resp = "📩 Novos Emails:\n"
        for msg in results['messages']:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = m['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Sem Assunto)')
            resp += f"- {subject}\n"
        return resp
    except Exception as e: return f"Erro Gmail: {e}"

def create_email_draft(user_id: str, to: str, subject: str, body_text: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to
        message['Subject'] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(userId='me', body={'message': {'raw': encoded}}).execute()
        return f"✉️ Rascunho salvo no Gmail (ID: {draft['id']})"
    except Exception as e: return f"Erro Draft: {e}"
