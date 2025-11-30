import datetime
import base64
from email.message import EmailMessage
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

# --- 1. AGENDA: LISTAR, CRIAR, DELETAR, ATUALIZAR ---

def list_calendar_events(user_id: str, date_str: str = None, days: int = 1):
    """
    Lista eventos.
    - date_str: Data inicial (YYYY-MM-DD). Se vazio, usa hoje.
    - days: Quantos dias listar a partir da data inicial.
    """
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
        # Calcula intervalo de tempo com base em 'days'
        dt_start = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dt_end = dt_start + datetime.timedelta(days=days)
        
        start_of_period = f"{date_str}T00:00:00-03:00"
        end_of_period = f"{dt_end.strftime('%Y-%m-%d')}T23:59:59-03:00"

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_of_period,
            timeMax=end_of_period,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"Agenda livre entre {date_str} e {dt_end.strftime('%Y-%m-%d')}."

        agenda_str = f"Agenda ({date_str} até {dt_end.strftime('%Y-%m-%d')}):\n"
        seen_events = set()
        
        for event in events:
            event_id = event['id']
            if event_id in seen_events: continue
            seen_events.add(event_id)
            
            summary = event.get('summary', 'Sem título')
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            # Formatação limpa
            data_evento = start[:10]
            hora_evento = start[11:16] if 'T' in start else "Dia todo"
            
            agenda_str += f"- [{data_evento} às {hora_evento}] {summary} (ID: {event_id})\n"
            
        return agenda_str

    except Exception as e:
        return f"Erro ao ler agenda: {str(e)}"

def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    """Cria evento na agenda."""
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    # Lógica de Horário
    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido (Use ISO ex: 2025-11-20T14:00:00)."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
    }

    if description:
        event_body['description'] = description

    if attendees_emails:
        valid_attendees = []
        for email in attendees_emails:
            if isinstance(email, str) and "@" in email:
                valid_attendees.append({'email': email.strip()})
        if valid_attendees:
            event_body['attendees'] = valid_attendees

    try:
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        return f"Sucesso! Evento '{summary}' criado. Link: {link}"
    except Exception as e:
        return f"Erro do Google Agenda: {str(e)}"

def delete_calendar_event(user_id: str, event_id: str):
    """Remove um evento pelo ID."""
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Evento removido com sucesso."
    except Exception as e:
        return f"Erro ao deletar: {e}"

def update_calendar_event(user_id: str, event_id: str, new_summary: str = None, new_start_time: str = None):
    """Atualiza título ou horário de um evento."""
    service = get_service(user_id, 'calendar', 'v3')
    
    event_patch = {}
    if new_summary:
        event_patch['summary'] = new_summary
        
    if new_start_time:
        try:
            dt = datetime.datetime.fromisoformat(new_start_time)
            end_time = (dt + datetime.timedelta(hours=1)).isoformat()
            event_patch['start'] = {'dateTime': new_start_time, 'timeZone': 'America/Sao_Paulo'}
            event_patch['end'] = {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'}
        except:
            return "Erro: Data inválida."

    try:
        service.events().patch(calendarId='primary', eventId=event_id, body=event_patch).execute()
        return "Evento atualizado."
    except Exception as e:
        return f"Erro ao atualizar: {e}"

# --- 2. DOCS: CRIAR E LER ---

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

def read_google_doc(user_id: str, doc_id: str):
    """Lê o texto completo de um Google Doc."""
    service = get_service(user_id, 'docs', 'v1')
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        full_text = ""
        for element in content:
            if 'paragraph' in element:
                elements = element.get('paragraph').get('elements')
                for elem in elements:
                    full_text += elem.get('textRun', {}).get('content', '')
        return f"Conteúdo do Doc:\n{full_text[:3000]}..."
    except Exception as e:
        return f"Erro ao ler doc: {e}"

# --- 3. DRIVE: BUSCAR ARQUIVO ---

def search_drive_file(user_id: str, query_name: str):
    service = get_service(user_id, 'drive', 'v3')
    try:
        q = f"name contains '{query_name}' and trashed = false"
        results = service.files().list(q=q, pageSize=5, fields="files(id, name, webViewLink)").execute()
        items = results.get('files', [])

        if not items: return f"Nenhum arquivo encontrado com nome '{query_name}'."

        resp = "Arquivos encontrados:\n"
        for item in items:
            resp += f"- {item['name']} (ID: {item['id']})\n  Link: {item['webViewLink']}\n"
        return resp
    except Exception as e:
        return f"Erro Drive: {e}"

# --- 4. TASKS ---

def create_task(user_id: str, title: str, notes: str = None):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        body = {'title': title, 'notes': notes}
        task = service.tasks().insert(tasklist='@default', body=body).execute()
        return f"Tarefa criada: {task['title']}"
    except Exception as e:
        return f"Erro Tasks: {e}"

def list_tasks(user_id: str):
    service = get_service(user_id, 'tasks', 'v1')
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=False, maxResults=10).execute()
        items = results.get('items', [])
        if not items: return "Nenhuma tarefa pendente."
        
        resp = "Minhas Tarefas:\n"
        for item in items:
            resp += f"☐ {item['title']}\n"
        return resp
    except Exception as e:
        return f"Erro Tasks: {e}"

# --- 5. GMAIL ---

def get_unread_emails(user_id: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages: return "Você não tem novos emails."

        resp = "📩 Últimos emails não lidos:\n"
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = m['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
            resp += f"- De: {sender} | Assunto: {subject}\n"
        return resp
    except Exception as e:
        return f"Erro Gmail: {e}"

def create_email_draft(user_id: str, to: str, subject: str, body_text: str):
    service = get_service(user_id, 'gmail', 'v1')
    try:
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': encoded_message}}
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        return f"Rascunho criado com sucesso! ID: {draft['id']} (Verifique seu Gmail)"
    except Exception as e:
        return f"Erro ao criar rascunho: {e}"