import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from auth import load_user_credentials  # Importamos a função do arquivo auth.py

# --- FUNÇÃO AUXILIAR (Para não repetir código) ---
def get_service(user_id, api_name, version):
    """
    Recupera as credenciais do usuário, renova o token se necessário
    e retorna o cliente da API pronto para uso.
    """
    creds = load_user_credentials(user_id)
    
    if not creds:
        print(f"⚠️ [TOOLS] Usuário {user_id} não tem credenciais válidas.")
        return None

    # Se o token venceu, tenta renovar automaticamente
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 [TOOLS] Token renovado para o usuário {user_id}")
        except Exception as e:
            print(f"❌ [TOOLS] Erro ao renovar token: {e}")
            return None

    return build(api_name, version, credentials=creds)

def list_calendar_events(user_id: str, date_str: str = None):
    """
    Lista os eventos de um dia específico para ver o que está ocupado.
    Se date_str não for informado, usa hoje. Formato date_str: 'YYYY-MM-DD'.
    """
    print(f"🔧 [TOOLS] Listando eventos para {user_id} na data {date_str}")
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "Erro: Usuário não conectado."

    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
        # Define o intervalo do dia inteiro (00:00 até 23:59:59)
        start_of_day = f"{date_str}T00:00:00-03:00" # Fuso horário Brasil
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
            # Pega só a hora (HH:MM) para simplificar pro Gemini
            start_time = start[11:16] if 'T' in start else "Dia todo"
            agenda_str += f"- {start_time}: {event['summary']}\n"
            
        return agenda_str

    except Exception as e:
        print(f"❌ [TOOLS] Erro ao listar: {e}")
        return f"Erro ao ler agenda: {str(e)}"


# --- FERRAMENTA ATUALIZADA: CRIAR EVENTO COM CONVIDADOS ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None):
    """
    Cria evento na agenda principal. 
    Agora aceita uma lista opcional de emails para convidar (attendees_emails).
    """
    print(f"🔧 [TOOLS] Agendando '{summary}' para {user_id}. Convidados: {attendees_emails}")
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "Erro: Usuário não conectado."

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

    # --- NOVIDADE: ADICIONA CONVIDADOS ---
    if attendees_emails:
        attendees_list = [{'email': email.strip()} for email in attendees_emails]
        event_body['attendees'] = attendees_list
    # -------------------------------------

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

# --- FERRAMENTA 2: GOOGLE DOCS ---
def create_google_doc(title: str, content: str, user_id: str):
    """
    Cria um Doc DIRETAMENTE no Drive do usuário.
    Não precisa mais compartilhar link público, pois o dono é o próprio usuário!
    """
    print(f"🔧 [TOOLS] Criando Doc '{title}' para usuário ID: {user_id}")
    
    # Precisamos de dois serviços: Docs (para editar) e Drive (para pegar o link bonito)
    docs_service = get_service(user_id, 'docs', 'v1')
    if not docs_service:
        return "Erro: Falha de autenticação. Usuário não conectado."

    try:
        # 1. Cria o Doc
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')

        # 2. Insere o conteúdo
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        # MUDANÇA: Não precisamos mais de 'drive_service.permissions'
        # O arquivo já nasce privado e pertencente ao usuário.
        
        link = f"https://docs.google.com/document/d/{doc_id}"
        print(f"✅ [TOOLS] Doc Finalizado: {link}")
        return f"Documento criado no seu Drive: {link}"

    except Exception as e:
        print(f"❌ [TOOLS] Erro Doc: {e}")
        return f"Erro ao criar documento: {str(e)}"