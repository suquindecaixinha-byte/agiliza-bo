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

# --- FERRAMENTA 1: AGENDA ---
def create_calendar_event(summary: str, start_datetime: str, user_id: str, end_datetime: str = None):
    """
    Cria um evento na agenda PRINCIPAL do usuário autenticado.
    Note que agora pedimos 'user_id' em vez de 'user_email'.
    """
    print(f"🔧 [TOOLS] Agendando '{summary}' para usuário ID: {user_id}")
    
    service = get_service(user_id, 'calendar', 'v3')
    
    if not service:
        return "Erro: Você não está conectado à sua conta Google. Por favor, faça o login clicando no link de conexão."

    if not end_datetime:
        try:
            dt = datetime.datetime.fromisoformat(start_datetime)
            end_datetime = (dt + datetime.timedelta(hours=1)).isoformat()
        except ValueError:
            return "Erro: Formato de data inválido. O cérebro enviou algo errado."

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'}
    }

    try:
        # MUDANÇA CRUCIAL: calendarId='primary'
        # Como estamos logados COMO o usuário, 'primary' é a agenda dele.
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        print(f"✅ [TOOLS] Agenda Sucesso: {link}")
        return f"Agendado com sucesso! Link: {link}"
        
    except Exception as e:
        print(f"❌ [TOOLS] Erro Agenda: {e}")
        return f"O Google recusou o agendamento. Detalhe: {str(e)}"

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