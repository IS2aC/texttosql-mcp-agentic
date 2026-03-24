# # client/web/core/agent.py
# import time
# import ollama
# from loguru import logger
# from config import Config
# from core.mcp_client import execute_tool, parse_args, is_tool_error


# async def run_agent(user_message: str, user_session: dict) -> dict:
#     messages       = user_session["messages"]
#     mcp_session_id = user_session["mcp_session_id"]
#     tools          = user_session["tools"]

#     start        = time.perf_counter()
#     sql_used     = None
#     tools_called = []
#     retry_count  = 0
#     final_answer = "(pas de réponse)"

#     messages.append({"role": "user", "content": user_message})

#     while retry_count <= Config.MAX_TOOL_RETRIES:
#         response = ollama.chat(
#             model=Config.OLLAMA_MODEL,
#             messages=messages,
#             tools=tools,
#             stream=False,
#             options={"temperature": 0.1},
#         )

#         assistant_message = response["message"]
#         tool_calls        = assistant_message.get("tool_calls") or []

#         if not tool_calls:
#             final_answer = assistant_message.get("content") or "(pas de réponse)"
#             messages.append(assistant_message)
#             break

#         messages.append(assistant_message)

#         for tool_call in tool_calls:
#             tool_name = tool_call["function"]["name"]
#             args      = parse_args(tool_call["function"]["arguments"])
#             args["session_id"] = mcp_session_id  # injection automatique
#             tools_called.append(tool_name)

#             if tool_name in Config.DANGEROUS_TOOLS:
#                 result = '{"status": "cancelled", "message": "Opération refusée."}'
#             else:
#                 result = await execute_tool(tool_name, args)

#             if tool_name == "query_data":
#                 sql_used = args.get("sql_query")

#             messages.append({"role": "tool", "name": tool_name, "content": result})

#         last_result = messages[-1].get("content", "")
#         if is_tool_error(last_result):
#             retry_count += 1
#             if retry_count > Config.MAX_TOOL_RETRIES:
#                 messages.append({
#                     "role": "user",
#                     "content": "Les outils retournent des erreurs. Explique ce qui s'est passé.",
#                 })
#             continue

#         retry_count = 0

#     return {
#         "answer":       final_answer,
#         "sql_used":     sql_used,
#         "tools_called": tools_called,
#         "elapsed_s":    round(time.perf_counter() - start, 3),
#     }



# client/web/core/agent.py
# import time
# import ollama
# from loguru import logger
# from config import Config
# from core.mcp_client import execute_tool, parse_args, is_tool_error


# async def run_agent(user_message: str, user_session: dict) -> dict:
#     messages       = user_session["messages"]
#     mcp_session_id = user_session["mcp_session_id"]
#     tools          = user_session["tools"]

#     start        = time.perf_counter()
#     sql_used     = None
#     tools_called = []
#     retry_count  = 0
#     final_answer = "(pas de réponse)"

#     messages.append({"role": "user", "content": user_message})

#     while retry_count <= Config.MAX_TOOL_RETRIES:
#         response = ollama.chat(
#             model=Config.OLLAMA_MODEL,
#             messages=messages,
#             tools=tools,
#             stream=False,
#             options={"temperature": 0.1},
#         )

#         assistant_message = response["message"]
#         tool_calls        = assistant_message.get("tool_calls") or []
#         content           = assistant_message.get("content") or ""

#         # ✅ Pas de tool call → réponse finale
#         if not tool_calls:
#             final_answer = content if content.strip() else "(pas de réponse)"
#             messages.append(assistant_message)
#             break

#         # ✅ Il y a des tool calls : on les exécute
#         messages.append(assistant_message)

#         for tool_call in tool_calls:
#             tool_name = tool_call["function"]["name"]
#             args      = parse_args(tool_call["function"]["arguments"])
#             args["session_id"] = mcp_session_id
#             tools_called.append(tool_name)

#             logger.info(f"[agent] tool={tool_name} args={args}")

#             if tool_name in Config.DANGEROUS_TOOLS:
#                 result = '{"status": "cancelled", "message": "Opération refusée."}'
#             else:
#                 result = await execute_tool(tool_name, args)

#             logger.debug(f"[agent] tool result ({tool_name}): {str(result)[:300]}")

#             if tool_name == "query_data":
#                 sql_used = args.get("sql_query")

#             messages.append({"role": "tool", "name": tool_name, "content": result})

#         # ✅ Vérification d'erreur sur le dernier résultat tool
#         last_result = messages[-1].get("content", "")
#         if is_tool_error(last_result):
#             retry_count += 1
#             logger.warning(f"[agent] tool error (retry {retry_count}): {last_result[:200]}")
#             if retry_count > Config.MAX_TOOL_RETRIES:
#                 # ✅ Demander à Ollama d'expliquer l'erreur plutôt que de sortir silencieusement
#                 messages.append({
#                     "role": "user",
#                     "content": "Les outils retournent des erreurs. Explique ce qui s'est passé en français.",
#                 })
#                 response = ollama.chat(
#                     model=Config.OLLAMA_MODEL,
#                     messages=messages,
#                     tools=tools,
#                     stream=False,
#                     options={"temperature": 0.1},
#                 )
#                 final_answer = response["message"].get("content") or "Erreur lors de l'exécution des outils."
#                 messages.append(response["message"])
#                 break
#             continue

#         retry_count = 0
#         # ✅ Continuer la boucle pour laisser Ollama synthétiser les résultats

#     logger.info(f"[agent] final_answer: {final_answer[:200]}")

#     return {
#         "answer":       final_answer,
#         "sql_used":     sql_used,
#         "tools_called": list(dict.fromkeys(tools_called)),  # dédoublonner
#         "elapsed_s":    round(time.perf_counter() - start, 3),
#     }



# client/web/core/agent.py
import time
import ollama
from loguru import logger
from config import Config
from core.mcp_client import execute_tool, parse_args, is_tool_error

# Client Ollama pointant vers l'hôte configuré (host machine via Docker)
_ollama_client = ollama.Client(host=Config.OLLAMA_HOST)


async def run_agent(user_message: str, user_session: dict) -> dict:
    messages       = user_session["messages"]
    mcp_session_id = user_session["mcp_session_id"]
    tools          = user_session["tools"]

    start        = time.perf_counter()
    sql_used     = None
    tools_called = []
    retry_count  = 0
    final_answer = "(pas de réponse)"

    messages.append({"role": "user", "content": user_message})

    while retry_count <= Config.MAX_TOOL_RETRIES:
        response = _ollama_client.chat(
            model=Config.OLLAMA_MODEL,
            messages=messages,
            tools=tools,
            stream=False,
            options={"temperature": 0.1},
        )

        assistant_message = response["message"]
        tool_calls        = assistant_message.get("tool_calls") or []
        content           = assistant_message.get("content") or ""

        if not tool_calls:
            final_answer = content if content.strip() else "(pas de réponse)"
            messages.append(assistant_message)
            break

        messages.append(assistant_message)

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            args      = parse_args(tool_call["function"]["arguments"])
            args["session_id"] = mcp_session_id
            tools_called.append(tool_name)

            logger.info(f"[agent] tool={tool_name} args={args}")

            if tool_name in Config.DANGEROUS_TOOLS:
                result = '{"status": "cancelled", "message": "Opération refusée."}'
            else:
                result = await execute_tool(tool_name, args)

            logger.debug(f"[agent] tool result ({tool_name}): {str(result)[:300]}")

            if tool_name == "query_data":
                sql_used = args.get("sql_query")

            messages.append({"role": "tool", "name": tool_name, "content": result})

        last_result = messages[-1].get("content", "")
        if is_tool_error(last_result):
            retry_count += 1
            logger.warning(f"[agent] tool error (retry {retry_count}): {last_result[:200]}")
            if retry_count > Config.MAX_TOOL_RETRIES:
                messages.append({
                    "role": "user",
                    "content": "Les outils retournent des erreurs. Explique ce qui s'est passé en français.",
                })
                response = _ollama_client.chat(
                    model=Config.OLLAMA_MODEL,
                    messages=messages,
                    tools=tools,
                    stream=False,
                    options={"temperature": 0.1},
                )
                final_answer = response["message"].get("content") or "Erreur lors de l'exécution des outils."
                messages.append(response["message"])
                break
            continue

        retry_count = 0

    logger.info(f"[agent] final_answer: {final_answer[:200]}")

    return {
        "answer":       final_answer,
        "sql_used":     sql_used,
        "tools_called": list(dict.fromkeys(tools_called)),
        "elapsed_s":    round(time.perf_counter() - start, 3),
    }