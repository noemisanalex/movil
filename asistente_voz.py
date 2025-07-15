import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import os
import subprocess
import threading
import queue
import json
import importlib.util
import sys
import logging
import requests
import re
import datetime
import time
import socket
from dotenv import load_dotenv

# --- Bloqueo de instancia única ---
LOCK_FILE = os.path.join(os.path.dirname(__file__), ".assistant_lock")

def is_already_running():
    return os.path.exists(LOCK_FILE)

def create_lock_file():
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_lock_file():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración del logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler para la consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Handler para el archivo
file_handler = logging.FileHandler('errores.log', mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)

# Configuración del logger principal
logger = logging.getLogger()
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

def _load_config():
    config = {
        "USER_DATA_FILE": os.getenv("USER_DATA_FILE", os.path.join(os.path.dirname(__file__), "user_data.json")),
        "CUSTOM_COMMANDS_FILE": os.getenv("CUSTOM_COMMANDS_FILE", os.path.join(os.path.dirname(__file__), "custom_commands.json")),
        "HA_URL": os.getenv("HA_URL", "http://localhost:8123"),
        "HA_TOKEN": os.getenv("HA_TOKEN"),
        "MCP_GITHUB_SERVER_URL": os.getenv("MCP_GITHUB_SERVER_URL", "http://localhost:8080"),
        "GITHUB_PAT": os.getenv("GITHUB_PAT"),
        "SPEECH_RECOGNITION_PAUSE_THRESHOLD": float(os.getenv("SPEECH_RECOGNITION_PAUSE_THRESHOLD", 0.8)),
        "SPEECH_RECOGNITION_PHRASE_TIME_LIMIT": int(os.getenv("SPEECH_RECOGNITION_PHRASE_TIME_LIMIT", 8)),
        "SPEECH_RECOGNITION_TIMEOUT": int(os.getenv("SPEECH_RECOGNITION_TIMEOUT", 10)),
        "SPEECH_RECOGNITION_LANGUAGE": os.getenv("SPEECH_RECOGNITION_LANGUAGE", "es-ES"),
        "TTS_LANGUAGE": os.getenv("TTS_LANGUAGE", "es"),
        "MAX_HISTORY_LENGTH": int(os.getenv("MAX_HISTORY_LENGTH", 10)),
        "PLUGINS_DIR": os.getenv("PLUGINS_DIR", os.path.join(os.path.dirname(__file__), "plugins"))
    }
    return config

def check_internet_connection(hostname="8.8.8.8"):
    """Checks for a stable internet connection by trying to resolve and connect to a hostname."""
    try:
        # see if we can resolve the host name -- tells us if there is a DNS listening
        host = socket.gethostbyname(hostname)
        # connect to the host -- tells us if the host is actually reachable
        s = socket.create_connection((host, 53), timeout=3)
        s.close()
        logging.info("Conexión a internet confirmada.")
        return True
    except (socket.error, socket.gaierror) as ex:
        logging.warning(f"No se detectó conexión a internet: {ex}")
        return False

# Cargar configuración global
CONFIG = _load_config()

# Cola para la comunicación entre el hilo de escucha y el hilo principal
q_input = queue.Queue()
q_output = queue.Queue()

# Global variable to store information about the last executed command
last_executed_command_info = {}

# Mensajes de error centralizados
ERROR_MESSAGES = {
    "speech_recognition_unknown": "No pude entender lo que dijiste. Por favor, inténtalo de nuevo.",
    "speech_recognition_service": "Hubo un problema con el servicio de reconocimiento de voz. Asegúrate de tener conexión a internet.",
    "speech_recognition_unexpected": "Ocurrió un error inesperado al escuchar. Por favor, inténtalo de nuevo.",
    "tts_playback_error": "Lo siento, no pude reproducir el audio de la respuesta.",
    "tts_save_error": "No pude guardar el archivo de audio para la respuesta.",
    "gemini_cli_error": "Lo siento, hubo un error al comunicarme con Gemini. Por favor, revisa la consola para más detalles.",
    "gemini_cli_not_found": "El comando de Gemini no se encontró. Asegúrate de que Gemini CLI esté instalado y en tu PATH.",
    "plugin_error": "Ocurrió un error en uno de los plugins. Por favor, revisa la consola para más detalles.",
    "n8n_webhook_failed": "Lo siento, no pude activar la automatización en n8n. Revisa la configuración del webhook.",
    "ha_service_failed": "Lo siento, no pude realizar la acción en Home Assistant. Revisa la configuración y los logs.",
    "ha_state_failed": "Lo siento, no pude obtener la información de Home Assistant. Revisa la configuración y los logs.",
    "user_data_corrupt": "El archivo de datos de usuario está corrupto. Se ha creado uno nuevo.",
    "custom_commands_corrupt": "El archivo de comandos personalizados está corrupto. Se ha ignorado.",
    "mcp_request_failed": "Lo siento, hubo un error al comunicarme con el servidor MCP. Revisa la configuración y los logs.",
    "general_unexpected_error": "Lo siento, ocurrió un error inesperado."
}

# --- Home Assistant Integration ---

def call_ha_service(domain, service, entity_id=None, data=None):
    HA_HEADERS = {
        "Authorization": f"Bearer {CONFIG["HA_TOKEN"]}",
        "Content-Type": "application/json",
    }
    url = f"{CONFIG["HA_URL"]}/api/services/{domain}/{service}"
    payload = {}
    if entity_id:
        payload["entity_id"] = entity_id
    if data:
        payload.update(data)

    try:
        response = requests.post(url, headers=HA_HEADERS, json=payload)
        response.raise_for_status()
        logging.info(f"Llamada a HA exitosa: {domain}.{service} para {entity_id}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al llamar al servicio de Home Assistant ({domain}.{service}): {e}")
        hablar(ERROR_MESSAGES["ha_service_failed"])
        return False

def get_ha_state(entity_id):
    HA_HEADERS = {
        "Authorization": f"Bearer {CONFIG["HA_TOKEN"]}",
        "Content-Type": "application/json",
    }
    url = f"{CONFIG["HA_URL"]}/api/states/{entity_id}"
    try:
        response = requests.get(url, headers=HA_HEADERS)
        response.raise_for_status()
        state_data = response.json()
        logging.info(f"Estado de HA obtenido para {entity_id}: {state_data.get('state')}")
        return state_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener el estado de Home Assistant para {entity_id}: {e}")
        hablar(ERROR_MESSAGES["ha_state_failed"])
        return None
# --- End Home Assistant Integration ---

# --- MCP Integration ---

def send_mcp_request(method, params=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CONFIG["GITHUB_PAT"]}" # Usar PAT para autenticación
    }
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params if params is not None else {},
        "id": 1 # Un ID de solicitud, puede ser incremental
    }
    try:
        response = requests.post(CONFIG["MCP_GITHUB_SERVER_URL"], headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            logging.error(f"Error en la respuesta del servidor MCP: {result['error']}")
            hablar(ERROR_MESSAGES["mcp_request_failed"])
            return None
        logging.info(f"Solicitud MCP exitosa para método {method}")
        return result.get("result")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al enviar solicitud al servidor MCP ({CONFIG["MCP_GITHUB_SERVER_URL"]}): {e}")
        hablar(ERROR_MESSAGES["mcp_request_failed"])
        return None
# --- End MCP Integration ---

def load_user_data():
    if os.path.exists(CONFIG["USER_DATA_FILE"]):
        with open(CONFIG["USER_DATA_FILE"], 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.warning(f"Archivo de datos de usuario corrupto: {CONFIG['USER_DATA_FILE']}. Se creará uno nuevo.")
                hablar(ERROR_MESSAGES["user_data_corrupt"])
                return {}
    return {}

def save_user_data(data):
    with open(CONFIG["USER_DATA_FILE"], 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_custom_commands():
    if os.path.exists(CONFIG["CUSTOM_COMMANDS_FILE"]):
        with open(CONFIG["CUSTOM_COMMANDS_FILE"], 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.warning(f"Archivo de comandos personalizados corrupto: {CONFIG['CUSTOM_COMMANDS_FILE']}. Se ignorará.")
                hablar(ERROR_MESSAGES["custom_commands_corrupt"])
                return {}
    return {}

class AudioInputHandler:
    def __init__(self, config):
        self.recognizer = sr.Recognizer()
        self.config = config
        self.recognizer.pause_threshold = config["SPEECH_RECOGNITION_PAUSE_THRESHOLD"]
        
        # Ajustar para el ruido ambiental una sola vez al inicio
        with sr.Microphone() as source:
            logging.info("Ajustando para ruido ambiental... Por favor, espere.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logging.info(f"Ajuste de ruido ambiental completo. Umbral de energía dinámico: {self.recognizer.energy_threshold:.2f}")

    def escuchar(self):
        with sr.Microphone() as source:
            logging.info("Escuchando...")
            try:
                audio = self.recognizer.listen(
                    source,
                    phrase_time_limit=self.config["SPEECH_RECOGNITION_PHRASE_TIME_LIMIT"],
                    timeout=self.config["SPEECH_RECOGNITION_TIMEOUT"]
                )
                logging.info("Audio capturado, procesando con Google Speech Recognition...")
                texto = self.recognizer.recognize_google(audio, language=self.config["SPEECH_RECOGNITION_LANGUAGE"])
                logging.info(f"Texto reconocido: '{texto}'")
                return texto
            except sr.WaitTimeoutError:
                logging.warning("Tiempo de espera agotado. No se detectó voz.")
                return ""
            except sr.UnknownValueError:
                logging.warning("Google Speech Recognition no pudo entender el audio.")
                hablar(ERROR_MESSAGES["speech_recognition_unknown"])
                return ""
            except sr.RequestError as e:
                logging.error(f"Error en la solicitud a Google Speech Recognition; {e}")
                if not check_internet_connection():
                    hablar("No pude conectarme a los servicios de voz. Por favor, revisa tu conexión a internet.")
                else:
                    hablar(ERROR_MESSAGES["speech_recognition_service"])
                return ""
            except Exception as e:
                logging.error(f"Ocurrió un error inesperado durante la escucha: {e}", exc_info=True)
                hablar(ERROR_MESSAGES["speech_recognition_unexpected"])
                return ""

def _format_structured_data(data):
    if isinstance(data, list):
        if not data:
            return "No hay elementos para mostrar."
        
        formatted_items = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                display_text = item.get('title') or item.get('name') or item.get('description') or str(item)
                formatted_items.append(f"{i+1}. {display_text}")
            else:
                formatted_items.append(f"{i+1}. {str(item)}")
        return "Aquí tienes los elementos: " + ", ".join(formatted_items)
    elif isinstance(data, dict):
        formatted_pairs = []
        for key, value in data.items():
            formatted_pairs.append(f"{key}: {value}")
        return "Aquí está la información: " + ", ".join(formatted_pairs)
    else:
        return str(data)

def hablar(texto=None, structured_data=None):
    if structured_data:
        text_to_speak = _format_structured_data(structured_data)
    elif texto:
        text_to_speak = texto
    else:
        logging.warning("Llamada a hablar() sin texto ni datos estructurados.")
        return

    logging.info(f"Intentando decir: '{text_to_speak}'")
    nombre_archivo = "respuesta_gemini.mp3"
    
    try:
        logging.debug("Generando audio TTS con gTTS...")
        tts = gTTS(text=text_to_speak, lang=CONFIG["TTS_LANGUAGE"])
        tts.save(nombre_archivo)
        logging.debug(f"Audio TTS guardado en {nombre_archivo}")

        try:
            logging.debug(f"Cargando audio desde {nombre_archivo} con pydub...")
            sound = AudioSegment.from_mp3(nombre_archivo)
            logging.debug("Audio cargado. Reproduciendo...")
            play(sound)
            logging.info("Reproducción de audio completada.")
        except Exception as e:
            logging.error(f"Error al cargar o reproducir audio con pydub: {e}", exc_info=True)
        finally:
            if os.path.exists(nombre_archivo):
                try:
                    os.remove(nombre_archivo)
                    logging.debug(f"Archivo de audio temporal eliminado: {nombre_archivo}")
                except OSError as e:
                    logging.error(f"Error al eliminar el archivo de audio temporal {nombre_archivo}: {e}")

    except Exception as e:
        logging.critical(f"Fallo crítico en gTTS al guardar el audio: {e}", exc_info=True)

# --- Gestión de Plugins ---

def load_plugins():
    regular_plugins = []
    command_plugins = []
    plugins_dir = CONFIG["PLUGINS_DIR"]
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)
        logging.info(f"Directorio de plugins creado: {plugins_dir}")
        return regular_plugins, command_plugins

    sys.path.insert(0, plugins_dir)

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            plugin_name = filename[:-3]
            filepath = os.path.join(plugins_dir, filename)
            spec = importlib.util.spec_from_file_location(plugin_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                try:
                    spec.loader.exec_module(module)
                    logging.info(f"Plugin cargado: {plugin_name}")
                    module.load_user_data = load_user_data
                    module.save_user_data = save_user_data
                    module.hablar = hablar
                    module.ERROR_MESSAGES = ERROR_MESSAGES
                    module.call_ha_service = call_ha_service
                    module.get_ha_state = get_ha_state
                    module.send_mcp_request = send_mcp_request
                    module.CONFIG = CONFIG

                    if hasattr(module, 'handle_input') or hasattr(module, 'process_response'):
                        regular_plugins.append(module)
                    if hasattr(module, 'handle_command'):
                        command_plugins.append(module)
                except Exception as e:
                    logging.error(f"Error al cargar el plugin {plugin_name}: {e}")
    return regular_plugins, command_plugins

# --- Hilo para comandos activados por tiempo ---
stop_timed_commands_thread = threading.Event()

def timed_command_executor(custom_commands):
    last_executed_date = {}
    while not stop_timed_commands_thread.is_set():
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M")
        current_date_str = now.strftime("%Y-%m-%d")

        for command_phrase, command_details in custom_commands.items():
            trigger_time = command_details.get("trigger_time")
            if trigger_time and trigger_time == current_time_str:
                if command_phrase not in last_executed_date or last_executed_date[command_phrase] != current_date_str:
                    logging.info(f"Activando comando por tiempo: {command_phrase} a las {trigger_time}")
                    action_type = command_details.get("action")
                    if action_type == "home_assistant_service":
                        domain = command_details.get("domain")
                        service = command_details.get("service")
                        entity_id = command_details.get("entity_id")
                        data = command_details.get("data")
                        if call_ha_service(domain, service, entity_id, data):
                            hablar(f"Comando programado ejecutado: {command_phrase}")
                        else:
                            hablar(f"Fallo al ejecutar comando programado: {command_phrase}")
                    elif action_type == "user_data_lookup":
                        key = command_details.get("key")
                        user_data = load_user_data()
                        value = user_data.get(key, "no tengo esa información")
                        hablar(f"Tu {key} es {value}.")
                    elif action_type == "user_data_set":
                        key = command_details.get("key")
                        value = command_details.get("value")
                        user_data = load_user_data()
                        user_data[key] = value
                        save_user_data(user_data)
                        hablar(f"He recordado que tu {key} es {value}.")
                    elif action_type == "log_reminder":
                        que = command_details.get("que")
                        cuando = command_details.get("cuando")
                        logging.info(f"RECORDATORIO PROGRAMADO: {que} para {cuando}")
                        hablar(f"Recordatorio programado: {que} para {cuando}")
                    elif action_type == "morning_summary":
                        hablar("Buenos días. Aquí está tu resumen matutino.")
                        try:
                            from plugins import calendar_plugin
                            eventos = calendar_plugin.list_upcoming_events()
                            hablar(eventos)
                        except Exception as e:
                            logging.error(f"Error al obtener eventos del calendario para el resumen: {e}")
                            hablar("No pude obtener los eventos del calendario.")
                        try:
                            from plugins import todo_plugin
                            tareas = todo_plugin.list_tasks()
                            hablar(tareas)
                        except Exception as e:
                            logging.error(f"Error al obtener tareas para el resumen: {e}")
                            hablar("No pude obtener la lista de tareas.")
                    elif action_type == "mcp_request":
                        method = command_details.get("method")
                        params = command_details.get("params")
                        result = send_mcp_request(method, params)
                        if result:
                            hablar(f"Comando MCP programado ejecutado: {method}")
                        else:
                            hablar(f"Fallo al ejecutar comando MCP programado: {method}")

                    last_executed_date[command_phrase] = current_date_str
        time.sleep(60)

# --- Interacción con Gemini CLI ---

def _handle_custom_commands(entrada_usuario, custom_commands, last_executed_command_info):
    command_handled = False
    extracted_params = {}

    for command_phrase, command_details in custom_commands.items():
        if "{" in command_phrase and "}" in command_phrase:
            pattern = re.sub(r'{(\w+)}', r'(?P<\1>.*)', command_phrase.lower())
            match = re.match(pattern, entrada_usuario.lower())
            if match:
                extracted_params = match.groupdict()
                action_type = command_details.get("action")

                if action_type == "home_assistant_service":
                    domain = command_details.get("domain")
                    service = command_details.get("service")
                    entity_id = extracted_params.get(command_details.get("entity_id_param", "entity_id"), command_details.get("entity_id"))
                    data = command_details.get("data")
                    if call_ha_service(domain, service, entity_id, data):
                        hablar(f"Comando personalizado ejecutado: {command_phrase}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": True}
                        break
                elif action_type == "user_data_lookup":
                    key = command_details.get("key")
                    user_data = load_user_data()
                    value = user_data.get(key, "no tengo esa información")
                    hablar(f"Tu {key} es {value}.")
                    command_handled = True
                    last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": True}
                    break
                elif action_type == "user_data_set":
                    key = command_details.get("key")
                    value_from_input_key = command_details.get("value_from_input")
                    value = extracted_params.get(value_from_input_key)
                    if value:
                        user_data = load_user_data()
                        user_data[key] = value
                        save_user_data(user_data)
                        hablar(f"He recordado que tu {key} es {value}.")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": True}
                        break
                    else:
                        logging.warning(f"No se pudo extraer el valor para {key} del comando: {entrada_usuario}")
                        hablar("Lo siento, no pude entender el valor que quieres que recuerde.")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": False, "error": "Value extraction failed"}
                        break
                elif action_type == "log_reminder":
                    que = extracted_params.get("que")
                    cuando = extracted_params.get("cuando")
                    logging.info(f"RECORDATORIO: {que} para {cuando}")
                    hablar(f"Recordatorio creado: {que} para {cuando}")
                    command_handled = True
                    last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": True}
                    break
                elif action_type == "mcp_request":
                    method = command_details.get("method")
                    params = command_details.get("params")
                    resolved_params = {}
                    if params:
                        for p_key, p_value in params.items():
                            if isinstance(p_value, str) and p_value.startswith("{") and p_value.endswith("}"):
                                param_name = p_value[1:-1]
                                resolved_params[p_key] = extracted_params.get(param_name, p_value)
                            else:
                                resolved_params[p_key] = p_value
                    
                    result = send_mcp_request(method, resolved_params)
                    if result:
                        hablar(f"Comando MCP ejecutado: {method}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": True, "result_data": result}
                        break
                    else:
                        hablar(f"Fallo al ejecutar comando MCP: {method}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": extracted_params, "success": False, "error": "MCP request failed"}
                        break
        else:
            if command_phrase.lower() == entrada_usuario.lower():
                action_type = command_details.get("action")
                if action_type == "home_assistant_service":
                    domain = command_details.get("domain")
                    service = command_details.get("service")
                    entity_id = command_details.get("entity_id")
                    data = command_details.get("data")
                    if call_ha_service(domain, service, entity_id, data):
                        hablar(f"Comando personalizado ejecutado: {command_phrase}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": True}
                        break
                elif action_type == "user_data_lookup":
                    key = command_details.get("key")
                    user_data = load_user_data()
                    value = user_data.get(key, "no tengo esa información")
                    hablar(f"Tu {key} es {value}.")
                    command_handled = True
                    last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": True}
                    break
                elif action_type == "user_data_set":
                    key = command_details.get("key")
                    value = command_details.get("value")
                    user_data = load_user_data()
                    user_data[key] = value
                    save_user_data(user_data)
                    hablar(f"He recordado que tu {key} es {value}.")
                    command_handled = True
                    last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": True}
                    break
                elif action_type == "log_reminder":
                    que = command_details.get("que")
                    cuando = command_details.get("cuando")
                    logging.info(f"RECORDATORIO: {que} para {cuando}")
                    hablar(f"Recordatorio creado: {que} para {cuando}")
                    command_handled = True
                    last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": True}
                    break
                elif action_type == "mcp_request":
                    method = command_details.get("method")
                    params = command_details.get("params")
                    result = send_mcp_request(method, params)
                    if result:
                        hablar(f"Comando MCP ejecutado: {method}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": True, "result_data": result}
                        break
                    else:
                        hablar(f"Fallo al ejecutar comando MCP: {method}")
                        command_handled = True
                        last_executed_command_info = {"type": "custom_command", "phrase": command_phrase, "details": command_details, "params": {}, "success": False, "error": "MCP request failed"}
                        break
    return command_handled, last_executed_command_info

def _handle_command_plugins(entrada_usuario, command_plugins):
    for plugin in command_plugins:
        if hasattr(plugin, 'handle_command'):
            try:
                response = plugin.handle_command(entrada_usuario)
                if response:
                    hablar(response)
                    return True
            except Exception as e:
                logging.error(f"Error en plugin de comando {plugin.__name__}.handle_command: {e}")
                hablar(ERROR_MESSAGES["plugin_error"])
    return False

def _handle_regular_plugins_input(entrada_usuario, regular_plugins):
    for plugin in regular_plugins:
        if hasattr(plugin, 'handle_input'):
            try:
                new_input = plugin.handle_input(entrada_usuario)
                if new_input is None:
                    logging.info(f"Plugin {plugin.__name__} consumió la entrada.")
                    return None
                else:
                    entrada_usuario = new_input
            except Exception as e:
                logging.error(f"Error en plugin {plugin.__name__}.handle_input: {e}")
                hablar(ERROR_MESSAGES["plugin_error"])
    return entrada_usuario

def _handle_regular_plugins_response(respuesta_gemini, regular_plugins):
    for plugin in regular_plugins:
        if hasattr(plugin, 'process_response'):
            try:
                respuesta_gemini = plugin.process_response(respuesta_gemini)
            except Exception as e:
                logging.error(f"Error en plugin {plugin.__name__}.process_response: {e}")
                hablar(ERROR_MESSAGES["plugin_error"])
    return respuesta_gemini

def main():
    if is_already_running():
        logging.error("El asistente de voz ya se está ejecutando en otra instancia.")
        return

    create_lock_file()
    
    try:
        if not check_internet_connection():
            logging.error("No hay conexión a internet. El asistente de voz no puede funcionar.")
            return

        logging.info("Iniciando asistente de voz. Di 'salir' para terminar.")
        
        audio_handler = AudioInputHandler(CONFIG)
        conversation_history = []
        regular_plugins, command_plugins = load_plugins()
        custom_commands = load_custom_commands()
        last_executed_command_info = {}
        
        timed_thread = threading.Thread(target=timed_command_executor, args=(custom_commands,))
        timed_thread.daemon = True
        timed_thread.start()

        while True:
            entrada_usuario = audio_handler.escuchar()

            if entrada_usuario.lower() == "salir":
                hablar("Adiós.")
                stop_timed_commands_thread.set()
                timed_thread.join()
                break

            if entrada_usuario:
                command_handled, last_executed_command_info = _handle_custom_commands(entrada_usuario, custom_commands, last_executed_command_info)
                if command_handled:
                    continue

                command_handled = _handle_command_plugins(entrada_usuario, command_plugins)
                if command_handled:
                    continue

                entrada_usuario = _handle_regular_plugins_input(entrada_usuario, regular_plugins)
                if entrada_usuario is None:
                    continue

                conversation_history.append({"role": "user", "parts": [{"text": entrada_usuario}]})
                
                payload = {"contents": conversation_history}
                json_payload = json.dumps(payload)

                logging.debug(f"Enviando a Gemini CLI: '{entrada_usuario}' (con historial)")
                try:
                    comando_gemini = ["gemini", "generate-content", "--stdin"]
                    resultado = subprocess.run(
                        comando_gemini,
                        input=json_payload,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    respuesta_gemini = resultado.stdout.strip()
                    logging.debug(f"Respuesta de Gemini: {respuesta_gemini}")

                    conversation_history.append({"role": "model", "parts": [{"text": respuesta_gemini}]})

                    if len(conversation_history) > CONFIG["MAX_HISTORY_LENGTH"]:
                        conversation_history = conversation_history[-CONFIG["MAX_HISTORY_LENGTH"]:]
                        logging.info(f"Historial de conversación truncado a {CONFIG["MAX_HISTORY_LENGTH"]} mensajes.")

                    respuesta_gemini = _handle_regular_plugins_response(respuesta_gemini, regular_plugins)
                    hablar(respuesta_gemini)
                    
                except subprocess.CalledProcessError as e:
                    logging.error(f"Error al interactuar con Gemini CLI: {e}")
                    logging.error(f"Salida de error: {e.stderr}")
                    hablar(ERROR_MESSAGES["gemini_cli_error"])
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.pop()
                except FileNotFoundError:
                    logging.error(ERROR_MESSAGES["gemini_cli_not_found"])
                    hablar(ERROR_MESSAGES["gemini_cli_not_found"])
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.pop()
                except Exception as e:
                    logging.error(f"Ocurrió un error inesperado: {e}")
                    hablar(ERROR_MESSAGES["general_unexpected_error"])
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.pop()
    finally:
        remove_lock_file()

if __name__ == "__main__":
    main()