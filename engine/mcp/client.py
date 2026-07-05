import asyncio
import threading
import sys
import os
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Force UTF-8 on Windows stdout/stderr to prevent UnicodeEncodeError
import io
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', write_through=True)
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', write_through=True)
    except Exception:
        pass

class MCPClientSync:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = MCPClientSync()
                cls._instance.start()
        return cls._instance

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.session = None
        self._exit_stack = None

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        """Starts the MCP server process and initializes client session."""
        future = asyncio.run_coroutine_threadsafe(self._init_session(), self.loop)
        future.result() # Wait for initialization

    async def _init_session(self):
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path],
            env=os.environ.copy()
        )
        
        # Connect to stdio server
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns the list of tools registered on the server."""
        future = asyncio.run_coroutine_threadsafe(self._list_tools_async(), self.loop)
        return future.result()

    async def _list_tools_async(self):
        if not self.session:
            return []
        res = await self.session.list_tools()
        # Format tools to list of dicts matching openAI schema
        tools_list = []
        for tool in res.tools:
            tools_list.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        return tools_list

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Executes a tool on the server and returns the string response."""
        future = asyncio.run_coroutine_threadsafe(self._call_tool_async(name, arguments), self.loop)
        return future.result()

    async def _call_tool_async(self, name: str, arguments: Dict[str, Any]):
        if not self.session:
            raise RuntimeError("MCP Client Session not initialized.")
        res = await self.session.call_tool(name, arguments)
        
        # Extract text content from content objects
        contents = []
        for content in res.content:
            if hasattr(content, "text"):
                contents.append(content.text)
            elif isinstance(content, dict) and "text" in content:
                contents.append(content["text"])
        return "\n".join(contents)

    def stop(self):
        """Stops the server process and closes the session."""
        future = asyncio.run_coroutine_threadsafe(self._close_session(), self.loop)
        try:
            future.result(timeout=5.0)
        except Exception:
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2.0)

    async def _close_session(self):
        if self._exit_stack:
            await self._exit_stack.aclose()

if __name__ == "__main__":
    # Test client connection
    print("Connecting to MCP Server...")
    client = MCPClientSync.get_instance()
    print("Discovered tools:")
    tools = client.list_tools()
    for t in tools:
        print(f" - {t['function']['name']}: {t['function']['description']}")
    
    print("\nCalling get_time tool...")
    res = client.call_tool("get_time", {})
    print(f"Result: {res}")
    
    client.stop()
    print("Done.")
