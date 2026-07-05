# JARVIS MOBILE AI
**CONFIDENTIAL & PROPRIETARY DOCUMENTATION**
*Project Owner: Sandeep*
*Date: July 2026*

> **CONFIDENTIALITY NOTICE:** This document and the source code it describes contain proprietary, confidential algorithms and architecture designs belonging exclusively to the Project Owner. Unauthorized distribution, reproduction, or reverse engineering is strictly prohibited.

---

## 1. System Overview
JARVIS (Just A Rather Very Intelligent System) is a state-of-the-art, voice-activated AI assistant designed to run autonomously across both **Windows Desktop** environments and **Android (Samsung) Mobile** devices. 

It is designed to be fully self-reliant, utilizing **Hybrid Cloud-to-Edge** pipelines. If internet access is available, JARVIS leverages massive cloud LLMs for reasoning and transcription. If offline, the system gracefully degrades to local on-device models, ensuring zero downtime.

## 2. Core Architecture

The system is built on a modular, event-driven graph architecture (LangGraph) allowing for complex decision routing, tool usage, and memory retrieval.

### A. The Brain (LangGraph Core)
Located in `engine/core/agent.py`, the core routing logic processes all transcripts:
1. **Intent Analyzer**: A lightning-fast LLM call that sanitizes phonetic errors (e.g., "play Dudue OST") and classifies the user's intent into: `fast_path`, `vision`, `phone_task`, or `chat`.
2. **Fast Path Engine**: Instantly intercepts commands like "turn on torch" or "send WhatsApp to Mom" and executes them directly via Deep Links, bypassing the heavy visual processing latency.
3. **Visual Execution (Mobilerun)**: For complex tasks requiring screen interaction, JARVIS analyzes the Android UI tree and uses a Vision-Language Model to navigate the screen autonomously.
4. **Conversational/Chat Node**: Standard QA routing.

### B. Voice Pipeline (STT & TTS)
Located in `engine/voice/`.
*   **Wake Word (`wake_word.py`)**: Powered by `openwakeword`. Runs a continuous background listener looking for the acoustic signature of "Hey Jarvis" (threshold optimized to 0.45 for the owner's voice).
*   **Authentication (`voice_auth.py`)**: Uses `speechbrain/spkrec-ecapa-voxceleb` to extract biometric voice embeddings. Rejects unauthorized users from issuing system commands.
*   **Hybrid ASR (`hybrid_asr.py`)**:
    *   *Primary*: Groq Cloud `whisper-large-v3-turbo` for near-instant, highly accurate transcription.
    *   *Desktop Fallback*: Local `faster-whisper` (int8 quantized) for offline desktop usage.
    *   *Mobile Fallback*: Local `Vosk` (small en-us model) for lightweight offline Android usage.
*   **Text-to-Speech (`tts_engine.py`)**:
    *   *Primary*: Offline `Kokoro-ONNX` (voice: `af_heart`) for highly realistic, emotional speech synthesis.
    *   *Mobile Fallback*: `termux-tts-speak` for native Android vocalization.

### C. Device Controllers (Hardware & OS)
Located in `engine/device/`. JARVIS features a dual-controller setup to handle strict OEM security policies (like Samsung Knox).
*   **ADB Controller (`android_controller.py`)**: Used when running via Desktop tethered to the phone. Pulls UI XML dumps, runs semantic self-healing on broken UI buttons using `all-MiniLM-L6-v2`, and injects taps via ADB.
*   **Termux Controller (`termux_controller.py`)**: Used when JARVIS runs *natively* on the Samsung phone. Because Knox blocks localhost ADB, JARVIS routes all hardware commands directly to the `termux-api` (Torch, SMS, WhatsApp Deep Links, Battery, Notifications).

### D. Memory & Context
Located in `engine/memory/`.
*   **RAG Engine**: Uses `ChromaDB` to store past conversations and user preferences as vectorized embeddings. When the user asks a question, JARVIS queries the vector database to recall past context.
*   **Semantic Waypoints**: When JARVIS successfully completes a complex UI navigation task, it caches the exact "semantic path" (the sequence of buttons clicked). Next time the user asks for the same task, JARVIS skips the expensive visual search and instantly replays the waypoints.

---

## 3. Environment & Deployment Modes

JARVIS automatically detects its host environment at runtime via `engine/core/jk_core.py` and shapes its architecture accordingly.

### Mode 1: Desktop Host (Windows)
*   **Trigger**: No Termux environment detected.
*   **Hardware Control**: `adb shell`
*   **Wake Word**: High-precision `openwakeword`
*   **Offline ASR**: `faster-whisper`
*   **UI Automation**: Full XML hierarchy parsing + Vision LLM

### Mode 2: Native Android (Samsung Termux Lite Mode)
*   **Trigger**: `/data/data/com.termux` detected.
*   **Hardware Control**: `termux-api` bypass (circumventing Samsung Knox ADB block)
*   **Wake Word**: `openwakeword` Python port.
*   **Offline ASR**: `Vosk` (lightweight CPU inference).
*   **UI Automation**: Disabled (Requires Root/ADB). Relies entirely on explicit `termux-api` Deep Links for Calls, WhatsApp, SMS, and Hardware toggles.
*   **Power**: Utilizes `termux-wake-lock` to prevent Android from killing JARVIS while the screen is off.

---

## 4. Getting Started (Mobile Deployment)

To deploy this exact configuration to the target Samsung device:
1. Install **Termux** and **Termux:API** from F-Droid (Not the Google Play Store).
2. Allow both apps Unrestricted Battery Access in Android Settings.
3. Run the following inside Termux:
```bash
termux-setup-storage
pkg update -y && pkg upgrade -y
git clone https://github.com/Madan160306/jarvis-mobile-ai.git
cd jarvis-mobile-ai
bash setup_termux.sh
```
4. Start the engine: `python -m engine.core.jk_core`

---
*End of Document*
