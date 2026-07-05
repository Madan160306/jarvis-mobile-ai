#!/bin/bash
echo "=== JARVIS Termux Setup ==="

# Core packages
pkg update -y
pkg install -y python git termux-api \
  portaudio python-pyaudio \
  clang wget unzip python-numpy python-scipy

# Python packages (lightweight only)
pip install --upgrade pip
pip install vosk
pip install groq
pip install requests
pip install pyyaml
pip install chromadb
pip install sounddevice

# Download vosk small model
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..

echo "=== Setup Complete ==="
echo "Now do these manually:"
echo "1. Settings → Apps → Termux → Battery → Unrestricted"
echo "2. Settings → Apps → Termux:API → Battery → Unrestricted"
echo "3. Developer Options → Wireless Debugging → ON"
echo "Then run: python -m engine.core.jk_core"
