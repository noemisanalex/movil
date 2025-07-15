import datetime
import os.path
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly", "https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/data/data/com.termux/files/home/agp/credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "/data/data/com.termux/files/home/agp/token.json")

# Injected by the main script
hablar = print
logging.basicConfig(level=logging.INFO)


def get_calendar_service():
    """Devuelve un objeto de servicio de la API de Google Calendar autenticado."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Error al refrescar el token: {e}")
                hablar("Tu sesión de Google ha expirado. Por favor, autoriza de nuevo.")
                os.remove(TOKEN_FILE)
                return get_calendar_service() # Llama recursivamente para re-autenticar
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                hablar("Falta el archivo credentials.json. Por favor, descárgalo desde la Consola de APIs de Google y colócalo en la raíz del proyecto.")
                return None
            
            hablar("Necesito que autorices el acceso a tu calendario de Google.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Redirigir al usuario a una URL específica para la autenticación
            auth_url, _ = flow.authorization_url(prompt='consent')
            hablar(f"Por favor, ve a esta URL para autorizar: {auth_url}")
            hablar("Después de autorizar, pega el código que recibas aquí en la consola.")
            
            # En un entorno real, aquí se detendría para esperar la entrada del usuario.
            # Para este CLI, asumimos que el usuario pegará el código en la terminal.
            # El flujo se completaría con ese código.
            # Como no podemos pausar y esperar input aquí, esta es una limitación.
            # La solución real sería manejar esto en el bucle principal de la aplicación.
            # Por ahora, solo informamos al usuario.
            return None 

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        logging.error(f"Ocurrió un error al construir el servicio: {error}")
        hablar("No se pudo conectar con la API de Google Calendar.")
        return None

def list_upcoming_events():
    """Lista los próximos 10 eventos en el calendario principal del usuario."""
    service = get_calendar_service()
    if not service:
        return "El servicio de calendario no está disponible."

    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indica UTC
    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return "No tienes próximos eventos."

        response = "Tus próximos eventos son:\n"
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            response += f"- {start}: {event['summary']}\n"
        return response

    except HttpError as error:
        logging.error(f"Ocurrió un error en la API de Calendar: {error}")
        return "Lo siento, no pude obtener tus eventos del calendario."

def create_event(summary, start_time_str, end_time_str=None):
    """Crea un nuevo evento en el calendario."""
    service = get_calendar_service()
    if not service:
        return "El servicio de calendario no está disponible."

    # Aquí necesitaríamos una lógica robusta para parsear fechas y horas del lenguaje natural.
    # Por simplicidad, este ejemplo espera un formato específico como "YYYY-MM-DDTHH:MM:SS".
    # Ejemplo: "2025-12-31T10:00:00"
    
    try:
        start_time = datetime.datetime.fromisoformat(start_time_str)
        if end_time_str:
            end_time = datetime.datetime.fromisoformat(end_time_str)
        else:
            end_time = start_time + datetime.timedelta(hours=1)

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Los_Angeles', # Debería ser configurable
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Evento creado: {created_event.get('htmlLink')}"

    except (HttpError, ValueError) as error:
        logging.error(f"Error al crear el evento: {error}")
        return "Lo siento, no pude crear el evento. Asegúrate de que el formato de fecha y hora sea correcto."


def handle_command(command):
    """Maneja los comandos de voz para el plugin de calendario."""
    if "cuáles son mis próximos eventos" in command or "qué tengo en mi calendario" in command:
        return list_upcoming_events()
    
    # Ejemplo de cómo podría funcionar la creación de eventos (requiere parsing avanzado)
    # "crea un evento llamado 'Reunión de equipo' para mañana a las 10am"
    # Esto necesitaría una librería de NLP para extraer 'Reunión de equipo', la fecha y la hora.
    # Por ahora, no implementaremos el NLP completo aquí.
    
    return None
