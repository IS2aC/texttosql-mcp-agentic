# client/web/routes/chat.py
import asyncio
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from loguru import logger
from core import session_store, mcp_client
from core.agent import run_agent
from system_prompt_generator import SystemPromptGenerator

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

    result = run_async(mcp_client.execute_tool(
        "full_schema", {"session_id": user_session["mcp_session_id"]}
    ))

    tables  = []
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

    logger.info(f"[schema] {len(tables)} tables parsées pour {user_session['db_type']}")
    return jsonify({"tables": tables})


@chat_bp.route("/chat/reset", methods=["POST"])
def chat_reset():
    uid, user_session = _get_user_session()
    if uid and user_session:
        session_store.reset_messages(uid)
    return jsonify({"status": "ok"})


@chat_bp.route("/chat/refresh", methods=["POST"])
def chat_refresh():
    """
    Rafraîchit le system prompt sans quitter le chat.
    - Recharge le schéma depuis la DB (nouvelles tables détectées)
    - Réutilise le .ctx persisté OU prend un nouveau context_file uploadé
    - Régénère la base de connaissance via Groq
    - Met à jour messages[0] dans la session + reset historique
    """
    uid, user_session = _get_user_session()
    if not user_session:
        return jsonify({"error": "Session expirée"}), 401

    db_type     = user_session.get("db_type")
    credentials = user_session.get("credentials")

    if not credentials:
        return jsonify({
            "error": "Credentials non disponibles. Reconnectez-vous."
        }), 400

    # Lecture du nouveau context_file si uploadé via la modal
    new_context_text = ""
    if "context_file" in request.files:
        context_file = request.files.get("context_file")
        if context_file and context_file.filename:
            try:
                new_context_text = context_file.read().decode("utf-8", errors="ignore").strip()
                logger.info(
                    f"[{uid[:8]}] refresh — nouveau context "
                    f"({len(new_context_text)} chars) reçu"
                )
            except Exception as e:
                logger.warning(f"[refresh] Lecture context_file échouée : {e}")

    # Refresh du system prompt
    try:
        gen = SystemPromptGenerator(
            database_name=credentials["database"],
            user_name=credentials["user"],
            password=credentials["password"],
            host_name=credentials["host"],
            port=credentials["port"],
            db_type=db_type,
            sslmode=credentials.get("sslmode"),
        )
        prompt_path, tables_count = gen.refresh(new_context_text=new_context_text)

        with open(prompt_path, "r", encoding="utf-8") as f:
            new_system_prompt = f.read()

    except Exception as e:
        logger.error(f"[{uid[:8]}] refresh erreur : {e}")
        return jsonify({"error": f"Refresh échoué : {str(e)}"}), 500

    # Mise à jour session : nouveau sys prompt + reset historique
    user_session["messages"] = [{"role": "system", "content": new_system_prompt}]

    logger.info(f"[{uid[:8]}] Refresh OK — {tables_count} tables")
    return jsonify({
        "status":       "ok",
        "tables_count": tables_count,
        "message":      f"Schéma mis à jour — {tables_count} tables détectées",
    })


@chat_bp.route("/chat/disconnect", methods=["POST"])
def chat_disconnect():
    uid, user_session = _get_user_session()
    if user_session:
        run_async(mcp_client.execute_tool(
            "disconnect", {"session_id": user_session["mcp_session_id"]}
        ))
        session_store.delete(uid)
    session.clear()
    return redirect(url_for("home.home"))