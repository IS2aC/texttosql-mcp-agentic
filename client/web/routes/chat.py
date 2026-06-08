# client/web/routes/chat.py
import asyncio
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from loguru import logger
from core import session_store, mcp_client
from core.agent import run_agent

chat_bp = Blueprint("chat", __name__)

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _get_user_session():
    uid = session.get("user_session_id")
    if not uid:
        return None, None
    return uid, session_store.get(uid)


@chat_bp.route("/chat")
def chat():
    uid, user_session = _get_user_session()
    if not user_session:
        return redirect(url_for("register.register"))
    return render_template("chat.html", db_type=user_session["db_type"])


@chat_bp.route("/chat/message", methods=["POST"])
def chat_message():
    uid, user_session = _get_user_session()
    if not user_session:
        return jsonify({"error": "Session expirée"}), 401

    user_msg = (request.get_json().get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "Message vide"}), 400

    logger.info(f"[{uid[:8]}] USER >> {user_msg}")
    result = run_async(run_agent(user_msg, user_session))
    logger.info(f"[{uid[:8]}] AI   >> {result['answer'][:200]}")

    return jsonify(result)


@chat_bp.route("/chat/schema")
def chat_schema():
    uid, user_session = _get_user_session()
    if not user_session:
        return jsonify({"tables": []})

    # Récupère le schéma via MCP
    result = run_async(mcp_client.execute_tool(
        "full_schema", {"session_id": user_session["mcp_session_id"]}
    ))

    # Parse le schéma texte en structure JSON pour le frontend
    tables = []
    current = None
    for line in result.splitlines():
        if line.startswith("###"):
            if current:
                tables.append(current)
            current = {"name": line.replace("###", "").strip(), "columns": []}
        elif line.strip().startswith("•") and current:
            col_name = line.strip().lstrip("•").strip().split("—")[0].strip()
            current["columns"].append({
                "name":  col_name,
                "is_pk": col_name == "id",
                "is_fk": col_name.endswith("_id") and col_name != "id",
            })
    if current:
        tables.append(current)

    return jsonify({"tables": tables})


@chat_bp.route("/chat/reset", methods=["POST"])
def chat_reset():
    uid, _ = _get_user_session()
    if uid:
        session_store.reset_messages(uid)
    return jsonify({"status": "ok"})


@chat_bp.route("/chat/disconnect", methods=["POST"])
def chat_disconnect():
    uid, user_session = _get_user_session()
    if user_session:
        run_async(mcp_client.execute_tool("disconnect",
                  {"session_id": user_session["mcp_session_id"]}))
        session_store.delete(uid)
    session.clear()
    return redirect(url_for("home.home"))