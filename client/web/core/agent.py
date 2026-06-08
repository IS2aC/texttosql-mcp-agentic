import time
from openai import OpenAI
from loguru import logger
from config import Config
from core.mcp_client import execute_tool, parse_args, is_tool_error

_openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

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
        response = _openai_client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            tools=tools,
            temperature=0.1,
        )

        assistant_message = response.choices[0].message
        tool_calls        = assistant_message.tool_calls or []
        content           = assistant_message.content or ""

        if not tool_calls:
            final_answer = content if content.strip() else "(pas de réponse)"
            messages.append({"role": "assistant", "content": content})
            break

        messages.append({"role": "assistant", "content": content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tool_calls
        ]})

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            args      = parse_args(tool_call.function.arguments)
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

            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })

        last_result = messages[-1].get("content", "")
        if is_tool_error(last_result):
            retry_count += 1
            logger.warning(f"[agent] tool error (retry {retry_count}): {last_result[:200]}")
            if retry_count > Config.MAX_TOOL_RETRIES:
                messages.append({
                    "role":    "user",
                    "content": "Les outils retournent des erreurs. Explique ce qui s'est passé en français.",
                })
                response = _openai_client.chat.completions.create(
                    model=Config.OPENAI_MODEL,
                    messages=messages,
                    tools=tools,
                    temperature=0.1,
                )
                final_answer = response.choices[0].message.content or "Erreur lors de l'exécution des outils."
                messages.append({"role": "assistant", "content": final_answer})
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
