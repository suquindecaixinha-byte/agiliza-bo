import datetime
import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from auth import load_user_credentials

def get_service(user_id, api_name, version):
    if not user_id or user_id in ["user_id", "SYSTEM_ID"]: return None
    creds = load_user_credentials(user_id)
    if not creds: return None
    if creds.expired and creds.refresh_token:
        try: creds.refresh(Request())
        except: return None
    return build(api_name, version, credentials=creds)

# --- AGENDA ---
def list_calendar_events(user_id: str, date_str: str = None, days: int = 1):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."
    if not date_str: date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        start_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = start_dt + datetime.timedelta(days=days)
        start_iso = f"{date_str}T00:00:00-03:00"
        end_iso = f"{end_dt.strftime('%Y-%m-%d')}T23:59:59-03:00"

        events = service.events().list(calendarId='primary', timeMin=start_iso, timeMax=end_iso, singleEvents=True, orderBy='startTime').execute().get('items', [])
        
        if not events: return f"Agenda livre."
        
        resp = f"📅 Agenda:\n"
        for ev in events:
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            time_str = start[11:16] if 'T' in start else "Dia todo"
            resp += f"- {time_str}: {ev.get('summary', 'Sem título')} (ID: {ev['id']})\n"
        return resp
    except Exception as e: return f"Erro Agenda: {e}"

def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "Erro Auth."
    
    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except: return "Erro data."

    body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'},
        'description': description or ""
    }
    if attendees_emails:
        body['attendees'] = [{'email': e.strip()} for e in attendees_emails if '@' in e]

    try:
        ev = service.events().insert(calendarId='primary', body=body).execute()
        return f"✅ Evento criado: {ev.get('htmlLink')}"
    except Exception as e: return f"Erro Google: {e}"

def delete_calendar_event(user_id: str, event_id: str):
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Evento deletado."
    except Exception as e: return f"Erro delete: {e}"

def update_calendar_event(user_id: str, event_id: str, new_summary: str = None, new_start_time: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    patch = {}
    if new_summary: patch['summary'] = new_summary
    if new_start_time:
        patch['start'] = {'dateTime': new_start_time}
    try:
        service.events().patch(calendarId='primary', eventId=event_id, body=patch).execute()
        return "Evento atualizado."
    except Exception as e: return f"Erro update: {e}"

# --- DOCS & DRIVE ---
def create_google_doc(title: str, content: str, user_id: str):
    service = get_service(user_id, 'docs', 'v1')
    try:
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        service.documents().batchUpdate(documentId=doc_id, body={'requests': [{'insertText': {'location': {'index': 1}, 'text': content}}]}).execute()
        return f"📄 Doc criado: https://docs.google.com/document/d/{doc_id}"
    except Exception as e: return f"Erro Doc: {e}"

def read_google_doc(user_id: str, doc_id: str):
    service = get_service(user_id, 'docs', 'v1')
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        text = ""
        for c in doc.get('body')['content']:
            if 'paragraph' in c:
                for e in c['paragraph']['elements']: text += e.get('textRun', {}).get('content', '')
        return f"Conteúdo:\n{text[:2000]}..."
    except Exception as e: return f"Erro Ler: {e}"

def search_drive_file(user_id: str, query_name: str):
    service = get_service(user_id, 'drive', 'v3')
    try:
        res = service.files().list(q=f"name contains '{query_name}' and trashed=false", pageSize=5, fields="files(id, name, webViewLink)").execute()
        files = res.get('files', [])
        if not files: return "Nada encontrado."
        return "\n".join([f"- {f['name']} ({f['webViewLink']})" for f in files])
    except Exception as e: return f"Erro Drive: {e}"

# --- TASKS & GMAIL ---
def create_task(user_id: str, title: str, notes: str = None):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        service.tasks().insert(tasklist='@default', body={'title': title, 'notes': notes}).execute()
        return f"Tarefa '{title}' criada."
    except Exception as e: return f"Erro Task: {e}"

def list_tasks(user_id: str):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        items = service.tasks().list(tasklist='@default', showCompleted=False).execute().get('items', [])
        return "Tarefas:\n" + "\n".join([f"☐ {i['title']}" for i in items]) if items else "Sem tarefas."
    except Exception as e: return f"Erro List Task: {e}"

def get_unread_emails(user_id: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        msgs = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute().get('messages', [])
        if not msgs: return "Sem novos emails."
        resp = "📩 Emails:\n"
        for m in msgs:
            headers = service.users().messages().get(userId='me', id=m['id']).execute()['payload']['headers']
            subj = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
            resp += f"- {subj}\n"
        return resp
    except Exception as e: return f"Erro Gmail: {e}"

def create_email_draft(user_id: str, to: str, subject: str, body_text: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        msg = EmailMessage()
        msg.set_content(body_text)
        msg['To'], msg['Subject'] = to, subject
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = service.users().drafts().create(userId='me', body={'message': {'raw': encoded}}).execute()
        return f"Rascunho criado (ID: {draft['id']})"
    except Exception as e: return f"Erro Draft: {e}"
