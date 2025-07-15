SHELL := /bin/bash

.PHONY: setup start clean

setup:
	@echo "🚀 Ejecutando el script de configuración inicial..."
	@./setup-agp-pro.sh

start:
	@echo "🔊 Iniciando el asistente Gemini..."
	@./start_gemini_assistant.sh

clean:
	@echo "🧹 Limpiando archivos generados..."
	@rm -rf .venv
	@find . -name "__pycache__" -exec rm -rf {} + 
	@rm -f *.mp3
	@echo "✅ Limpieza completada."