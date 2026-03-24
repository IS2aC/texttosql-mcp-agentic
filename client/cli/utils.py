
from system_prompt_generator import SystemPromptGenerator

#### je reflechi a comment je peux utiliser ce truc ########
DB_DIALECTS = {
    "postgresql": "PostgreSQL — utiliser :: pour les casts, ILIKE pour les recherches insensibles à la casse.",
    "mysql":      "MySQL — utiliser BACKTICKS pour les noms réservés, LIMIT au lieu de FETCH FIRST.",
    "excel":      "DuckDB SQL sur fichier Excel — pas de schéma, une seule table disponible.",
    "csv":        "DuckDB SQL sur fichier CSV — pas de schéma, une seule table disponible.",
    "demo":       "Base de démonstration PostgreSQL.",
}
############################################################



def build_system_prompt(db_type: str, credentials: dict) -> str:
    """
    1. Instancie le générateur avec les credentials
    2. Génère ou charge le prompt depuis le fichier .txt existant
    3. Retourne le contenu du prompt
    """

    if db_type in ("postgresql", "mysql", "demo"):
        generator = SystemPromptGenerator(
            database_name=credentials["database"],
            user_name=credentials["user"],
            password=credentials["password"],
            host_name=credentials["host"],
            port=credentials["port"],
        )


        # ✅ Génération ou pas && chargement du prompt
        prompt_path = generator.generate_prompt_path()
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()