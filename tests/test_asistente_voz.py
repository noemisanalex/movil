import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import json
import sys
import requests # Added for mocking requests

# Añadir el directorio padre al path para poder importar asistente_voz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asistente_voz import (
    load_user_data,
    save_user_data,
    load_custom_commands,
    hablar,
    _format_structured_data,
    call_ha_service,
    get_ha_state,
    send_mcp_request,
    load_plugins,
    timed_command_executor,
    _handle_custom_commands,
    _handle_command_plugins,
    _handle_regular_plugins_input,
    _handle_regular_plugins_response,
    ERROR_MESSAGES
)

class TestAsistenteVoz(unittest.TestCase):

    def setUp(self):
        # Configurar un entorno de prueba limpio para cada test
        self.user_data_file = 'test_user_data.json'
        self.custom_commands_file = 'test_custom_commands.json'
        # Asegurarse de que los archivos de prueba no existan antes de cada test
        if os.path.exists(self.user_data_file):
            os.remove(self.user_data_file)
        if os.path.exists(self.custom_commands_file):
            os.remove(self.custom_commands_file)

        # Parchear las rutas de los archivos en el módulo asistente_voz
        # para que apunten a nuestros archivos de prueba
        self.patcher_user_data_file = patch('asistente_voz.USER_DATA_FILE', self.user_data_file)
        self.patcher_custom_commands_file = patch('asistente_voz.CUSTOM_COMMANDS_FILE', self.custom_commands_file)
        self.mock_user_data_file = self.patcher_user_data_file.start()
        self.mock_custom_commands_file = self.patcher_custom_commands_file.start()

        # Mockear la función hablar para evitar la salida de voz durante los tests
        self.patcher_hablar = patch('asistente_voz.hablar')
        self.mock_hablar = self.patcher_hablar.start()

        # Mockear logging para capturar mensajes
        self.patcher_logging_warning = patch('logging.warning')
        self.mock_logging_warning = self.patcher_logging_warning.start()
        self.patcher_logging_error = patch('logging.error')
        self.mock_logging_error = self.patcher_logging_error.start()
        self.patcher_logging_info = patch('logging.info')
        self.mock_logging_info = self.patcher_logging_info.start()

    def tearDown(self):
        # Limpiar después de cada test
        if os.path.exists(self.user_data_file):
            os.remove(self.user_data_file)
        if os.path.exists(self.custom_commands_file):
            os.remove(self.custom_commands_file)
        self.patcher_user_data_file.stop()
        self.patcher_custom_commands_file.stop()
        self.patcher_hablar.stop()
        self.patcher_logging_warning.stop()
        self.patcher_logging_error.stop()
        self.patcher_logging_info.stop()

    # --- Tests para load_user_data y save_user_data ---
    def test_load_user_data_file_not_exists(self):
        self.assertEqual(load_user_data(), {})

    def test_save_user_data(self):
        data = {"name": "Test", "age": 30}
        save_user_data(data)
        with open(self.user_data_file, 'r') as f:
            self.assertEqual(json.load(f), data)

    def test_load_user_data_file_exists(self):
        data = {"name": "Test", "city": "Example"}
        with open(self.user_data_file, 'w') as f:
            json.dump(data, f)
        self.assertEqual(load_user_data(), data)

    def test_load_user_data_corrupt_file(self):
        with open(self.user_data_file, 'w') as f:
            f.write("{\"name\": \"Test\",}") # JSON inválido
        self.assertEqual(load_user_data(), {})
        self.mock_logging_warning.assert_called_with(ERROR_MESSAGES["user_data_corrupt"].format(USER_DATA_FILE=self.user_data_file))
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["user_data_corrupt"])

    # --- Tests para load_custom_commands ---
    def test_load_custom_commands_file_not_exists(self):
        self.assertEqual(load_custom_commands(), {})

    def test_load_custom_commands_file_exists(self):
        commands = {"hello": {"action": "speak", "text": "Hi!"}}
        with open(self.custom_commands_file, 'w') as f:
            json.dump(commands, f)
        self.assertEqual(load_custom_commands(), commands)

    def test_load_custom_commands_corrupt_file(self):
        with open(self.custom_commands_file, 'w') as f:
            f.write("{\"command\": \"invalid\",}") # JSON inválido
        self.assertEqual(load_custom_commands(), {})
        self.mock_logging_warning.assert_called_with(ERROR_MESSAGES["custom_commands_corrupt"])
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["custom_commands_corrupt"])

    # --- Tests para _format_structured_data ---
    def test_format_structured_data_list_of_dicts(self):
        data = [{'title': 'Item 1'}, {'name': 'Item 2'}, {'description': 'Item 3'}, {'other': 'Item 4'}]
        expected = "Aquí tienes los elementos: 1. Item 1, 2. Item 2, 3. Item 3, 4. {'other': 'Item 4'}"
        self.assertEqual(_format_structured_data(data), expected)

    def test_format_structured_data_list_of_strings(self):
        data = ["apple", "banana"]
        expected = "Aquí tienes los elementos: 1. apple, 2. banana"
        self.assertEqual(_format_structured_data(data), expected)

    def test_format_structured_data_empty_list(self):
        data = []
        expected = "No hay elementos para mostrar."
        self.assertEqual(_format_structured_data(data), expected)

    def test_format_structured_data_dict(self):
        data = {"key1": "value1", "key2": "value2"}
        expected = "Aquí está la información: key1: value1, key2: value2"
        self.assertEqual(_format_structured_data(data), expected)

    def test_format_structured_data_string(self):
        data = "simple string"
        expected = "simple string"
        self.assertEqual(_format_structured_data(data), expected)

    # --- Tests para hablar ---
    @patch('asistente_voz.gTTS')
    @patch('asistente_voz.AudioSegment.from_mp3')
    @patch('asistente_voz.play')
    @patch('os.remove')
    def test_hablar_text(self, mock_os_remove, mock_play, mock_from_mp3, mock_gTTS):
        mock_tts_instance = MagicMock()
        mock_gTTS.return_value = mock_tts_instance
        mock_from_mp3.return_value = MagicMock() # Mock the sound object

        hablar("Hola mundo")

        mock_gTTS.assert_called_once_with(text="Hola mundo", lang='es')
        mock_tts_instance.save.assert_called_once_with("respuesta_gemini.mp3")
        mock_from_mp3.assert_called_once_with("respuesta_gemini.mp3")
        mock_play.assert_called_once()
        mock_os_remove.assert_called_once_with("respuesta_gemini.mp3")
        self.mock_logging_info.assert_called_with("Gemini dice: Hola mundo")

    @patch('asistente_voz.gTTS')
    @patch('asistente_voz.AudioSegment.from_mp3')
    @patch('asistente_voz.play')
    @patch('os.remove')
    def test_hablar_structured_data(self, mock_os_remove, mock_play, mock_from_mp3, mock_gTTS):
        mock_tts_instance = MagicMock()
        mock_gTTS.return_value = mock_tts_instance
        mock_from_mp3.return_value = MagicMock()

        data = [{"title": "Tarea 1"}]
        hablar(structured_data=data)

        mock_gTTS.assert_called_once_with(text="Aquí tienes los elementos: 1. Tarea 1", lang='es')
        mock_tts_instance.save.assert_called_once_with("respuesta_gemini.mp3")
        mock_from_mp3.assert_called_once_with("respuesta_gemini.mp3")
        mock_play.assert_called_once()
        mock_os_remove.assert_called_once_with("respuesta_gemini.mp3")
        self.mock_logging_info.assert_called_with("Gemini dice: Aquí tienes los elementos: 1. Tarea 1")

    @patch('asistente_voz.gTTS')
    @patch('asistente_voz.AudioSegment.from_mp3')
    @patch('asistente_voz.play')
    @patch('os.remove')
    def test_hablar_tts_save_error(self, mock_os_remove, mock_play, mock_from_mp3, mock_gTTS):
        mock_gTTS.side_effect = Exception("Save error")

        hablar("Hola")

        self.mock_logging_error.assert_called_with("Error al reproducir o guardar el audio: Save error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["tts_save_error"])
        mock_os_remove.assert_not_called()
        mock_play.assert_not_called()

    @patch('asistente_voz.gTTS')
    @patch('asistente_voz.AudioSegment.from_mp3')
    @patch('asistente_voz.play')
    @patch('os.remove')
    def test_hablar_playback_error(self, mock_os_remove, mock_play, mock_from_mp3, mock_gTTS):
        mock_tts_instance = MagicMock()
        mock_gTTS.return_value = mock_tts_instance
        mock_from_mp3.side_effect = Exception("Playback error")

        hablar("Hola")

        self.mock_logging_error.assert_called_with("Error al intentar reproducir audio con pydub: Playback error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["tts_playback_error"])
        mock_os_remove.assert_called_once_with("respuesta_gemini.mp3") # Should still try to remove
        mock_play.assert_not_called()

    # --- Tests para call_ha_service ---
    @patch('requests.post')
    def test_call_ha_service_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = call_ha_service("light", "turn_on", "light.test_light")
        self.assertTrue(result)
        mock_post.assert_called_once()
        self.mock_logging_info.assert_called_with("Llamada a HA exitosa: light.turn_on para light.test_light")

    @patch('requests.post')
    def test_call_ha_service_failure(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("HA error")

        result = call_ha_service("light", "turn_on", "light.test_light")
        self.assertFalse(result)
        self.mock_logging_error.assert_called_with("Error al llamar al servicio de Home Assistant (light.turn_on): HA error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["ha_service_failed"])

    # --- Tests para get_ha_state ---
    @patch('requests.get')
    def test_get_ha_state_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"entity_id": "sensor.test", "state": "25"}
        mock_get.return_value = mock_response

        state = get_ha_state("sensor.test")
        self.assertEqual(state["state"], "25")
        mock_get.assert_called_once()
        self.mock_logging_info.assert_called_with("Estado de HA obtenido para sensor.test: 25")

    @patch('requests.get')
    def test_get_ha_state_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("State error")

        state = get_ha_state("sensor.test")
        self.assertIsNone(state)
        self.mock_logging_error.assert_called_with("Error al obtener el estado de Home Assistant para sensor.test: State error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["ha_state_failed"])

    # --- Tests para send_mcp_request ---
    @patch('requests.post')
    def test_send_mcp_request_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": {"id": "123"}, "id": 1}
        mock_post.return_value = mock_response

        result = send_mcp_request("test.method", {"param": "value"})
        self.assertEqual(result, {"id": "123"})
        mock_post.assert_called_once()
        self.mock_logging_info.assert_called_with("Solicitud MCP exitosa para método test.method")

    @patch('requests.post')
    def test_send_mcp_request_mcp_error_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}
        mock_post.return_value = mock_response

        result = send_mcp_request("test.method")
        self.assertIsNone(result)
        self.mock_logging_error.assert_called_with("Error en la respuesta del servidor MCP: {'code': -32601, 'message': 'Method not found'}")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["mcp_request_failed"])

    @patch('requests.post')
    def test_send_mcp_request_network_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = send_mcp_request("test.method")
        self.assertIsNone(result)
        self.mock_logging_error.assert_called_with("Error al enviar solicitud al servidor MCP (http://localhost:8080): Network error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["mcp_request_failed"])

    # --- Tests para load_plugins ---
    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['plugin1.py', '__init__.py', 'plugin2.pyc'])
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    def test_load_plugins_success(self, mock_module_from_spec, mock_spec_from_file_location, mock_listdir, mock_exists):
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_module = MagicMock()
        mock_module.__name__ = "plugin1" # Assign __name__ attribute
        mock_module.handle_input = MagicMock()
        mock_module.process_response = MagicMock()
        # Ensure handle_command is not present for a regular plugin
        if hasattr(mock_module, 'handle_command'):
            del mock_module.handle_command
        mock_module_from_spec.return_value = mock_module

        regular_plugins, command_plugins = load_plugins()

        self.assertEqual(len(regular_plugins), 1)
        self.assertEqual(len(command_plugins), 0)
        self.mock_logging_info.assert_called_with("Plugin cargado: plugin1")

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['bad_plugin.py'])
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    def test_load_plugins_error_during_load(self, mock_module_from_spec, mock_spec_from_file_location, mock_listdir, mock_exists):
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module.side_effect = Exception("Plugin load error")
        mock_spec_from_file_location.return_value = mock_spec

        mock_module = MagicMock()
        mock_module.__name__ = "bad_plugin" # Assign __name__ attribute
        mock_module_from_spec.return_value = mock_module

        regular_plugins, command_plugins = load_plugins()

        self.assertEqual(len(regular_plugins), 0)
        self.assertEqual(len(command_plugins), 0)
        self.mock_logging_error.assert_called_with("Error al cargar el plugin bad_plugin: Plugin load error")

    # --- Tests para _handle_custom_commands ---
    @patch('asistente_voz.call_ha_service', return_value=True)
    @patch('asistente_voz.load_user_data', return_value={})
    @patch('asistente_voz.save_user_data')
    @patch('asistente_voz.send_mcp_request', return_value={"id": "123"})
    def test_handle_custom_commands_ha_service_dynamic(self, mock_send_mcp_request, mock_save_user_data, mock_load_user_data, mock_call_ha_service):
        custom_commands = {
            "enciende la luz de {entidad}": {
                "action": "home_assistant_service",
                "domain": "light",
                "service": "turn_on",
                "entity_id_param": "entidad"
            }
        }
        entrada = "enciende la luz de la cocina"
        command_handled, info = _handle_custom_commands(entrada, custom_commands, {})
        self.assertTrue(command_handled)
        mock_call_ha_service.assert_called_with("light", "turn_on", "la cocina", None)
        self.mock_hablar.assert_called_with("Comando personalizado ejecutado: enciende la luz de {entidad}")
        self.assertTrue(info["success"])

    def test_handle_custom_commands_user_data_lookup(self):
        custom_commands = {
            "cual es mi nombre": {
                "action": "user_data_lookup",
                "key": "nombre_usuario"
            }
        }
        with patch('asistente_voz.load_user_data', return_value={'nombre_usuario': 'Juan'}):
            command_handled, info = _handle_custom_commands("cual es mi nombre", custom_commands, {})
            self.assertTrue(command_handled)
            self.mock_hablar.assert_called_with("Tu nombre_usuario es Juan.")
            self.assertTrue(info["success"])

    def test_handle_custom_commands_user_data_set_dynamic(self):
        custom_commands = {
            "recuerda que mi nombre es {nombre}": {
                "action": "user_data_set",
                "key": "nombre_usuario",
                "value_from_input": "nombre"
            }
        }
        with patch('asistente_voz.load_user_data', return_value={}), \
             patch('asistente_voz.save_user_data') as mock_save_user_data:
            command_handled, info = _handle_custom_commands("recuerda que mi nombre es Pedro", custom_commands, {})
            self.assertTrue(command_handled)
            mock_save_user_data.assert_called_once_with({'nombre_usuario': 'Pedro'})
            self.mock_hablar.assert_called_with("He recordado que tu nombre_usuario es Pedro.")
            self.assertTrue(info["success"])

    def test_handle_custom_commands_log_reminder(self):
        custom_commands = {
            "crear recordatorio {que} para {cuando}": {
                "action": "log_reminder"
            }
        }
        entrada = "crear recordatorio comprar leche para mañana"
        command_handled, info = _handle_custom_commands(entrada, custom_commands, {})
        self.assertTrue(command_handled)
        self.mock_logging_info.assert_called_with("RECORDATORIO: comprar leche para mañana")
        self.mock_hablar.assert_called_with("Recordatorio creado: comprar leche para mañana")
        self.assertTrue(info["success"])

    @patch('asistente_voz.send_mcp_request', return_value={"status": "ok"})
    def test_handle_custom_commands_mcp_request_dynamic(self, mock_send_mcp_request):
        custom_commands = {
            "ejecuta mcp {metodo} con {parametro}": {
                "action": "mcp_request",
                "method": "{metodo}",
                "params": {"data": "{parametro}"}
            }
        }
        entrada = "ejecuta mcp mi_metodo con mi_parametro"
        command_handled, info = _handle_custom_commands(entrada, custom_commands, {})
        self.assertTrue(command_handled)
        mock_send_mcp_request.assert_called_once_with("mi_metodo", {"data": "mi_parametro"})
        self.mock_hablar.assert_called_with("Comando MCP ejecutado: mi_metodo")
        self.assertTrue(info["success"])

    def test_handle_custom_commands_no_match(self):
        custom_commands = {"comando_falso": {"action": "speak", "text": "Fake"}}
        command_handled, info = _handle_custom_commands("entrada_no_existente", custom_commands, {})
        self.assertFalse(command_handled)
        self.assertEqual(info, {})

    # --- Tests para _handle_command_plugins ---
    def test_handle_command_plugins_handled(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_command.return_value = True
        command_plugins = [mock_plugin]
        self.assertTrue(_handle_command_plugins("test command", command_plugins))
        mock_plugin.handle_command.assert_called_once_with("test command")

    def test_handle_command_plugins_not_handled(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_command.return_value = False
        command_plugins = [mock_plugin]
        self.assertFalse(_handle_command_plugins("test command", command_plugins))
        mock_plugin.handle_command.assert_called_once_with("test command")

    def test_handle_command_plugins_error(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_command.side_effect = Exception("Plugin error")
        command_plugins = [mock_plugin]
        self.assertFalse(_handle_command_plugins("test command", command_plugins))
        self.mock_logging_error.assert_called_with("Error en plugin de comando MagicMock.handle_command: Plugin error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["plugin_error"])

    # --- Tests para _handle_regular_plugins_input ---
    def test_handle_regular_plugins_input_consumed(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_input.return_value = None
        regular_plugins = [mock_plugin]
        self.assertIsNone(_handle_regular_plugins_input("test input", regular_plugins))
        mock_plugin.handle_input.assert_called_once_with("test input")
        self.mock_logging_info.assert_called_with("Plugin MagicMock consumió la entrada.")

    def test_handle_regular_plugins_input_modified(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_input.return_value = "modified input"
        regular_plugins = [mock_plugin]
        self.assertEqual(_handle_regular_plugins_input("test input", regular_plugins), "modified input")
        mock_plugin.handle_input.assert_called_once_with("test input")

    def test_handle_regular_plugins_input_error(self):
        mock_plugin = MagicMock()
        mock_plugin.handle_input.side_effect = Exception("Input plugin error")
        regular_plugins = [mock_plugin]
        self.assertEqual(_handle_regular_plugins_input("test input", regular_plugins), "test input")
        self.mock_logging_error.assert_called_with("Error en plugin MagicMock.handle_input: Input plugin error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["plugin_error"])

    # --- Tests para _handle_regular_plugins_response ---
    def test_handle_regular_plugins_response_modified(self):
        mock_plugin = MagicMock()
        mock_plugin.process_response.return_value = "modified response"
        regular_plugins = [mock_plugin]
        self.assertEqual(_handle_regular_plugins_response("test response", regular_plugins), "modified response")
        mock_plugin.process_response.assert_called_once_with("test response")

    def test_handle_regular_plugins_response_error(self):
        mock_plugin = MagicMock()
        mock_plugin.process_response.side_effect = Exception("Response plugin error")
        regular_plugins = [mock_plugin]
        self.assertEqual(_handle_regular_plugins_response("test response", regular_plugins), "test response")
        self.mock_logging_error.assert_called_with("Error en plugin MagicMock.process_response: Response plugin error")
        self.mock_hablar.assert_called_with(ERROR_MESSAGES["plugin_error"])

if __name__ == '__main__':
    unittest.main()