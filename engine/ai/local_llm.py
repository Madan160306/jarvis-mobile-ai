from llama_cpp import Llama
import os
import json

class LLMEngine:
    _model = None
    MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
    
    @classmethod
    def get_model(cls) -> Llama:
        if cls._model is None:
            if not os.path.exists(cls.MODEL_PATH):
                raise FileNotFoundError(f"Model not found at {cls.MODEL_PATH}. Run download script.")
            cls._model = Llama(
                model_path=cls.MODEL_PATH,
                n_ctx=2048,        # Context window
                n_threads=8,       # Increase threads for speed
                n_gpu_layers=20,   # Offload layers to GPU
                use_mlock=True,    # Keep model in RAM
                n_batch=512,       # Batch size for prompt processing
                verbose=False,
            )
        return cls._model
    
    @classmethod
    def enhance_text(cls, rough_text: str, context: str = "email") -> str:
        """Convert rough input to professional text."""
        prompt = f"""You are a professional writer. Convert this rough text to 
professional {context}. Return ONLY the enhanced text, nothing else.

Rough: {rough_text}
Professional:"""
        model = cls.get_model()
        result = model(prompt, max_tokens=256, temperature=0.3, stop=["\n\n"])
        return result['choices'][0]['text'].strip()
    
    _parser_grammar = None

    @classmethod
    def translate(cls, text: str, src: str, dest: str) -> str:
        """Translate text between languages offline using local LLaMA model."""
        lang_map = {
            'en': 'English',
            'ta': 'Tamil',
            'te': 'Telugu',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'kn': 'Kannada',
            'es': 'Spanish',
            'fr': 'French'
        }
        src_name = lang_map.get(src, src)
        dest_name = lang_map.get(dest, dest)
        
        prompt = f"""Translate this text from {src_name} to {dest_name}. Return ONLY the direct translation, with no explanation, introduction, formatting or extra words.
Text: {text}
Translation:"""
        model = cls.get_model()
        result = model(prompt, max_tokens=128, temperature=0.1, stop=["\n"])
        return result['choices'][0]['text'].strip().strip('"')

    @classmethod
    def classify_command(cls, raw: str) -> dict:
        """Parse ambiguous command to structured intent using few-shot classification."""
        prompt = f"""You are an advanced intent classifier for a smart assistant.
Classify the user's command into a structured JSON object with fields: intent, action, target, value.
Valid intents: device, app, comms, email, home, greeting, vision, chat, productivity, media, mobile, unknown.

Examples:
Command: "turn on the flashlight"
JSON: {{"intent": "mobile", "action": "torch", "target": "torch", "value": "on"}}

Command: "how are you today?"
JSON: {{"intent": "chat", "action": "respond", "target": null, "value": null}}

Command: "open chrome"
JSON: {{"intent": "app", "action": "open", "target": "chrome", "value": null}}

Command: "what files are in this folder"
JSON: {{"intent": "chat", "action": "respond", "target": null, "value": null}}

Command: "hello jk"
JSON: {{"intent": "greeting", "action": "greet", "target": null, "value": null}}

Command: "tell me a joke"
JSON: {{"intent": "chat", "action": "respond", "target": null, "value": null}}

Command: "what is the time"
JSON: {{"intent": "chat", "action": "respond", "target": null, "value": null}}

Command: "play some music"
JSON: {{"intent": "media", "action": "ytmusic_play", "target": null, "value": "music"}}

Command: "check mobile battery"
JSON: {{"intent": "mobile", "action": "check_battery", "target": null, "value": null}}

Command: "{raw}"
JSON:"""
        model = cls.get_model()
        
        # Compile grammar lazily
        if cls._parser_grammar is None:
            from llama_cpp import LlamaGrammar
            grammar_text = r"""
root ::= "{" ws "\"intent\"" ws ":" ws intent-value "," ws "\"action\"" ws ":" ws string-or-null "," ws "\"target\"" ws ":" ws string-or-null "," ws "\"value\"" ws ":" ws string-or-null "}" ws
intent-value ::= "\"device\"" | "\"app\"" | "\"comms\"" | "\"email\"" | "\"home\"" | "\"greeting\"" | "\"vision\"" | "\"chat\"" | "\"productivity\"" | "\"media\"" | "\"mobile\"" | "\"unknown\""
string-or-null ::= string | "null"
string ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
ws ::= [ \t\n\r]*
"""
            cls._parser_grammar = LlamaGrammar.from_string(grammar_text)
            
        result = model(prompt, max_tokens=128, temperature=0.1, grammar=cls._parser_grammar)
        try:
            parsed = json.loads(result['choices'][0]['text'].strip())
            # Convert JSON null values or string 'null' to None
            for k in ["action", "target", "value"]:
                if parsed.get(k) == "null" or parsed.get(k) is None:
                    parsed[k] = None
            return parsed
        except Exception as e:
            print(f"[ERROR] Failed to parse grammar-enforced LLM output: {e}")
            return {"intent": "unknown", "action": None, "target": None, "value": None}

    @classmethod
    def chat(cls, text: str, target_lang: str = 'en') -> str:
        """Generate a conversational response like JK with a specific personality, and support basic offline tools."""
        import re
        import datetime
        import random
        from engine.memory.memory_manager import MemoryManager
        
        memory = MemoryManager.get_instance()
        context = memory.get_context_string()
        
        query_lower = text.lower().strip()
        query_clean = re.sub(r'[?.!,]', '', query_lower).strip()
        
        # Override conversational response lookup
        if "what can you do" in query_clean:
            reply = "I can control your mobile settings, open apps, set reminders, manage emails, and talk with you. Anything you need, just ask."
            memory.add_interaction(text, reply)
            return reply
            
        elif "how are you" in query_clean:
            reply = "I'm doing great, feeling pretty good. How about you?"
            memory.add_interaction(text, reply)
            return reply
            
        elif "what time is it" in query_clean or "tell me the time" in query_clean:
            now = datetime.datetime.now()
            reply = f"It's {now.strftime('%I:%M %p')}."
            memory.add_interaction(text, reply)
            return reply
            
        elif "what is todays date" in query_clean or "what is the date" in query_clean or "date today" in query_clean:
            now = datetime.datetime.now()
            reply = f"Today is {now.strftime('%A, %B %d, %Y')}."
            memory.add_interaction(text, reply)
            return reply
            
        elif "tell me a joke" in query_clean:
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why was the computer cold? It left its Windows open!",
                "Parallel lines have so much in common. It’s a shame they’ll never meet.",
                "What did the cell phone say to the charger? You make me feel alive!"
            ]
            reply = random.choice(jokes)
            memory.add_interaction(text, reply)
            return reply
            
        elif "who are you" in query_clean:
            reply = "I am J.A.R.V.I.S., an extraordinarily advanced artificial intelligence created by you, Sir."
            memory.add_interaction(text, reply)
            return reply

        # Offline Tool Support - naive matching for offline safety
        try:
            from engine.ai.tools import execute_tool
            if "weather in" in query_clean:
                city = query_clean.split("weather in")[-1].strip()
                res = execute_tool("check_weather", {"city": city})
                return res
            elif "calculate" in query_clean:
                expr = query_clean.split("calculate")[-1].strip()
                res = execute_tool("calculate", {"expression": expr})
                return res
        except Exception as e:
            print(f"[LLMEngine] Offline tool error: {e}")

        # Otherwise, ask the LLM
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        
        prompt = (
            "You are J.A.R.V.I.S., an extraordinarily advanced, emotionally intelligent AI assistant created by Madan (address him as 'Sir'). "
            "You are NOT a robotic command-executor. You are a conversational partner. Speak exactly like J.A.R.V.I.S. from Marvel's Iron Man movies: highly articulate, impeccably polite, but with a dry, subtle British wit. "
            "Be conversational and emotionally intelligent. Add genuine personality. "
            "Keep your responses extremely short—strictly a maximum of ONE sentence.\n"
            f"Current Local Time: {time_str}. Current Date: {date_str}.\n"
            f"{context}User: {text}\nJARVIS:"
        )
        
        model = cls.get_model()
        result = model(prompt, max_tokens=40, temperature=0.6, stop=["\n", "User:"])
        reply = result['choices'][0]['text'].strip()
        
        if not reply:
            reply = "I'm not sure, tell me more about it."
            
        memory.add_interaction(text, reply)
            
        if target_lang != 'en':
            try:
                reply = cls.translate(reply, src='en', dest=target_lang)
            except Exception as e:
                print(f"[ERROR] Could not translate response to {target_lang}: {e}")
                
        return reply
