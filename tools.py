import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from auth import load_user_credentials

# --- FUNÇÃO AUXILIAR ---
def get_service(user_id, api_name, version):
    """Recupera credenciais e retorna o cliente da API."""
    
    # --- DEBUG CRÍTICO: Mostra no terminal o que a IA enviou ---
    print(f"🔍 [TOOLS DEBUG] Tentando obter serviço para user_id: '{user_id}' (Tipo: {type(user_id)})")
    
    if not user_id or user_id == "user_id" or user_id == "SYSTEM_ID":
        print(f"❌ [TOOLS] Erro: A IA enviou um ID inválido: {user_id}")
        return None

    creds = load_user_credentials(user_id)
    if not creds:
        print(f"⚠️ [TOOLS] Credenciais não encontradas no banco para ID: {user_id}")
        return None
        
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 [TOOLS] Token renovado para {user_id}")
        except Exception as e:
            print(f"❌ [TOOLS] Erro refresh token: {e}")
            return None
            
    return build(api_name, version, credentials=creds)

# --- LISTAR EVENTOS ---
def list_calendar_events(user_id: str, date_str: str = None):
    """
    Lista os eventos de um dia específico.
    user_id: O ID numérico do usuário (string). OBRIGATÓRIO.
    """
    service = get_service(user_id, 'calendar', 'v3')
    if not service: 
        return "ERRO CRÍTICO: Não foi possível autenticar. Verifique se o user_id passado está correto e se o usuário está logado."

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
        print(f"❌ [TOOLS] Erro ao listar: {e}")
        return f"Erro ao ler agenda: {str(e)}"

# --- CRIAR EVENTO ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None):
    """
    Cria evento na agenda.
    user_id: O ID numérico do usuário (string). OBRIGATÓRIO.
    """
    service = get_service(user_id, 'calendar', 'v3')
    if not service: 
        return "ERRO CRÍTICO: Falha de autenticação (user_id inválido ou não logado)."

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
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        print(f"✅ [TOOLS] Agenda Sucesso: {link}")
        
        invite_text = ""
        if attendees_emails:
            invite_text = f" Convites enviados para: {', '.join(attendees_emails)}."
            
        return f"Agendado com sucesso!{invite_text} Link: {link}"
        
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"Erro do Google: {str(e)}"

# --- CRIAR DOC ---
def create_google_doc(title: str, content: str, user_id: str):
    """
    Cria documento no Drive.
    user_id: O ID numérico do usuário (string). OBRIGATÓRIO.
    """
    # Precisamos de dois serviços: Docs (editar) e Drive (permissões/link)
    docs_service = get_service(user_id, 'docs', 'v1')
    if not docs_service: return "Erro: Falha de autenticação no Docs."

    try:
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')

        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        link = f"https://docs.google.com/document/d/{doc_id}"
        return f"Documento criado no seu Drive: {link}"

    except Exception as e:
        print(f"❌ [TOOLS] Erro Doc: {e}")
        return f"Erro ao criar documento: {str(e)}"
