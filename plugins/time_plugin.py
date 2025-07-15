"""Plugin para proporcionar la hora y el pronóstico del tiempo.

Permite al asistente responder a preguntas sobre la hora y el clima,
recordando la ciudad preferida del usuario.
"""

import datetime
import os
import requests
import json
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- Inyección de dependencias (proporcionadas por el script principal) ---
hablar = print
load_user_data = lambda: {}
save_user_data = lambda data: None
# ----------------------------------------------------------------------

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

def get_weather(city):
    """Obtiene el pronóstico del tiempo para una ciudad usando OpenWeatherMap."""
    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY == "TU_API_KEY_DE_OPENWEATHERMAP_AQUI":
        return "La API key de OpenWeatherMap no está configurada. Por favor, añádela al archivo .env."

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric", # Usar grados Celsius
        "lang": "es"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() # Lanza un error para respuestas 4xx/5xx
        data = response.json()

        description = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        temp_min = data['main']['temp_min']
        temp_max = data['main']['temp_max']

        return f"En {city}, el cielo está {description}. La temperatura es de {temp:.0f} grados, con una sensación térmica de {feels_like:.0f}. La mínima será de {temp_min:.0f} y la máxima de {temp_max:.0f} grados."

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "La API key de OpenWeatherMap no es válida. Por favor, revísala."
        elif e.response.status_code == 404:
            return f"No pude encontrar la ciudad '{city}'. Por favor, prueba con otra."
        else:
            logging.error(f"Error HTTP al obtener el clima: {e}")
            return "Lo siento, no pude obtener el pronóstico del tiempo en este momento."
    except Exception as e:
        logging.error(f"Error inesperado al obtener el clima: {e}")
        return "Ocurrió un error inesperado al consultar el tiempo."

def handle_command(command):
    """Maneja comandos relacionados con la hora y el tiempo."""
    command = command.lower()

    if "dime la hora" in command:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        hablar(f"Son las {current_time}")
        return f"Son las {current_time}" # Devuelve la respuesta para que el bucle principal la maneje

    if "qué tiempo hace" in command:
        # Extraer la ciudad si se especifica en el comando
        parts = command.split("en")
        if len(parts) > 1:
            city = parts[-1].strip()
        else:
            # Si no se especifica, buscar la ciudad por defecto del usuario
            user_data = load_user_data()
            city = user_data.get("default_city")

        if city:
            weather_report = get_weather(city)
            hablar(weather_report)
            return weather_report
        else:
            # Si no hay ciudad guardada, preguntar al usuario
            hablar("No sé cuál es tu ciudad. ¿De qué ciudad quieres saber el tiempo?")
            return "Ciudad no especificada"

    return None # No se manejó ningún comando
