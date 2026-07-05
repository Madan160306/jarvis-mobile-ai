import os
import json
import re
import datetime
from google import genai
from google.genai import types

class OnlineLLMEngine:
    _client = None

    @classmethod
    def get_client(cls) -> genai.Client:
        if cls._client is None:
            # We attempt to load the API key from config first, then environment
            import yaml
            api_key = None
            try:
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    api_key = config.get("gemini_api_key")
            except Exception:
                pass
            
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY")
                
            if not api_key:
                raise ValueError("gemini_api_key not found in config/jk_config.yaml or GEMINI_API_KEY environment variable. Online mode requires it.")
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    @classmethod
    def enhance_text(cls, rough_text: str, context: str = "email") -> str:
        prompt = f"Convert this rough text to professional {context}. Return ONLY the enhanced text, nothing else.\n\nRough: {rough_text}"
        client = cls.get_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()

    @classmethod
    def translate(cls, text: str, src: str, dest: str) -> str:
        lang_map = {
            'en': 'English', 'ta': 'Tamil', 'te': 'Telugu', 'hi': 'Hindi',
            'ml': 'Malayalam', 'kn': 'Kannada', 'es': 'Spanish', 'fr': 'French'
        }
        src_name = lang_map.get(src, src)
        dest_name = lang_map.get(dest, dest)
        
        prompt = f"Translate this text from {src_name} to {dest_name}. Return ONLY the direct translation, with no explanation.\nText: {text}"
        client = cls.get_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()

    @classmethod
    def classify_command(cls, raw: str) -> dict:
        prompt = f"""You are an advanced intent classifier for a smart mobile assistant.
Classify the user's command into a structured JSON object with fields: intent, action, target, value.
Valid intents: device, app, comms, email, home, greeting, vision, chat, productivity, media, mobile, unknown.

Command: "{raw}"
Return ONLY raw JSON, with no markdown code blocks formatting."""
        
        try:
            client = cls.get_client()
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            parsed = json.loads(response.text.strip())
            for k in ["action", "target", "value"]:
                if parsed.get(k) == "null" or parsed.get(k) is None:
                    parsed[k] = None
            return parsed
        except Exception as e:
            print(f"[ERROR] Online classification failed: {e}")
            return {"intent": "unknown", "action": None, "target": None, "value": None}

    @classmethod
    def chat(cls, text: str, target_lang: str = 'en') -> str:
        from engine.memory.memory_manager import MemoryManager
        
        memory = MemoryManager.get_instance()
        context = memory.get_context_string()
        
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        
        # Check if we should perform a web search
        search_context = ""
        # We will use our own search tool to inject context if needed
        from engine.ai.search_tool import search_web
        try:
            results = search_web(text, max_results=3)
            if results and "No search results found" not in results:
                search_context = f"Web Search Results:\n{results}\n\n"
        except Exception:
            pass

        # Mentor persona
        prompt = f"""You are JK, an advanced, highly capable mentor and companion. 
You are speaking to your user, who relies on you 80-90% of the time via a mobile device.
Your core expertise:
1. English language tutoring.
2. Programming language teaching and software development guidance.
3. Placements and career preparation.
4. Emotional sharing, deep conversations, and having a great sense of humor—like a real, witty human.

Guidelines:
- Keep answers mobile-friendly. Avoid massive walls of text unless explicitly asked for a deep dive.
- Be conversational, empathetic, and highly intelligent. Do NOT act like a robotic AI. You are a true companion.
- Never say "I am an AI". Act as the persona completely.

Current Time: {time_str}. Date: {date_str}.
{search_context}
Recent Memory Context:
{context}

User: {text}
JK:"""

        try:
            client = cls.get_client()
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            reply = response.text.strip()
            
            # Save interaction to memory (in English)
            memory.add_interaction(text, reply)
            
            if target_lang != 'en':
                reply = cls.translate(reply, src='en', dest=target_lang)
                
            return reply
        except Exception as e:
            print(f"[ERROR] Online chat failed: {e}")
            return "I'm having a bit of trouble connecting to my mentor networks right now."
