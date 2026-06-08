# client/web/core/mcp_client.py
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastmcp import Client as MCPClient
from config import Config


async def load_mcp_tools() -> list:
    async with MCPClient(Config.MCP_SERVER_URL) as mcp:
        tools_list = await mcp.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            }
            for t in tools_list
        ]


async def execute_tool(tool_name: str, arguments: dict) -> str:
    try:
        async with MCPClient(Config.MCP_SERVER_URL) as mcp:
            result = await mcp.call_tool(tool_name, arguments)
            items  = result if isinstance(result, list) else getattr(result, "content", [result])
            return "\n".join(i.text if hasattr(i, "text") else str(i) for i in items)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def parse_args(args) -> dict:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"raw": args}
    return args if isinstance(args, dict) else {}


def is_tool_error(result: str) -> bool:
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            return parsed.get("status") == "error"
    except Exception:
        pass
    return result.strip().startswith("❌")