"""Plugin para activar flujos de trabajo en n8n a través de webhooks.

Permite al asistente disparar automatizaciones predefinidas en n8n.
"""

import requests
import logging
import os
from asistente_voz import hablar, ERROR_MESSAGES

# Configura tu URL de Webhook de n8n aquí
# Puedes obtenerla al crear un nodo 'Webhook' en n8n y configurarlo en modo 'POST'
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "TU_URL_DE_WEBHOOK_N8N_AQUI")

def handle_command(text):
    """Maneja comandos relacionados con la activación de webhooks de n8n.

    Args:
        text (str): El texto de la entrada del usuario.

    Returns:
        bool: True si el comando fue manejado, False en caso contrario.
    """
    text_lower = text.lower()

    if "activar automatización de prueba" in text_lower:
        logging.info("Comando 'activar automatización de prueba' detectado. Enviando a n8n...")
        try:
            response = requests.post(N8N_WEBHOOK_URL, json={"command": "activar_automatizacion_prueba", "original_text": text})
            response.raise_for_status() # Lanza una excepción para códigos de estado HTTP erróneos
            hablar("Automatización de prueba activada en n8n.")
            logging.info(f"Respuesta de n8n: {response.status_code} - {response.text}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al enviar el webhook a n8n: {e}")
            hablar(ERROR_MESSAGES["n8n_webhook_failed"])
            return True
    
    return False