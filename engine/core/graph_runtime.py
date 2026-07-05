import os
import sqlite3
import json
from typing import Annotated, Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from engine.ai.hybrid_llm import HybridLLM
from engine.mcp.client import MCPClientSync

# Custom reducer to append new messages
def merge_messages(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    new_messages = list(left) if left else []
    for msg in right:
        new_messages.append(msg)
    return new_messages

class AgentState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], merge_messages]
    tool_calls_count: int
    errors: List[str]
    human_approved: bool

# SQLite Checkpointer helper
def get_db_checkpointer(db_path: str) -> SqliteSaver:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # We use check_same_thread=False since SqliteSaver operates inside execution threads
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)

def is_high_risk_tool(tool_calls: List[Dict[str, Any]]) -> bool:
    """Detects if any of the planned tool calls are high-risk/destructive."""
    if not tool_calls:
        return False
    for tc in tool_calls:
        name = tc.get("function", {}).get("name", "")
        args = tc.get("function", {}).get("arguments", "")
        # Labeled as high risk
        if name in ["execute_adb_command", "execute_adb"]:
            args_lower = str(args).lower()
            if any(k in args_lower for k in ["uninstall", "rm ", "reboot", "format", "delete"]):
                return True
        if name in ["forget_memory"]:
            return True
    return False

def create_agent_graph(agent):
    workflow = StateGraph(AgentState)
    
    # 1. Reason Node
    def reason(state: AgentState) -> Dict[str, Any]:
        print(f"[GraphRuntime] Reason Node - Step {state.get('tool_calls_count', 0) + 1}")
        
        # Check if we exceeded max tool calls
        if state.get("tool_calls_count", 0) >= agent.max_tool_calls:
            print("[GraphRuntime] Max tool calls reached. Exiting graph.")
            return {
                "messages": [{"role": "assistant", "content": "I have reached the execution limit for this task. Please let me know if you would like me to proceed differently."}]
            }
            
        try:
            mcp_client = MCPClientSync.get_instance()
            mcp_tools = mcp_client.list_tools()
            
            # Prune context to prevent 400 Bad Request from massive XML dumps
            messages_to_send = state["messages"]
            if len(messages_to_send) > 8:
                messages_to_send = messages_to_send[:2] + messages_to_send[-6:]
            
            # We call the LLM chat completions
            response = HybridLLM.chat_completion(
                messages=messages_to_send,
                tools=mcp_tools,
                timeout=15.0
            )
            
            response_message = response.choices[0].message
            msg_dict = {
                "role": "assistant",
                "content": response_message.content or ""
            }
            if response_message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            
            return {
                "messages": [msg_dict],
                "tool_calls_count": state.get("tool_calls_count", 0) + (1 if response_message.tool_calls else 0)
            }
        except Exception as e:
            err_str = str(e)
            print(f"[GraphRuntime] LLM Error: {err_str}")
            
            # Check for malformed tool calls in error message (recovery pathway)
            recovered_msg = None
            if "tool_use_failed" in err_str or "Failed to call a function" in err_str:
                import re
                match = re.search(r'<function=(\w+)[>}]?(.*?)</function>', err_str)
                if not match:
                    match = re.search(r'<function=(\w+)(.*?)</function>', err_str)
                if match:
                    func_name = match.group(1)
                    try:
                        args_str = match.group(2).strip()
                        recovered_msg = {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": f"call_rec_{state.get('tool_calls_count', 0)}",
                                    "type": "function",
                                    "function": {
                                        "name": func_name,
                                        "arguments": args_str if args_str.startswith("{") else "{" + args_str
                                    }
                                }
                            ]
                        }
                        print(f"[GraphRuntime] Recovered malformed tool call: {func_name}")
                    except:
                        pass
            
            if recovered_msg:
                return {
                    "messages": [recovered_msg],
                    "tool_calls_count": state.get("tool_calls_count", 0) + 1
                }
                
            # If no recovery, fall back to offline local LLM
            print("[GraphRuntime] Falling back to offline local LLM.")
            from engine.ai.local_llm import LLMEngine
            user_text = ""
            for m in reversed(state["messages"]):
                if m["role"] == "user":
                    user_text = m["content"]
                    break
            
            reply = LLMEngine.chat(user_text)
            return {
                "messages": [{"role": "assistant", "content": "Offline Fallback: " + reply}],
                "errors": [err_str]
            }
            
    # 2. Execute Tool Node
    def execute_tools(state: AgentState) -> Dict[str, Any]:
        print("[GraphRuntime] Execute Tools Node")
        last_msg = state["messages"][-1]
        
        if "tool_calls" not in last_msg or not last_msg["tool_calls"]:
            return {}
            
        tool_messages = []
        for tc in last_msg["tool_calls"]:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except:
                func_args = {}
                
            print(f"[GraphRuntime] Running tool: {func_name}({func_args})")
            mcp_client = MCPClientSync.get_instance()
            tool_result = mcp_client.call_tool(func_name, func_args)
            print(f"[GraphRuntime] Tool result: {tool_result}")
            
            tool_messages.append({
                "role": "tool",
                "name": func_name,
                "content": str(tool_result),
                "tool_call_id": tc.get("id")
            })
            
        return {
            "messages": tool_messages
        }
        
    # 3. Router Edge
    def should_continue(state: AgentState):
        last_msg = state["messages"][-1]
        
        if "tool_calls" in last_msg and last_msg["tool_calls"]:
            return "execute_tools"
            
        return END

    # Define the graph structure
    workflow.add_node("reason", reason)
    workflow.add_node("execute_tools", execute_tools)
    
    workflow.set_entry_point("reason")
    
    workflow.add_conditional_edges(
        "reason",
        should_continue,
        {
            "execute_tools": "execute_tools",
            END: END
        }
    )
    
    workflow.add_edge("execute_tools", "reason")
    
    return workflow
