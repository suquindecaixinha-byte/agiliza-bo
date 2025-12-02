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
    if not creds: return None
        
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # NOTA: Idealmente aqui você deveria salvar as credenciais renovadas no Supabase
        except Exception:
            return None
            
    return build(api_name, version, credentials=creds)

# --- 1. AGENDA ---

def list_calendar_events(user_id: str, date_str: str = None, days: int = 1):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "SYSTEM_ERROR: Falha de autenticação."

    if not date_str: date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
        dt_start = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dt_end = dt_start + datetime.timedelta(days=days)
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=f"{date_str}T00:00:00-03:00",
            timeMax=f"{dt_end.strftime('%Y-%m-%d')}T23:59:59-03:00",
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events: return f"Agenda livre entre {date_str} e {dt_end.strftime('%Y-%m-%d')}."

        agenda_str = f"Agenda ({date_str} até {dt_end.strftime('%Y-%m-%d')}):\n"
        seen_events = set()
        
        for event in events:
            if event['id'] in seen_events: continue
            seen_events.add(event['id'])
            
            summary = event.get('summary', 'Sem título')
            start = event['start'].get('dateTime', event['start'].get('date'))
            link_meet = event.get('hangoutLink', '') 
            
            data_evento = start[:10]
            hora_evento = start[11:16] if 'T' in start else "Dia todo"
            
            agenda_str += f"- [{data_evento} {hora_evento}] {summary}"
            if link_meet: agenda_str += f" (Link Meet: {link_meet})"
            agenda_str += "\n"
            
        return agenda_str

    except Exception as e: return f"SYSTEM_ERROR: Erro ao ler agenda: {str(e)}"

def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "SYSTEM_ERROR: Falha de autenticação."

    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError: return "SYSTEM_ERROR: Data inválida."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'},
        'conferenceData': { 
            'createRequest': {'requestId': f"req{datetime.datetime.now().timestamp()}", 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}
        }
    }

    if description: event_body['description'] = description
    if attendees_emails:
        valid = [{'email': e.strip()} for e in attendees_emails if "@" in e]
        if valid: event_body['attendees'] = valid

    try:
        event = service.events().insert(calendarId='primary', body=event_body, conferenceDataVersion=1).execute()
        
        link_meet = event.get('hangoutLink', 'Não gerado')
        link_cal = event.get('htmlLink', '')

        # RETORNO PADRONIZADO PARA EVITAR ALUCINAÇÃO
        return (
            f"SYSTEM_CONFIRMATION: Evento criado com sucesso.\n"
            f"URL REAL MEET: {link_meet}\n"
            f"URL REAL CALENDAR: {link_cal}\n"
            f"INSTRUÇÃO: Confirme o agendamento ao usuário e apresente os links acima."
        )
    except Exception as e: return f"SYSTEM_ERROR: Erro API Google: {str(e)}"

# --- 2. DOCS (CORREÇÃO PRINCIPAL AQUI) ---

def create_google_doc(title: str, content: str, user_id: str):
    docs_service = get_service(user_id, 'docs', 'v1')
    if not docs_service: return "SYSTEM_ERROR: Erro autenticação Docs."

    try:
        # 1. Cria o arquivo vazio
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        # 2. Insere o conteúdo
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        link = f"https://docs.google.com/document/d/{doc_id}"
        
        # RETORNO PADRONIZADO E RIGÍDO
        return (
            f"SYSTEM_CONFIRMATION: Documento criado com sucesso.\n"
            f"TÍTULO: {title}\n"
            f"URL REAL (Use apenas esta): {link}\n"
            f"INSTRUÇÃO: Responda ao usuário dizendo 'Criei a ata: [Titulo]' e forneça o link."
        )
    except Exception as e: return f"SYSTEM_ERROR: Falha ao criar Doc: {str(e)}"

def read_google_doc(user_id: str, doc_id: str):
    service = get_service(user_id, 'docs', 'v1')
    if not service: return "SYSTEM_ERROR: Erro auth Docs."
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        full_text = ""
        for element in content:
            if 'paragraph' in element:
                for elem in element.get('paragraph').get('elements'):
                    full_text += elem.get('textRun', {}).get('content', '')
        return f"Conteúdo do Doc (Resumo):\n{full_text[:2000]}..."
    except Exception as e: return f"SYSTEM_ERROR: Erro ao ler doc: {e}"

# --- 3. DRIVE ---

def search_drive_file(user_id: str, query_name: str):
    service = get_service(user_id, 'drive', 'v3')
    if not service: return "SYSTEM_ERROR: Erro auth Drive."
    try:
        q = f"name contains '{query_name}' and trashed = false"
        results = service.files().list(q=q, pageSize=5, fields="files(id, name, webViewLink)").execute()
        items = results.get('files', [])

        if not items: return f"Nenhum arquivo encontrado com nome '{query_name}'."

        resp = "Arquivos encontrados (MOSTRE OS LINKS REAIS ABAIXO):\n"
        for item in items:
            resp += f"- {item['name']} -> Link: {item['webViewLink']}\n"
        return resp
    except Exception as e: return f"SYSTEM_ERROR: Erro Drive: {e}"

# --- 4. TASKS & GMAIL ---

def create_task(user_id: str, title: str, notes: str = None):
    service = get_service(user_id, 'tasks', 'v1')
    if not service: return "SYSTEM_ERROR: Erro auth Tasks."
    try:
        body = {'title': title, 'notes': notes}
        task = service.tasks().insert(tasklist='@default', body=body).execute()
        return f"SYSTEM_CONFIRMATION: Tarefa '{task['title']}' criada no Google Tasks."
    except Exception as e: return f"SYSTEM_ERROR: Erro Tasks: {e}"

def list_tasks(user_id: str):
    service = get_service(user_id, 'tasks', 'v1')
    if not service: return "SYSTEM_ERROR: Erro auth Tasks."
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=False, maxResults=10).execute()
        items = results.get('items', [])
        if not items: return "Nenhuma tarefa pendente."
        return "Minhas Tarefas:\n" + "\n".join([f"☐ {i['title']}" for i in items])
    except Exception as e: return f"SYSTEM_ERROR: Erro Tasks: {e}"

def get_unread_emails(user_id: str):
    service = get_service(user_id, 'gmail', 'v1')
    if not service: return "SYSTEM_ERROR: Erro auth Gmail."
    try:
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
        messages = results.get('messages', [])
        if not messages: return "Sem novos emails."

        resp = "📩 Emails não lidos (MOSTRE OS LINKS REAIS):\n"
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = m['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
            link = f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}"
            resp += f"- {sender}: {subject} -> {link}\n"
        return resp
    except Exception as e: return f"SYSTEM_ERROR: Erro Gmail: {e}"

def create_email_draft(user_id: str, to: str, subject: str, body_text: str):
    service = get_service(user_id, 'gmail', 'v1')
    if not service: return "SYSTEM_ERROR: Erro auth Gmail."
    try:
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to
        message['Subject'] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': encoded}}
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        link = "https://mail.google.com/mail/u/0/#drafts"
        
        return f"SYSTEM_CONFIRMATION: Rascunho criado. Link: {link}"
    except Exception as e: return f"SYSTEM_ERROR: Erro Rascunho: {e}"

def delete_calendar_event(user_id: str, event_id: str):
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "SYSTEM_CONFIRMATION: Evento removido."
    except Exception as e: return f"SYSTEM_ERROR: Erro delete: {e}"

def update_calendar_event(user_id: str, event_id: str, new_summary: str = None, new_start_time: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    patch = {}
    if new_summary: patch['summary'] = new_summary
    if new_start_time:
        try:
            dt = datetime.datetime.fromisoformat(new_start_time)
            patch['start'] = {'dateTime': new_start_time}
            patch['end'] = {'dateTime': (dt + datetime.timedelta(hours=1)).isoformat()}
        except: return "SYSTEM_ERROR: Data inválida."
    try:
        service.events().patch(calendarId='primary', eventId=event_id, body=patch).execute()
        return "SYSTEM_CONFIRMATION: Evento atualizado."
    except Exception as e: return f"SYSTEM_ERROR: Erro update: {e}"
