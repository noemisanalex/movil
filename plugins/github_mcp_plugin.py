"""Plugin para interactuar con GitHub a través del servidor MCP (Microservice Control Plane).

Permite al asistente realizar acciones como listar Pull Requests, Issues y crear Issues.
"""

import logging
from asistente_voz import hablar, ERROR_MESSAGES, send_mcp_request

def handle_command(text):
    """Maneja comandos relacionados con GitHub.

    Args:
        text (str): El texto de la entrada del usuario.

    Returns:
        bool: True si el comando fue manejado, False en caso contrario.
    """
    text_lower = text.lower()

    # Ejemplo: Listar Pull Requests abiertos
    if "lista mis pull requests abiertos" in text_lower:
        logging.info("Comando 'lista mis pull requests abiertos' detectado. Consultando MCP de GitHub...")
        try:
            result = send_mcp_request("github.pull_requests.list", {"state": "open"})
            if result and result.get("pull_requests"):
                hablar(structured_data=result["pull_requests"])
            elif result is not None: # Si result es un diccionario vacío o no tiene pull_requests
                hablar("No tienes pull requests abiertos.")
            else:
                hablar(ERROR_MESSAGES["mcp_request_failed"])
            return True
        except Exception as e:
            logging.error(f"Error al procesar comando de GitHub PRs: {e}. Mensaje: {ERROR_MESSAGES["plugin_error"]}")
            hablar(ERROR_MESSAGES["plugin_error"])
            return True

    # Ejemplo: Listar Issues abiertos
    if "lista mis issues abiertos" in text_lower:
        logging.info("Comando 'lista mis issues abiertos' detectado. Consultando MCP de GitHub...")
        try:
            result = send_mcp_request("github.issues.list", {"state": "open"})
            if result and result.get("issues"):
                hablar(structured_data=result["issues"])
            elif result is not None:
                hablar("No tienes issues abiertos.")
            else:
                hablar(ERROR_MESSAGES["mcp_request_failed"])
            return True
        except Exception as e:
            logging.error(f"Error al procesar comando de GitHub Issues: {e}. Mensaje: {ERROR_MESSAGES["plugin_error"]}")
            hablar(ERROR_MESSAGES["plugin_error"])
            return True

    # Ejemplo: Crear un Issue
    if "crea un issue en" in text_lower and "con titulo" in text_lower:
        parts = text_lower.split("crea un issue en ")[1].split(" con titulo ")
        if len(parts) == 2:
            repo_name = parts[0].strip()
            issue_title = parts[1].strip()
            logging.info(f"Comando 'crear issue' detectado para repo {repo_name} con título {issue_title}. Enviando a MCP de GitHub...")
            try:
                result = send_mcp_request("github.issues.create", {"repository": repo_name, "title": issue_title})
                if result and result.get("number"):
                    hablar(f"Issue número {result['number']} creado en {repo_name} con título {issue_title}.")
                else:
                    hablar(ERROR_MESSAGES["mcp_request_failed"])
            except Exception as e:
                logging.error(f"Error al crear issue en GitHub: {e}. Mensaje: {ERROR_MESSAGES["plugin_error"]}")
                hablar(ERROR_MESSAGES["plugin_error"])
            return True

    # Ejemplo: Comentar en un Issue
    if "comenta en el issue" in text_lower and "del repositorio" in text_lower and "con" in text_lower:
        try:
            issue_part = text_lower.split("comenta en el issue ")[1]
            issue_num_str = issue_part.split(" del repositorio ")[0].strip()
            issue_num = int(issue_num_str)

            repo_comment_part = issue_part.split(" del repositorio ")[1]
            repo_name = repo_comment_part.split(" con ")[0].strip()
            comment_text = repo_comment_part.split(" con ")[1].strip()

            logging.info(f"Comando 'comentar issue' detectado para issue {issue_num} en repo {repo_name} con comentario {comment_text}. Enviando a MCP de GitHub...")
            result = send_mcp_request("github.issues.comment", {"repository": repo_name, "issue_number": issue_num, "body": comment_text})
            if result and result.get("id"):
                hablar(f"Comentario añadido al issue {issue_num} en {repo_name}.")
            else:
                hablar(ERROR_MESSAGES["mcp_request_failed"])
        except ValueError:
            hablar("Lo siento, no pude entender el número de issue. Por favor, di un número válido.")
        except Exception as e:
            logging.error(f"Error al comentar en issue de GitHub: {e}. Mensaje: {ERROR_MESSAGES["plugin_error"]}")
            hablar(ERROR_MESSAGES["plugin_error"])
        return True

    return False