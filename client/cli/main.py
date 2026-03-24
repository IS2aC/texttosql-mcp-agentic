# client_cli.py
import json
import ollama
from fastmcp import Client as MCPClient
import asyncio
import sys
from utils import build_system_prompt 
import os
from dotenv import load_dotenv  
load_dotenv("/home/isaac/mcp-agentic-analytics/client/.env")

# ===============================
# Configuration
# ===============================
OLLAMA_MODEL = "qwen2.5:14b"
MCP_SERVER_URL = "http://127.0.0.1:8000/sse"
MAX_TOOL_RETRIES = 3
DANGEROUS_TOOLS = ["drop_table", "create_table", "create_user"]

# ===============================
# Session Context
# ===============================
DB_TYPES = {
    "1": "postgresql",
    "2": "mysql",
    "3": "excel",
    "4": "csv",
    "5": "demo",
}

def prompt_credentials(db_type: str) -> dict:
    """
    Collecte les credentials selon le type de source.
    Retourne un dict prêt à passer à connect_datasource.
    """
    print(f"\n🔐 Credentials pour {db_type.upper()} :")

    if db_type in ("postgresql", "mysql"):
        return {
            "host":     input("  Host     : ").strip(),
            "port":     int(input("  Port     : ").strip() or (5432 if db_type == "postgresql" else 3306)), 
            "database": input("  Database : ").strip(),
            "user":     input("  User     : ").strip(),
            "password": input("  Password : ").strip(),
        }

    if db_type in ("excel", "csv"):
        return {
            "file_path": input("  Chemin du fichier : ").strip(),
        }

    if db_type == "demo":
        return {
            "host": os.getenv("DEMO_DB_HOST"),
            "port": os.getenv("DEMO_DB_PORT"),
            "database": os.getenv("DEMO_DB_NAME"),
            "user": os.getenv("DEMO_DB_USER"),
            "password": os.getenv("DEMO_DB_PASSWORD"),
        }

    raise ValueError(f"Type inconnu : {db_type}")


def select_datasource() -> tuple[str, dict]:
    """
    Menu interactif de sélection de la source de données.
    Retourne (db_type, credentials).
    """
    print("\n📦 Sources de données disponibles :")
    for key, label in DB_TYPES.items():
        print(f"  {key}. {label.upper()}")

    choice = input("\nVotre choix : ").strip()
    db_type = DB_TYPES.get(choice)
    if not db_type:
        print("❌ Choix invalide.")
        sys.exit(1)

    credentials = prompt_credentials(db_type)
    return db_type, credentials


# ===============================
# Load MCP tools
# ===============================
async def load_mcp_tools() -> list:
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
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
    except Exception as e:
        print(f"❌ Impossible de joindre le MCP server : {e}")
        sys.exit(1)


# ===============================
# Execute Tool
# ===============================
async def execute_tool(tool_name: str, arguments: dict) -> str:
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
            result = await mcp.call_tool(tool_name, arguments)

            # Normalisation du résultat
            items = result if isinstance(result, list) else getattr(result, "content", [result])
            parts = [item.text if hasattr(item, "text") else str(item) for item in items]
            return "\n".join(parts)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ===============================
# Helpers
# ===============================
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
    except (json.JSONDecodeError, ValueError):
        pass
    return result.strip().startswith("❌")


# ===============================
# Handle Tool Calls
# ===============================
async def handle_tool_calls(tool_calls: list, messages: list, session_id: str) -> bool:
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        args = parse_args(tool_call["function"]["arguments"])

        # Injection systématique — plus de condition fragile
        args["session_id"] = session_id

        print(f"\n🔧 Outil appelé  : {tool_name}")
        print(f"📝 Arguments     : {json.dumps(args, indent=2, ensure_ascii=False)}")

        # Confirmation pour les outils dangereux
        if tool_name in DANGEROUS_TOOLS:
            confirm = input("⚠️  Action sensible. Confirmer ? (yes) : ").strip()
            if confirm.lower() != "yes":
                print("❌ Action annulée.")
                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps({"status": "cancelled", "message": "Action annulée par l'utilisateur."}),
                })
                continue

        result = await execute_tool(tool_name, args)
        print(f"\n✅ Résultat :\n{result}")

        messages.append({"role": "tool", "name": tool_name, "content": result})

    return True


# ===============================
# Agentic Loop
# ===============================
async def agentic_loop(messages: list, tools: list, session_id: str):
    """
    Boucle agentique : le LLM appelle des outils jusqu'à
    produire une réponse finale ou atteindre MAX_TOOL_RETRIES.
    """
    retry_count = 0

    while retry_count <= MAX_TOOL_RETRIES:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=tools,
            stream=False,
        )

        assistant_message = response["message"]
        tool_calls = assistant_message.get("tool_calls") or []

        # Pas d'outil → réponse finale
        if not tool_calls:
            content = assistant_message.get("content") or "(pas de réponse)"
            print(f"\n🤖 Assistant :\n{content}")
            messages.append(assistant_message)
            return

        messages.append(assistant_message)
        await handle_tool_calls(tool_calls, messages, session_id)

        last_result = messages[-1].get("content", "")
        if is_tool_error(last_result):
            retry_count += 1
            if retry_count > MAX_TOOL_RETRIES:
                print(f"\n⚠️  Max retries ({MAX_TOOL_RETRIES}) atteint.")
                messages.append({
                    "role": "user",
                    "content": "Les outils retournent des erreurs répétées. Explique ce qui s'est passé.",
                })
            else:
                print(f"\n🔁 Erreur détectée — retry {retry_count}/{MAX_TOOL_RETRIES}...")
        else:
            retry_count = 0  # reset si pas d'erreur


# ===============================
# Main
# ===============================
async def main():
    print("=" * 45)
    print("   🧠  Agentic Analytics — CLI")
    print("=" * 45)

    # 1. Sélection de la source
    db_type, credentials = select_datasource()

    # 2. Chargement des outils MCP
    print("\n🔍 Connexion au MCP server...")
    tools = await load_mcp_tools()
    print(f"✅ {len(tools)} outil(s) chargé(s).")

    # 3. Enregistrement de la session via MCP
    import uuid
    session_id = str(uuid.uuid4())
    print(f"\n🔗 Enregistrement session [{session_id[:8]}...]")

    init_result = await execute_tool("connect_datasource", {
        "session_id": session_id,
        "db_type": db_type,
        "credentials": credentials,
    })
    print(f"   {init_result}")

    if "error" in init_result.lower():
        print("❌ Échec de connexion. Vérifiez vos credentials.")
        sys.exit(1)

    # 4. Récupération du schéma complet pour enrichir le sys prompt
    # ✅ Maintenant
    print("\n📐 Génération / chargement du sys prompt...")
    system_prompt = build_system_prompt(db_type=db_type, credentials=credentials)
    print("✅ Sys prompt prêt.")

    messages = [{"role": "system", "content": system_prompt}]

    print("\n✅ Prêt. Posez vos questions en langage naturel.")
    print("   Tapez 'exit' pour quitter, 'reset' pour changer de source.\n")

    # 6. Boucle de chat
    while True:
        user_msg = input("👤 Vous : ").strip()
        if not user_msg:
            continue

        if user_msg.lower() == "exit":
            await execute_tool("disconnect", {"session_id": session_id})
            print("👋 Session fermée.")
            break

        if user_msg.lower() == "reset":
            await execute_tool("disconnect", {"session_id": session_id})
            await main()  # relance le flux depuis le début
            return

        messages.append({"role": "user", "content": user_msg})
        await agentic_loop(messages, tools, session_id)
        print("\n" + "-" * 45 + "\n")


# ===============================
# Entry Point
# ===============================
if __name__ == "__main__":
    asyncio.run(main())