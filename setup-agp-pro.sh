#!/data/data/com.termux/files/usr/bin/bash
set -e # Salir inmediatamente si un comando falla

echo "🔥 Setup AutogestiónPro - Opción 1 - Termux PRO sin Docker 🔥"

# 1. Actualizar sistema
echo "🛠 Actualizando paquetes..."
pkg update -y && pkg upgrade -y

# 2. Instalar herramientas base
echo "📦 Instalando Node.js, Python, Git, curl, micro y termux-api..."
pkg install -y nodejs python git curl micro termux-api proot

# 3. Limpiar pyenv y config viejas
echo "🧹 Limpiando pyenv y configuraciones antiguas..."
proot rm -rf ~/.pyenv 2>/dev/null
sed -i '/pyenv/d' ~/.bashrc

# 4. Crear .bashrc limpio y útil
echo "⚙️ Configurando .bashrc..."
cat > ~/.bashrc << 'EOF'
# ~/.bashrc limpio para Termux - AutogestiónPro

export PS1="\u@\h:\w $ "
alias ll='ls -la'
alias update='pkg update && pkg upgrade -y'
alias cls='clear'
export PATH=$PREFIX/bin:$PATH
EOF

source ~/.bashrc

# 7. Configurar entorno virtual de Python e instalar dependencias
echo "🐍 Configurando entorno virtual de Python e instalando dependencias..."
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup completado."

# 8. Configurar GOOGLE_API_KEY

if grep -q "export GOOGLE_API_KEY=" ~/.bashrc; then
    echo "🔑 GOOGLE_API_KEY ya está configurada en ~/.bashrc. Saltando configuración."
else
    echo "
"
    echo "🔑 Ahora, vamos a configurar tu GOOGLE_API_KEY."
    echo "   Puedes obtenerla en https://aistudio.google.com/app/apikey"
    read -p "Por favor, introduce tu GOOGLE_API_KEY: " api_key

    # Añadir la API Key a .bashrc para que esté disponible en futuras sesiones
    echo "export GOOGLE_API_KEY=\"$api_key\"" >> ~/.bashrc
    source ~/.bashrc # Cargar la variable en la sesión actual

    echo "✅ GOOGLE_API_KEY configurada y guardada en ~/.bashrc."
fi

echo "
"
echo "🔥 Para iniciar n8n, ejecuta: n8n"
echo "🔥 Para iniciar Home Assistant, ejecuta: hass"
echo "🔥 Para iniciar el asistente Gemini, ejecuta: ./start_gemini_assistant.sh"
