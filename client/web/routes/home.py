import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template
from core import session_store                     

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def home():
    return render_template("home.html", active_sessions=session_store.count())

@home_bp.route("/health")
def health():
    from config import Config
    return {
        "status":          "ok",
        "model":           Config.OLLAMA_MODEL,
        "active_sessions": session_store.count(),
    }