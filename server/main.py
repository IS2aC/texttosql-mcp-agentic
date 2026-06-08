# main.py
from mcp.server.fastmcp import FastMCP
from tools.schema_tools import get_schema_tools
from tools.query_tools import get_query_tools
from session import register_session, close_session
import json
import os


host = os.getenv("FASTMCP_HOST", "0.0.0.0")
port = int(os.getenv("FASTMCP_PORT", 8000))
mcp = FastMCP("server-mcp-generic", host=host, port=port)

# Injection des outils 
get_schema_tools(mcp)
get_query_tools(mcp)

@mcp.tool(description="Initialise une connexion à une source de données.")
def connect_datasource(session_id: str, db_type: str, credentials: dict) -> str:
    try:
        return register_session(session_id, db_type, credentials)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@mcp.tool(description="Ferme la session et libère les ressources.")
def disconnect(session_id: str) -> str:
    close_session(session_id)
    return f"Session {session_id} fermée."

if __name__ == "__main__":
    mcp.run(transport="sse")
    # production
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)



    