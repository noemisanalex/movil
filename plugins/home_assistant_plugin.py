"""Plugin para interactuar con Home Assistant.

Permite al asistente controlar dispositivos y obtener estados de Home Assistant.
"""

import logging
from asistente_voz import hablar, ERROR_MESSAGES, call_ha_service, get_ha_state # Importar funciones de HA

def handle_command(text):
    """Maneja comandos relacionados con Home Assistant.

    Args:
        text (str): El texto de la entrada del usuario.

    Returns:
        bool: True si el comando fue manejado, False en caso contrario.
    """
    text_lower = text.lower()

    # Ejemplo: Encender una luz
    if "enciende la luz de la sala" in text_lower:
        if call_ha_service("light", "turn_on", "light.luz_sala"):
            hablar("Encendiendo la luz de la sala.")
        return True

    # Ejemplo: Apagar una luz
    if "apaga la luz de la sala" in text_lower:
        if call_ha_service("light", "turn_off", "light.luz_sala"):
            hablar("Apagando la luz de la sala.")
        return True

    # Ejemplo: Obtener estado de un sensor de temperatura
    if "cuál es la temperatura de la sala" in text_lower:
        state = get_ha_state("sensor.temperatura_sala") # Reemplaza con tu sensor real
        if state and state.get("state"):
            hablar(f"La temperatura de la sala es de {state['state']} grados.")
        return True

    return False # El comando no fue manejado por este plugin