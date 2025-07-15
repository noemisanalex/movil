#!/bin/bash
set -e

# Navega al directorio del proyecto
cd /data/data/com.termux/files/home/agp/

# --- IMPORTANTE ---
# Asegúrate de que tu GOOGLE_API_KEY esté configurada en tu perfil de Termux (~/.bashrc o ~/.zshrc).

# Verifica si el entorno virtual existe
if [ ! -d ".venv" ]; then
    echo "Error: El entorno virtual '.venv' no se encontró. Por favor, ejecuta 'make setup' primero."
    exit 1
fi

# Ejecuta el asistente de voz
source .venv/bin/activate
python asistente_voz.py
