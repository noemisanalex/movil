import pyttsx3
engine = pyttsx3.init()
engine.save_to_file('Hola, esto es una prueba del motor de voz pyttsx3.', 'test_audio.mp3')
engine.runAndWait()