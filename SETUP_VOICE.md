# Configuración del Módulo de Voz para AutogestiónPro

Este documento detalla los pasos necesarios para configurar el entorno de voz (Speech-to-Text y Text-to-Speech) que permitirá la interacción hablada con AutogestiónPro.

## Requisitos Previos

*   **Python 3.x:** Asegúrate de tener Python 3.x instalado en tu sistema.
*   **Conexión a Internet:** Algunas librerías y APIs de voz requieren conexión a internet para funcionar.
*   **Micrófono y Altavoces:** Necesitarás un micrófono para la entrada de voz y altavoces para la salida de voz.

## Pasos de Configuración

### 1. Instalación de Librerías Python

Instala las librerías necesarias utilizando `pip`:

```bash
pip install SpeechRecognition gTTS playsound
```

*   **`SpeechRecognition`**: Para el reconocimiento de voz (STT).
*   **`gTTS` (Google Text-to-Speech)**: Para la síntesis de voz (TTS) utilizando el servicio de Google.
*   **`playsound`**: Para reproducir los archivos de audio generados por `gTTS`.

### 2. Configuración del Reconocimiento de Voz

`SpeechRecognition` puede utilizar varias APIs de reconocimiento de voz. Por defecto, usa la API de Google Web Speech, que generalmente no requiere configuración adicional para un uso básico, pero sí una conexión a internet.

Si deseas utilizar un motor offline (ej. CMU Sphinx), la configuración es más compleja y requeriría la descarga de modelos de lenguaje.

### 3. Configuración de la Síntesis de Voz

`gTTS` utiliza la API de Google Translate para la síntesis de voz. No requiere configuración de claves API para un uso básico, pero sí una conexión a internet.

### 4. Permisos del Micrófono

Asegúrate de que tu sistema operativo y cualquier software de seguridad (firewall, antivirus) permitan que Python acceda a tu micrófono.

### 5. Prueba de Configuración

Para verificar que todo está correctamente configurado, puedes ejecutar un script de prueba simple:

```python
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import os

def test_voice_setup():
    # Prueba de Reconocimiento de Voz
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Di algo para probar el micrófono...")
        try:
            audio = r.listen(source, timeout=5)
            text = r.recognize_google(audio, language="es-ES")
            print(f"Reconocido: {text}")
        except sr.UnknownValueError:
            print("No se pudo reconocer el audio.")
        except sr.RequestError as e:
            print(f"Error en el servicio de reconocimiento: {e}")

    # Prueba de Síntesis de Voz
    test_text = "Hola, esta es una prueba de síntesis de voz."
    try:
        tts = gTTS(text=test_text, lang='es')
        filename = "test_audio.mp3"
        tts.save(filename)
        print(f"Reproduciendo: '{test_text}'")
        playsound(filename)
        os.remove(filename)
    except Exception as e:
        print(f"Error en la síntesis o reproducción de voz: {e}")

if __name__ == "__main__":
    test_voice_setup()
```

Guarda este código como `test_voice.py` y ejecútalo:

```bash
python test_voice.py
```

Si escuchas la frase de prueba y tu voz es reconocida, la configuración básica es correcta.

## Solución de Problemas Comunes

*   **`PyAudio` Error:** Si encuentras errores relacionados con `PyAudio` (necesario para `SpeechRecognition` para acceder al micrófono), asegúrate de que esté correctamente instalado. En algunos sistemas, puede requerir dependencias del sistema (ej. `portaudio-dev` en Debian/Ubuntu).
*   **`playsound` no reproduce:** Asegúrate de que tienes un reproductor de MP3 predeterminado configurado en tu sistema que `playsound` pueda invocar.
*   **Errores de Conexión:** Verifica tu conexión a internet si estás usando APIs de voz en la nube.

