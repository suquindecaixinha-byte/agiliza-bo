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


# --- CRIAR EVENTO (ATUALIZADO: Com Descrição) ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    """
    Cria evento. 
    - summary: Título do evento.
    - description: Detalhes extras (ex: 'Encontrar com João'). Útil quando não se tem o e-mail.
    """
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido."

def delete_calendar_event(user_id: str, event_id: str):
    """Remove um evento pelo ID (O ID é mostrado na listagem)."""
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Evento removido com sucesso."
    except Exception as e:
        return f"Erro ao deletar: {e}"

def update_calendar_event(user_id: str, event_id: str, new_summary: str = None, new_start_time: str = None):
    """Atualiza título ou horário de um evento existente."""
    service = get_service(user_id, 'calendar', 'v3')
    
    event_patch = {}
    if new_summary:
        event_patch['summary'] = new_summary
        
    if new_start_time:
        # Assume duração de 1h se mudar o horário
        try:
            dt = datetime.datetime.fromisoformat(new_start_time)
            end_time = (dt + datetime.timedelta(hours=1)).isoformat()
            event_patch['start'] = {'dateTime': new_start_time, 'timeZone': 'America/Sao_Paulo'}
            event_patch['end'] = {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'}
        except:
            return "Erro: Formato de data inválido (Use ISO)."

    try:
        service.events().patch(calendarId='primary', eventId=event_id, body=event_patch).execute()
        return "Evento atualizado com sucesso."
    except Exception as e:
        return f"Erro ao atualizar: {e}"
# --- LISTAR EVENTOS (CORRIGIDO: REMOVE DUPLICATAS) ---
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
            singleEvents=True, # Isso expande eventos recorrentes (importante)
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"Agenda livre para o dia {date_str}."

        agenda_str = f"Agenda para {date_str}:\n"
        
        # --- FILTRO ANTI-DUPLICIDADE ---
        seen_events = set() # Conjunto para guardar IDs processados
        
        for event in events:
            # O Google às vezes retorna o mesmo evento base se houver exceções
            # Usamos o ID do evento para garantir unicidade
            event_id = event['id']
            
            if event_id in seen_events:
                continue # Pula se já vimos este evento
            
            seen_events.add(event_id)
            
            summary = event.get('summary', 'Sem título')
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            # Formatação de hora mais limpa
            start_time = start[11:16] if 'T' in start else "Dia todo"
            
            agenda_str += f"- {start_time}: {summary}\n"
            
        return agenda_str

    except Exception as e:
        return f"Erro ao ler agenda: {str(e)}"
    
    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
    }

    # Adiciona a descrição se houver
    if description:
        event_body['description'] = description

    # Lógica de convidados (Só adiciona se for e-mail válido)
    if attendees_emails:
        valid_attendees = []
        for email in attendees_emails:
            if isinstance(email, str) and "@" in email and "." in email:
                clean_email = email.strip()
                if clean_email:
                    valid_attendees.append({'email': clean_email})
        
        if valid_attendees:
            event_body['attendees'] = valid_attendees

    try:
        try:
            calendar_info = service.calendars().get(calendarId='primary').execute()
            saved_email = calendar_info.get('id', 'primary')
        except:
            saved_email = "Agenda Principal"

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        
        invite_msg = ""
        if attendees_emails and 'attendees' in event_body:
            invite_msg = f" (Convite enviado para {len(event_body['attendees'])} pessoas)"
        elif attendees_emails:
            invite_msg = " (Nenhum e-mail válido, nomes salvos na descrição)"

        return f"Sucesso! Evento '{summary}' criado em {saved_email}.{invite_msg} Link: {link}"
        
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"Erro do Google: {str(e)}"
# --- DOCS 
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
        return f"Conteúdo do Doc:\n{full_text[:3000]}..." # Limite para não estourar contexto
    except Exception as e:
        return f"Erro ao ler doc: {e}"

# --- 3. DRIVE: BUSCAR ARQUIVO ---

def search_drive_file(user_id: str, query_name: str):
    """Procura arquivos no Drive pelo nome e retorna ID e Link."""
    service = get_service(user_id, 'drive', 'v3')
    try:
        # Busca arquivos que não estão na lixeira e contém o nome
        q = f"name contains '{query_name}' and trashed = false"
        results = service.files().list(q=q, pageSize=5, fields="nextPageToken, files(id, name, webViewLink)").execute()
        items = results.get('files', [])

        if not items:
            return f"Nenhum arquivo encontrado com o nome '{query_name}'."

        resp = "Arquivos encontrados:\n"
        for item in items:
            resp += f"- {item['name']} (ID: {item['id']})\n  Link: {item['webViewLink']}\n"
        return resp
    except Exception as e:
        return f"Erro na busca do Drive: {e}"

# --- 4. TASKS: LISTAR E CRIAR ---

def create_task(user_id: str, title: str, notes: str = None):
    """Cria uma tarefa no Google Tasks (Lista padrão)."""
    service = get_service(user_id, 'tasks', 'v1')
    try:
        body = {'title': title, 'notes': notes}
        task = service.tasks().insert(tasklist='@default', body=body).execute()
        return f"Tarefa criada: {task['title']}"
    except Exception as e:
        return f"Erro Tasks: {e}"

def list_tasks(user_id: str):
    """Lista tarefas pendentes."""
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

# --- 5. GMAIL: LER E RASCUNHAR (SEM ENVIAR) ---

def get_unread_emails(user_id: str):
    """Lista os últimos 5 emails não lidos."""
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
    """Cria um RASCUNHO no Gmail (o usuário revisa e envia depois)."""
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



