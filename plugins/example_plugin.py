"""Plugin de ejemplo para demostrar la funcionalidad de los plugins.

Este plugin intercepta la entrada del usuario y procesa la respuesta de Gemini.
"""

import logging

def handle_input(text):
    """Procesa la entrada del usuario antes de enviarla a Gemini.

    Si la entrada contiene "hola", el plugin la consume y no se envía a Gemini.
    """
    if "hola" in text.lower():
        logging.info("Plugin de ejemplo: Interceptando 'hola'.")
        return None # Indica que el plugin ha manejado la entrada y no debe ir a Gemini
    return text # Pasa la entrada a Gemini si no es manejada

def process_response(text):
    """Procesa la respuesta de Gemini antes de que sea hablada.

    Añade un sufijo a la respuesta para indicar que ha sido procesada por el plugin.
    """
    logging.info("Plugin de ejemplo: Procesando respuesta de Gemini.")
    return f"{text} (procesado por plugin)"