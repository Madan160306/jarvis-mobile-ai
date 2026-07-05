import json
import time
import uuid
import os
import asyncio
from typing import Annotated, Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from engine.ai.hybrid_llm import HybridLLM
from engine.device.android_controller import AndroidController

# Initialize MobileAgent lazily to avoid blocking imports
try:
    from engine.device.mobile_agent import JKMobileAgent
except ImportError:
    JKMobileAgent = None

def merge_messages(left: list, right: list) -> list:
    new_messages = list(left) if left else []
    new_messages.extend(right)
    return new_messages

class AgentState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], merge_messages]
    intent: str
    task: str
    result: str

class Agent:
    def __init__(self):
        self.name = "JK Core Agent"
        self.mobile_agent = None

    def process(self, text: str, lang: str = 'en', thread_id: str = None) -> str:
        # Load memory and emotion (mocking existing architecture hooks)
        try:
            from engine.memory.rag_engine import RAGEngine
            memory = RAGEngine.get_instance()
        except ImportError:
            memory = None

        if not thread_id:
            thread_id = str(uuid.uuid4())

        # Define the Graph
        workflow = StateGraph(AgentState)

        # Node 1: Intent Analysis
        def classify_intent(state: AgentState):
            user_text = state["messages"][-1]["content"]
            
            # Simple heuristic for fast path (hardware controls and app launching)
            # This is a fast-track bypass to avoid LLM latency for extremely clean commands.
            text_lower = user_text.lower().strip()
            if any(k in text_lower for k in ["brightness", "volume", "wifi", "wi-fi", "wi fi", "bluetooth", "lock screen", "lock", "airplane"]):
                return {"intent": "fast_path", "task": user_text}
            
            # Fast path for opening/launching apps (e.g., "open whatsapp", "launch settings")
            if any(text_lower.startswith(prefix) for prefix in ["open ", "launch ", "start "]) and len(text_lower.split()) <= 4:
                return {"intent": "fast_path", "task": user_text}
            
            prompt = (
                "You are the phonetic input normalizer and intent classifier for JK, a mobile voice assistant.\n"
                "The user text is a voice transcript and may contain slurred speech, run-on words, or phonetic typos.\n\n"
                "Task:\n"
                "1. Correct any spelling or phonetic typos to make a clean command.\n"
                "2. Classify the intent into one of these categories:\n"
                "   - 'vision': The user asks about what is currently on their screen (e.g. 'what is on my screen', 'summarize this page').\n"
                "   - 'fast_path': Commands to toggle hardware settings (WiFi, Bluetooth) or open apps, OR exact deep-link actions with explicit data (e.g. 'call 9876543210', 'play X on YouTube').\n"
                "   - 'phone_task': Complex multi-step GUI actions that require screen clicking, OR actions with missing explicit data (e.g. 'call Sandy', 'send a whatsapp to John'). Since we don't have John's number, we MUST use Mobilerun to visually search for John.\n"
                "   - 'chat': Conversational chat or questions.\n\n"
                f"User Text: \"{user_text}\"\n\n"
                "Reply ONLY with a raw JSON object containing these keys:\n"
                "{\n"
                "  \"normalized_text\": \"<corrected clean text>\",\n"
                "  \"intent\": \"vision\" | \"fast_path\" | \"phone_task\" | \"chat\",\n"
                "  \"deep_link_action\": \"whatsapp_contact\" | \"youtube_search\" | \"phone_call\" | null,\n"
                "  \"deep_link_param\": \"<extracted param value, e.g. the phone NUMBER or youtube QUERY>\" | null\n"
                "}"
            )
            try:
                res = HybridLLM.chat(prompt)
                clean_res = res.strip().replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_res)
                normalized_text = data.get("normalized_text", user_text)
                intent = data.get("intent", "phone_task")
                
                # Pass deep link parameters through the state if they exist
                state["deep_link_action"] = data.get("deep_link_action")
                state["deep_link_param"] = data.get("deep_link_param")
            except Exception as e:
                print(f"[Agent] Intent classification error: {e}")
                normalized_text = user_text
                intent = "phone_task" # Default to phone task on failure
                
            return {"intent": intent, "task": normalized_text, "deep_link_action": state.get("deep_link_action"), "deep_link_param": state.get("deep_link_param")}

        # Node 2: Conversational Chat
        def conversational_chat(state: AgentState):
            user_text = state["task"]
            prompt = f"You are JK, a warm AI assistant. Reply naturally: {user_text}"
            res = HybridLLM.chat(prompt)
            return {"result": res}

        # Node 3: Fast Path ADB & Deep Link Execution
        def fast_path_execute(state: AgentState):
            # Use cleanly extracted LLM parameters instead of heuristics
            deep_action = state.get("deep_link_action")
            deep_param = state.get("deep_link_param")
            
            if deep_action and deep_param:
                from engine.device.deep_links import execute_deep_link
                # Map single param to the dictionary deep_links expects
                param_dict = {}
                if deep_action == "whatsapp_contact":
                    param_dict = {"phone": deep_param}
                elif deep_action == "whatsapp_send":
                    # Assume param contains phone and text
                    parts = deep_param.split("|")
                    param_dict = {"phone": parts[0]}
                    if len(parts) > 1:
                        param_dict["text"] = parts[1]
                elif deep_action == "youtube_search":
                    param_dict = {"query": deep_param}
                elif deep_action == "phone_call":
                    # Extra validation to ensure it's a number, not a name
                    import re
                    if re.match(r'^[\d\+\-\s]+$', deep_param):
                        param_dict = {"number": deep_param}
                    else:
                        return {"result": "I need a phone number to make a fast call, otherwise I must search visually via Mobilerun."}
                
                if param_dict:
                    deep_res = execute_deep_link(deep_action, param_dict)
                    if deep_res:
                        return {"result": deep_res}

            return {"result": "Command too complex for fast path. Transitioning to visual Mobilerun UI execution."}
            
        # Node 5: Vision Context
        def vision_analyze(state: AgentState):
            user_text = state["task"]
            try:
                from engine.vision.screen_vision import analyze_screen_with_vision
                res = analyze_screen_with_vision(user_text)
            except Exception as e:
                res = f"Vision error: {e}"
            return {"result": res}

        # Node 4: Complex Mobilerun Execution
        def mobile_agent_execute(state: AgentState):
            task = state["task"]
            
            # --- MACRO ENGINE INITIALIZATION ---
            try:
                from engine.memory.macro_engine import MacroEngine
                macro_engine = MacroEngine()
                
                # Start recording the new semantic path for this task
                macro_engine.start_recording(task)
            except Exception as e:
                print(f"[MacroEngine] Error: {e}")
                macro_engine = None
            # -----------------------------------
            
            if not self.mobile_agent:
                if JKMobileAgent:
                    self.mobile_agent = JKMobileAgent()
                else:
                    return {"result": "Error: Mobilerun framework not installed."}
            
            print(f"[Mobilerun] Starting autonomous execution for: {task}")
            
            # Run async function in sync loop
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self.mobile_agent.execute(task))
            except RuntimeError:
                # If loop is already running or missing
                result = asyncio.run(self.mobile_agent.execute(task))
                
            # --- MACRO ENGINE SAVE ---
            if macro_engine:
                success = "error" not in str(result).lower() and "failed" not in str(result).lower()
                macro_engine.save_macro(success)
            # -------------------------
                
            return {"result": f"Task completed: {result}"}

        # Edges
        def route_intent(state: AgentState):
            return state["intent"]
            
        def route_fast_path(state: AgentState):
            res = state.get("result", "")
            if "Transitioning to visual Mobilerun" in res or "I need a phone number to make a fast call" in res:
                # Instead of speaking the fallback string, clear it and let Mobilerun run silently
                state["result"] = "" 
                return "phone_task"
            return "end"

        workflow.add_node("classify", classify_intent)
        workflow.add_node("chat", conversational_chat)
        workflow.add_node("fast_path", fast_path_execute)
        workflow.add_node("phone_task", mobile_agent_execute)
        workflow.add_node("vision", vision_analyze)

        workflow.set_entry_point("classify")
        
        workflow.add_conditional_edges(
            "classify",
            route_intent,
            {
                "chat": "chat",
                "fast_path": "fast_path",
                "phone_task": "phone_task",
                "vision": "vision"
            }
        )
        
        workflow.add_conditional_edges(
            "fast_path",
            route_fast_path,
            {
                "end": END,
                "phone_task": "phone_task"
            }
        )
        
        workflow.add_edge("chat", END)
        workflow.add_edge("phone_task", END)
        workflow.add_edge("vision", END)

        # Memory Checkpointer
        os.makedirs("logs", exist_ok=True)
        conn = sqlite3.connect("logs/jk_checkpoints.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        graph = workflow.compile(checkpointer=checkpointer)
        thread_config = {"configurable": {"thread_id": thread_id}}

        # Execute
        initial_state = {"messages": [{"role": "user", "content": text}]}
        final_state = graph.invoke(initial_state, thread_config)
        
        reply = final_state.get("result", "Done.")
        if memory:
            memory.save_interaction(text, reply)
            
        return reply

