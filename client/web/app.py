# client/web/app.py
import os, sys
from flask import Flask
from loguru import logger
from config import Config
from routes.home import home_bp
from routes.register import register_bp
from routes.chat import chat_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    # Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(chat_bp)

    # Logger
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add("logs/app.log", rotation="10MB", level="INFO", encoding="utf-8")
    logger.add(sys.stderr, level="WARNING")

    return app


# if __name__ == "__main__":
#     app = create_app()
#     print("🌐 http://127.0.0.1:5050")
#     app.run(debug=False, port=5050, threaded=True)


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5050))
    print(f"🌐 http://{host}:{port}")
    app.run(debug=False, host=host, port=port, threaded=True)