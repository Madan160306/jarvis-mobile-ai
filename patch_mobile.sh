#!/bin/bash
wget -O engine/ai/hybrid_llm.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/ai/hybrid_llm.py
wget -O engine/voice/hybrid_asr.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/voice/hybrid_asr.py
wget -O engine/voice/audio_pipeline.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/voice/audio_pipeline.py
wget -O engine/voice/wake_word.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/voice/wake_word.py
wget -O engine/voice/tts_engine.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/voice/tts_engine.py
wget -O engine/voice/voice_auth.py https://raw.githubusercontent.com/Madan160306/jarvis-mobile-ai/main/engine/voice/voice_auth.py
echo "Mobile Patch Complete! Run: python -m engine.core.jk_core"
