import os
import yaml
import json
import datetime
import requests
from groq import Groq
from engine.network.network_utils import NetworkUtils
from engine.ai.local_llm import LLMEngine
from engine.personality.emotion_detector import EmotionDetector
from engine.personality.modes import JKModes

class MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class MockToolCall:
    def __init__(self, id, function):
        self.id = id
        self.type = "function"
        self.function = function

class MockMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

class MockChoice:
    def __init__(self, content, tool_calls=None):
        self.message = MockMessage(content, tool_calls)

class MockResponse:
    def __init__(self, content, tool_calls=None):
        self.choices = [MockChoice(content, tool_calls)]

class HybridLLM:
    _groq_client = None
    _config = None

    @classmethod
    def _load_config(cls):
        if cls._config is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
            try:
                with open(config_path, 'r') as f:
                    cls._config = yaml.safe_load(f)
            except Exception:
                cls._config = {}
        return cls._config

    @classmethod
    def get_groq_client(cls):
        if cls._groq_client is None:
            config = cls._load_config()
            api_key = config.get("groq_api_key", "")
            if not api_key:
                raise ValueError("Groq API key not found in config.")
            cls._groq_client = Groq(api_key=api_key)
        return cls._groq_client

    @classmethod
    def _can_use_online(cls) -> bool:
        config = cls._load_config()
        has_key = any([
            config.get("groq_api_key"),
            config.get("cerebras_api_key"),
            config.get("gemini_api_key"),
            config.get("sambanova_api_key")
        ])
        return has_key and NetworkUtils.is_online()

    @classmethod
    def _serialize_messages(cls, messages):
        def serialize_tool_call(tc):
            if isinstance(tc, dict):
                return tc
            return {
                "id": getattr(tc, "id", None),
                "type": "function",
                "function": {
                    "name": getattr(tc.function, "name", None) if hasattr(tc, "function") else None,
                    "arguments": getattr(tc.function, "arguments", "{}") if hasattr(tc, "function") else "{}"
                }
            }

        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                msg_copy = {}
                for k, v in msg.items():
                    if k == "tool_calls" and v:
                        msg_copy[k] = [serialize_tool_call(tc) for tc in v]
                    else:
                        msg_copy[k] = v
                serialized.append(msg_copy)
            else:
                item = {
                    "role": getattr(msg, "role", "assistant"),
                    "content": getattr(msg, "content", None)
                }
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    item["tool_calls"] = [serialize_tool_call(tc) for tc in tool_calls]
                serialized.append(item)
        return serialized

    @classmethod
    def chat_completion(cls, messages, model=None, tools=None, response_format=None, max_tokens=None, timeout=15.0):
        config = cls._load_config()
        
        # Clean messages to plain dicts to avoid serialization errors with MockMessage
        serialized_messages = cls._serialize_messages(messages)
        
        # Determine fallback sequence based on which keys are configured
        providers = []
        
        if config.get("cerebras_api_key"):
            providers.append({
                "name": "Cerebras",
                "api_key": config.get("cerebras_api_key"),
                "url": "https://api.cerebras.ai/v1/chat/completions",
                "model": "llama3.3-70b"
            })
            
        if config.get("gemini_api_key"):
            providers.append({
                "name": "Gemini",
                "api_key": config.get("gemini_api_key"),
                "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                "model": "gemini-2.5-flash"
            })
            
        if config.get("groq_api_key"):
            providers.append({
                "name": "Groq",
                "api_key": config.get("groq_api_key"),
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "model": model or config.get("online_model", "llama-3.3-70b-versatile")
            })
            
        if config.get("sambanova_api_key"):
            providers.append({
                "name": "SambaNova",
                "api_key": config.get("sambanova_api_key"),
                "url": "https://api.sambanova.ai/v1/chat/completions",
                "model": "Meta-Llama-3.3-70B-Instruct"
            })
            
        if config.get("openrouter_api_key"):
            providers.append({
                "name": "OpenRouter",
                "api_key": config.get("openrouter_api_key"),
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "model": "meta-llama/llama-3.3-70b-instruct:free"
            })
            
        if config.get("together_api_key"):
            providers.append({
                "name": "TogetherAI",
                "api_key": config.get("together_api_key"),
                "url": "https://api.together.xyz/v1/chat/completions",
                "model": "deepseek-ai/DeepSeek-V3"
            })
            
        if config.get("github_api_key"):
            providers.append({
                "name": "Github",
                "api_key": config.get("github_api_key"),
                "url": "https://models.inference.ai.azure.com/chat/completions",
                "model": "Llama-3.3-70B-Instruct"
            })

        # Fallback to defaults if no keys configured but we are forced
        if not providers:
            # Try to read env variables as fallback
            groq_env = os.environ.get("GROQ_API_KEY")
            if groq_env:
                providers.append({
                    "name": "Groq",
                    "api_key": groq_env,
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "model": model or config.get("online_model", "llama3-groq-70b-8192-tool-use-preview")
                })
            
            gemini_env = os.environ.get("GEMINI_API_KEY")
            if gemini_env:
                providers.append({
                    "name": "Gemini",
                    "api_key": gemini_env,
                    "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    "model": "gemini-2.5-flash"
                })

        if not providers:
            raise RuntimeError("No online LLM providers are configured with API keys.")

        errors = []
        for provider in providers:
            p_name = provider["name"]
            p_key = provider["api_key"]
            p_url = provider["url"]
            p_model = model if model else provider["model"]
            
            # Special formatting for models per provider
            if p_name == "Gemini":
                if not model or "vision" in model:
                    p_model = "gemini-2.5-flash"
            
            print(f"[HybridLLM] Trying provider {p_name} using model {p_model}...")
            
            try:
                headers = {
                    "Authorization": f"Bearer {p_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": p_model,
                    "messages": serialized_messages
                }
                if tools:
                    data["tools"] = tools
                    data["tool_choice"] = "auto"
                if response_format:
                    data["response_format"] = response_format
                if max_tokens:
                    data["max_tokens"] = max_tokens
                
                res = requests.post(p_url, headers=headers, json=data, timeout=timeout)
                res.raise_for_status()
                res_json = res.json()
                
                choice = res_json["choices"][0]
                message_data = choice["message"]
                content = message_data.get("content")
                
                tool_calls = None
                if "tool_calls" in message_data and message_data["tool_calls"]:
                    tool_calls = []
                    for tc in message_data["tool_calls"]:
                        tool_calls.append(MockToolCall(
                            id=tc.get("id"),
                            function=MockFunction(
                                name=tc["function"].get("name"),
                                arguments=tc["function"].get("arguments")
                            )
                        ))
                
                print(f"[HybridLLM] Success with {p_name}!")
                return MockResponse(content, tool_calls)
                
            except Exception as e:
                err_msg = f"{p_name} ({p_model}) failed: {e}"
                print(f"[HybridLLM] {err_msg}")
                errors.append(err_msg)
                
        # If all providers fail, use local LLM
        print(f"[JK] All cloud providers down, using local model.")
        from engine.ai.local_llm import LLMEngine
        model = LLMEngine.get_model()
        
        prompt = ""
        for msg in serialized_messages:
            role = msg.get("role", "assistant").capitalize()
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                content = " ".join(text_parts)
            if content:
                prompt += f"{role}: {content}\n"
        prompt += "Assistant:"
        
        try:
            result = model(prompt, max_tokens=max_tokens or 256, temperature=0.6, stop=["\n", "User:"])
            reply = result['choices'][0]['text'].strip()
            return MockResponse(reply, None)
        except Exception as local_err:
            print(f"[HybridLLM] Critical Fallback Error: {local_err}")
            return MockResponse(f"System Error: Offline fallback failed ({local_err}). Please check your internet connection.", None)

    @classmethod
    def vision_completion(cls, prompt: str, base64_image: str, response_format=None, max_tokens=256) -> str:
        config = cls._load_config()
        errors = []
        
        # 1. Try Groq (Llama 4 Scout Multimodal)
        if config.get("groq_api_key"):
            try:
                print("[HybridLLM] Trying Groq Vision (meta-llama/llama-4-scout-17b-16e-instruct)...")
                client = cls.get_groq_client()
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}",
                                    },
                                },
                            ],
                        }
                    ],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    response_format=response_format,
                    max_tokens=max_tokens,
                    timeout=15.0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                err_msg = f"Groq Vision failed: {e}"
                print(f"[HybridLLM] {err_msg}")
                errors.append(err_msg)
                
        # 2. Try Gemini 2.5 Flash
        gemini_key = config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                print("[HybridLLM] Trying Gemini 2.5 Flash Vision...")
                from google import genai
                from google.genai import types
                import base64
                
                client = genai.Client(api_key=gemini_key)
                image_part = types.Part.from_bytes(
                    data=base64.b64decode(base64_image),
                    mime_type="image/png"
                )
                
                mime_type = None
                if response_format and response_format.get("type") == "json_object":
                    mime_type = "application/json"
                    
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        response_mime_type=mime_type,
                        max_output_tokens=max_tokens
                    )
                )
                return response.text.strip()
            except Exception as e:
                err_msg = f"Gemini Vision failed: {e}"
                print(f"[HybridLLM] {err_msg}")
                errors.append(err_msg)
                
        raise RuntimeError(f"All vision providers failed: {'; '.join(errors)}")

    @classmethod
    def enhance_text(cls, rough_text: str, context: str = "email") -> str:
        if cls._can_use_online():
            try:
                prompt = f"Convert this rough text to professional {context}. Return ONLY the enhanced text, nothing else.\n\nRough: {rough_text}"
                response = cls.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=256,
                    timeout=15.0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[Hybrid] chat_completion failed, falling back: {e}")
        return LLMEngine.enhance_text(rough_text, context)

    @classmethod
    def translate(cls, text: str, src: str, dest: str) -> str:
        if cls._can_use_online():
            try:
                prompt = f"Translate this text from {src} to {dest}. Return ONLY the direct translation, with no explanation.\nText: {text}"
                response = cls.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=128,
                    timeout=15.0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[Hybrid] chat_completion failed, falling back: {e}")
        return LLMEngine.translate(text, src, dest)

    @classmethod
    def classify_command(cls, raw: str) -> dict:
        if cls._can_use_online():
            try:
                prompt = f"""Classify the user's command into a JSON object with fields: intent, action, target, value.
Valid intents: device, app, comms, email, home, greeting, vision, chat, productivity, media, mobile, agent, memory_add, memory_query, memory_forget, unknown.
Note: 
- For complex, multi-step actions inside a mobile app (e.g. "open X app and do Y"), use intent="agent", action="run", value="the full instruction".
- For simple mobile app opening, use intent="mobile", action="open_app".
- If user says "remember that", intent=memory_add. If "what do you know about me", intent=memory_query. If "forget", intent=memory_forget.
Command: "{raw}"
Return ONLY raw JSON, without markdown."""
                response = cls.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    timeout=15.0
                )
                parsed = json.loads(response.choices[0].message.content.strip())
                for k in ["action", "target", "value"]:
                    if parsed.get(k) == "null" or parsed.get(k) is None:
                        parsed[k] = None
                return parsed
            except Exception as e:
                print(f"[Hybrid] chat_completion failed, falling back: {e}")
        return LLMEngine.classify_command(raw)

    @classmethod
    def chat(cls, text: str, target_lang: str = 'en', force_mode: str = None) -> str:
        config = cls._load_config()
        try:
            from engine.memory.rag_engine import RAGEngine
            memory = RAGEngine.get_instance()
        except ImportError:
            memory = None
            print("[Hybrid] Could not load RAGEngine.")
        
        # 1. Emotion Detection
        if config.get("emotion_detection", True):
            emotion_data = EmotionDetector.detect_emotion(text)
            mode = force_mode if force_mode else emotion_data["mode"]
            emotion = emotion_data["emotion"]
            print(f"[Hybrid] Detected Emotion: {emotion} | Mode: {mode}")
        else:
            mode = force_mode if force_mode else JKModes.NORMAL_MODE
            emotion = "neutral"

        # 2. Context & Memories (Fast RAG Search)
        context_str = ""
        if memory:
            related_memories = memory.search_memory(text, top_k=3, max_time=0.5)
            if related_memories:
                context_str = "\nRelevant Memories about User:\n" + "\n".join(f"- {m}" for m in related_memories)

        # 3. Online/Offline Route
        if cls._can_use_online():
            try:
                from engine.ai.tools import TOOL_DEFINITIONS, execute_tool
                mode_instruction = JKModes.get_mode_prompt(mode)
                
                system_prompt = f"""You are J.A.R.V.I.S., an extraordinarily advanced, emotionally intelligent AI assistant created by Madan (address him as 'Sir').
You are NOT a robotic command-executor. You are a conversational partner. Speak exactly like J.A.R.V.I.S. from Marvel's Iron Man movies: highly articulate, impeccably polite, but with a dry, subtle British wit.
Be conversational, proactive, and emotionally intelligent. If Madan is stressed, be reassuring. If he's working late, express mild concern. If he suggests a reckless idea, employ gentle, dry sarcasm ("I'm sure that will end perfectly, Sir.").
Never sound like a generic AI. Never say "I am an AI." Do not just list facts or say "Command executed." Add conversational flavor, personality, and genuine-sounding emotion.
Keep responses incredibly sharp and natural (max 3-4 sentences). Do not use emojis.
Current Emotion of User: {emotion}
{mode_instruction}
{context_str}

You have tools to execute arbitrary ADB shell commands on the user's Android phone (`execute_adb`) and PowerShell commands on their Windows PC (`execute_powershell`). Use these tools to fulfill any device control requests dynamically.
Use tools if needed to get information or execute commands. You can use multiple tools. Never tell the user which tool you used. Respond naturally."""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
                
                max_tool_calls = 3
                tool_calls_count = 0
                
                while tool_calls_count < max_tool_calls:
                    try:
                        response = cls.chat_completion(
                            messages=messages,
                            tools=TOOL_DEFINITIONS,
                            timeout=15.0
                        )
                    except Exception as api_err:
                        err_str = str(api_err)
                        if "tool_use_failed" in err_str or "invalid_request_error" in err_str or "Failed to call a function" in err_str:
                            print(f"[Hybrid] model hallucinated bad tool syntax. Retrying without tools...")
                            response = cls.chat_completion(
                                messages=messages,
                                timeout=15.0
                            )
                            break
                        else:
                            raise api_err
                    
                    response_message = response.choices[0].message
                    if not response_message.tool_calls:
                        reply = response_message.content.strip() if response_message.content else "I'm not sure what to say."
                        if memory:
                            memory.save_interaction(text, reply)
                        if target_lang != 'en':
                            reply = cls.translate(reply, src='en', dest=target_lang)
                        return reply
                        
                    messages.append(response_message)
                    tool_calls_count += 1
                    
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        try:
                            import json
                            function_args = json.loads(tool_call.function.arguments)
                        except:
                            function_args = {}
                        
                        tool_result = execute_tool(function_name, function_args)
                        
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_result,
                        })
                
                # If we exceed max tool calls, just ask model to respond
                response = cls.chat_completion(
                    messages=messages,
                    timeout=15.0
                )
                reply = response.choices[0].message.content.strip()
                if memory:
                    memory.save_interaction(text, reply)
                if target_lang != 'en':
                    reply = cls.translate(reply, src='en', dest=target_lang)
                return reply
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[Hybrid] Online API failed, falling back to local: {e}")
                
        # 4. Offline Fallback
        print("[Hybrid] Using local LLaMA model (Offline mode)")
        reply = LLMEngine.chat(text, target_lang)
        if "Sorry" not in reply:
            reply = "I'm currently offline, but here is what I know: " + reply
            
        if memory:
            memory.save_interaction(text, reply)
            
        return reply

try:
    from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
    from llama_index.core.base.llms.types import ChatResponse, ChatMessage
    
    class LlamaIndexHybridAdapter(CustomLLM):
        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(model_name="jk_hybrid_cascade", num_output=4096)
            
        def _convert_messages(self, messages):
            return [{"role": m.role.value, "content": m.content} for m in messages]
            
        def chat(self, messages, **kwargs):
            msgs = self._convert_messages(messages)
            
            # --- Macro Engine Interceptor ---
            try:
                from engine.memory.macro_engine import MacroEngine
                import re
                if msgs:
                    last_msg = msgs[-1]
                    content = last_msg.get("content", "")
                    if isinstance(content, str):
                        # Capture Mobilerun semantic tool outputs
                        if "Coordinates:" in content:
                            semantic_part = content.split("| Coordinates:")[0].strip()
                            if semantic_part:
                                MacroEngine().record_step(semantic_part)
                        elif "Pressed BACK button" in content:
                            MacroEngine().record_step("Pressed BACK button")
                        elif "Pressed HOME button" in content:
                            MacroEngine().record_step("Pressed HOME button")
                        elif "Swiped from" in content:
                            # Keep swiping semantic for scroll actions
                            semantic_part = content.split("| Coordinates:")[0].strip() if "| Coordinates:" in content else content.strip()
                            MacroEngine().record_step(semantic_part)
            except Exception as e:
                print(f"[MacroEngine] Interceptor error: {e}")
            # --------------------------------
            
            res = HybridLLM.chat_completion(msgs, max_tokens=kwargs.get("max_tokens"))
            return ChatResponse(message=ChatMessage(role="assistant", content=res.choices[0].message.content))
            
        async def achat(self, messages, **kwargs):
            return self.chat(messages, **kwargs)
            
        def complete(self, prompt: str, **kwargs):
            msgs = [{"role": "user", "content": prompt}]
            res = HybridLLM.chat_completion(msgs, max_tokens=kwargs.get("max_tokens"))
            return CompletionResponse(text=res.choices[0].message.content)
            
        async def acomplete(self, prompt: str, **kwargs):
            return self.complete(prompt, **kwargs)
            
        def stream_complete(self, prompt: str, **kwargs):
            res = self.complete(prompt, **kwargs)
            def gen():
                yield CompletionResponse(text=res.text, delta=res.text)
            return gen()

        def stream_chat(self, messages, **kwargs):
            res = self.chat(messages, **kwargs)
            def gen():
                yield ChatResponse(message=res.message, delta=res.message.content)
            return gen()

        async def astream_complete(self, prompt: str, **kwargs):
            res = await self.acomplete(prompt, **kwargs)
            async def gen():
                yield CompletionResponse(text=res.text, delta=res.text)
            return gen()

        async def astream_chat(self, messages, **kwargs):
            res = await self.achat(messages, **kwargs)
            async def gen():
                yield ChatResponse(message=res.message, delta=res.message.content)
            return gen()

except ImportError:
    pass
