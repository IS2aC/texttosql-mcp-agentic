# client/web/routes/register.py
import uuid, os, sys, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template, request, redirect, url_for, session
from config import Config
from core import session_store, mcp_client
from system_prompt_generator import SystemPromptGenerator
import asyncio
from loguru import logger

register_bp = Blueprint("register", __name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ──────────────────────────────────────────────
# Credentials
# ──────────────────────────────────────────────
def _build_credentials(db_type: str, form, files) -> dict:
    if db_type in ("postgresql", "mysql"):
        return {
            "host":     form.get("host", "").strip(),
            "port":     int(form.get("port", 5432)),
            "database": form.get("database", "").strip(),
            "user":     form.get("user", "").strip(),
            "password": form.get("password", ""),
        }
    if db_type == "supabase":
        return {
            "host":      form.get("host", "").strip(),
            "port":      int(form.get("port", 5432)),
            "database":  form.get("database", "postgres").strip() or "postgres",
            "user":      form.get("user", "").strip(),
            "password":  form.get("password", ""),
            "pool_mode": form.get("pool_mode", "session").strip(),
            "sslmode":   "require",
        }
    if db_type in ("excel", "csv"):
        file = files.get("file")
        if not file or not file.filename:
            raise ValueError("Aucun fichier fourni.")
        ext         = file.filename.rsplit(".", 1)[-1].lower()
        actual_type = "csv" if ext == "csv" else "excel"
        path        = f"/tmp/{uuid.uuid4()}_{file.filename}"
        file.save(path)
        return {"file_path": path, "_resolved_type": actual_type}
    if db_type == "demo":
        return Config.DEMO_CREDENTIALS
    raise ValueError(f"Type de base de données inconnu : {db_type}")


# ──────────────────────────────────────────────
# Lecture du fichier contexte métier (.txt)
# ──────────────────────────────────────────────
def _read_context_file(files) -> str:
    """
    Lit le fichier .txt de contexte métier uploadé.
    Retourne "" si absent ou illisible.
    """
    context_file = files.get("context_file")
    if not context_file or not context_file.filename:
        return ""
    try:
        text = context_file.read().decode("utf-8", errors="ignore").strip()
        logger.info(
            f"Contexte métier chargé ({len(text)} caractères) "
            f"depuis '{context_file.filename}'"
        )
        return text
    except Exception as e:
        logger.warning(f"Impossible de lire le fichier contexte : {e}")
        return ""


# ──────────────────────────────────────────────
# Erreur MCP
# ──────────────────────────────────────────────
def _parse_mcp_error(raw: str) -> str:
    try:
        parsed = json.loads(raw)
        return parsed.get("error") or parsed.get("message") or raw
    except (json.JSONDecodeError, TypeError):
        return raw


# ──────────────────────────────────────────────
# Chargement du system prompt
# ──────────────────────────────────────────────
def _load_system_prompt(db_type: str, credentials: dict, context_text: str = "") -> str:
    """
    Délègue entièrement à SystemPromptGenerator.
    - context_text transmis à Groq → base de connaissance enrichie
    - Résultat sauvegardé dans le cache (SHA256 credentials)
    - Rechargé depuis le cache si identique
    """
    if db_type in ("postgresql", "mysql", "supabase", "demo"):
        gen = SystemPromptGenerator(
            database_name=credentials["database"],
            user_name=credentials["user"],
            password=credentials["password"],
            host_name=credentials["host"],
            port=credentials["port"],
            db_type=db_type,
            sslmode=credentials.get("sslmode"),
        )
        # context_text transmis → Groq génère une base de connaissance enrichie
        # sauvegardée dans le cache
        prompt_path = gen.construct_system_prompt(context_text=context_text)

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    prompt_file = f"shared/prompts/{db_type}.txt"
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


# ──────────────────────────────────────────────
# Rendu erreur
# ──────────────────────────────────────────────
def _render_error(error_msg: str, db_type: str = None):
    return render_template(
        "register.html",
        db_types=Config.DB_TYPES,
        db_type=db_type,
        error=error_msg,
    )


# ──────────────────────────────────────────────
# Route principale
# ──────────────────────────────────────────────
@register_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", db_types=Config.DB_TYPES)

    db_type = request.form.get("db_type", "").strip()
    if not db_type:
        return _render_error("Veuillez sélectionner un type de base de données.")

    # 1. Credentials
    try:
        credentials = _build_credentials(db_type, request.form, request.files)
    except (ValueError, Exception) as e:
        logger.warning(f"Erreur credentials ({db_type}): {e}")
        return _render_error(str(e), db_type)

    # 2. Contexte métier optionnel
    context_text = _read_context_file(request.files)

    # 3. Connexion MCP
    mcp_session_id = str(uuid.uuid4())
    try:
        init_result = run_async(mcp_client.execute_tool("connect_datasource", {
            "session_id":  mcp_session_id,
            "db_type":     db_type,
            "credentials": credentials,
        }))
    except Exception as e:
        logger.error(f"Erreur MCP inattendue : {e}")
        return _render_error("Impossible de joindre le serveur MCP. Vérifiez qu'il est démarré.", db_type)

    if "error" in init_result.lower():
        clean_error = _parse_mcp_error(init_result)
        logger.warning(f"Connexion refusée ({db_type}): {clean_error}")
        return _render_error(f"Connexion échouée : {clean_error}", db_type)

    # 4. System prompt — Groq génère la base de connaissance (schéma + contexte métier)
    try:
        system_prompt = _load_system_prompt(db_type, credentials, context_text)
    except Exception as e:
        logger.error(f"Erreur chargement system prompt : {e}")
        return _render_error("Connexion réussie mais impossible de charger le profil analytique.", db_type)

    # 5. Outils MCP
    try:
        tools = run_async(mcp_client.load_mcp_tools())
    except Exception as e:
        logger.error(f"Erreur chargement outils MCP : {e}")
        return _render_error("Impossible de charger les outils analytiques.", db_type)

    # 6. Session utilisateur
    user_session_id = str(uuid.uuid4())
    session_store.create(user_session_id, {
        "mcp_session_id": mcp_session_id,
        "db_type":        db_type,
        "messages":       [{"role": "system", "content": system_prompt}],
        "tools":          tools,
    })

    session["user_session_id"] = user_session_id
    logger.info(f"Session créée ({db_type}) → {user_session_id[:8]}…")
    return redirect(url_for("chat.chat"))