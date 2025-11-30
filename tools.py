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

# --- 1. AGENDA ---

def list_calendar_events(user_id: str, date_str: str = None, days: int = 1):
    """Lista eventos trazendo links do Calendar e do Meet."""
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    try:
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
            
            # Links
            link_cal = event.get('htmlLink', '')
            link_meet = event.get('hangoutLink', '') # Pega link do Meet se houver
            
            data_evento = start[:10]
            hora_evento = start[11:16] if 'T' in start else "Dia todo"
            
            agenda_str += f"- [{data_evento} às {hora_evento}] {summary}\n"
            
            if link_meet:
                agenda_str += f"  📹 Meet: {link_meet}\n"
            if link_cal:
                agenda_str += f"  📅 Detalhes: {link_cal}\n"
            
        return agenda_str

    except Exception as e:
        return f"Erro ao ler agenda: {str(e)}"

def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None, attendees_emails: list[str] = None, description: str = None):
    service = get_service(user_id, 'calendar', 'v3')
    if not service: return "ERRO: Falha de autenticação."

    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido (Use ISO ex: 2025-11-20T14:00:00)."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'},
        'conferenceData': {
            'createRequest': {'requestId': f"sample{datetime.datetime.now().timestamp()}", 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}
        }
    }

    if description: event_body['description'] = description

    if attendees_emails:
        valid_attendees = []
        for email in attendees_emails:
            if isinstance(email, str) and "@" in email:
                valid_attendees.append({'email': email.strip()})
        if valid_attendees:
            event_body['attendees'] = valid_attendees

    try:
        # conferenceDataVersion=1 é obrigatório para criar link do Meet automático
        event = service.events().insert(calendarId='primary', body=event_body, conferenceDataVersion=1).execute()
        
        link_cal = event.get('htmlLink')
        link_meet = event.get('hangoutLink', 'Sem link do Meet')
        
        return f"✅ Evento Criado: '{summary}'\n📅 Agenda: {link_cal}\n📹 Meet: {link_meet}"
    except Exception as e:
        return f"Erro do Google Agenda: {str(e)}"

def delete_calendar_event(user_id: str, event_id: str):
    service = get_service(user_id, 'calendar', 'v3')
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Evento removido com sucesso."
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
        except: return "Erro: Data inválida."

    try:
        event = service.events().patch(calendarId='primary', eventId=event_id, body=event_patch).execute()
        link = event.get('htmlLink')
        return f"✅ Evento Atualizado.\n🔗 Link: {link}"
    except Exception as e:
        return f"Erro ao atualizar: {e}"

# --- 2. DOCS ---

def create_google_doc(title: str, content: str, user_id: str):
    docs_service = get_service(user_id, 'docs', 'v1')
    if not docs_service: return "Erro autenticação Docs."

    try:
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        link = f"https://docs.google.com/document/d/{doc_id}"
        return f"✅ Documento Criado: '{title}'\n🔗 Link: {link}"
    except Exception as e:
        return f"Erro Doc: {str(e)}"

def read_google_doc(user_id: str, doc_id: str):
    service = get_service(user_id, 'docs', 'v1')
