#!/data/data/com.termux/files/usr/bin/bash

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

# 5. Instalar Gemini CLI globalmente (npm)
echo "🌟 Instalando Gemini CLI..."
npm install -g @google/gemini-cli

# 6. Instalar n8n globalmente (npm)
echo "🌟 Instalando n8n..."
npm install -g n8n

# 7. Instalar Home Assistant Core (pip)
echo "🌟 Instalando Home Assistant Core..."
pip install --upgrade pip
pip install homeassistant

echo "✅ Setup completado."

echo "🔥 Para iniciar n8n, ejecuta: n8n"
echo "🔥 Para iniciar Home Assistant, ejecuta: hass"
