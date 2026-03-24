# tools/query_tools.py
from session import get_connector
from loguru import logger
import json

# Opérations interdites — indépendant du connecteur
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", 
    "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"
]

def _is_query_safe(sql: str) -> tuple[bool, str | None]:
    """
    Vérifie que la requête est en lecture seule.
    Retourne (True, None) si safe, (False, motif) sinon.
    """
    sql_upper = sql.strip().upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if sql_upper.startswith(keyword):
            return False, keyword
    return True, None


def _format_results(rows: list[dict], max_rows: int = 500) -> str:
    """
    Formate les résultats pour le LLM.
    Tronque si trop de lignes pour ne pas saturer le contexte.
    """
    if not rows:
        return json.dumps({"status": "success", "message": "Requête exécutée, aucun résultat retourné.", "rows": []})

    truncated = False
    if len(rows) > max_rows:
        rows = rows[:max_rows]
        truncated = True

    result = json.dumps(rows, indent=2, default=str)

    if truncated:
        result += f"\n\n⚠️ Résultats tronqués à {max_rows} lignes. Affinez votre requête si nécessaire."

    return result


def get_query_tools(mcp):

    @mcp.tool(description=(
        "Exécute une requête SELECT sur la source de données de la session. "
        "Fonctionne pour PostgreSQL, MySQL, Excel et CSV. "
        "Toujours exécuter le SQL via cet outil, ne jamais l'afficher brut à l'utilisateur. "
        "Si une erreur est retournée, corriger le SQL et rappeler cet outil immédiatement. "
        "Utiliser list_tables et columns_of en amont si les noms de tables ou colonnes sont incertains."
    ))
    def query_data(session_id: str, sql_query: str) -> str:
        """
        Exécute un SELECT et retourne les résultats en JSON.
        Seules les requêtes en lecture sont autorisées.
        En cas d'erreur SQL, un objet JSON d'erreur est retourné avec un hint pour retry.
        """
        # Nettoyage
        sql_query = sql_query.replace("\\n", "\n").strip()

        # Garde-fou lecture seule
        safe, forbidden_kw = _is_query_safe(sql_query)
        if not safe:
            return json.dumps({
                "status": "error",
                "error": f"Opération interdite : {forbidden_kw}. Seules les requêtes SELECT sont autorisées.",
            }, indent=2)

        logger.info(f"[session={session_id}] Exécution SQL : {sql_query}")

        try:
            connector = get_connector(session_id)
            rows = connector.execute_query(sql_query)
            return _format_results(rows)

        except KeyError as e:
            # Session inconnue
            return json.dumps({
                "status": "error",
                "error": str(e),
                "hint": "La session est expirée ou invalide. Demander à l'utilisateur de re-soumettre ses credentials."
            }, indent=2)

        except Exception as e:
            logger.error(f"[session={session_id}] Erreur query : {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "hint": "Corriger le SQL et réessayer. Vérifier les noms de tables et colonnes avec columns_of."
            }, indent=2)

    @mcp.tool(description=(
        "Retourne un aperçu des premières lignes d'une table sans écrire de SQL. "
        "Utile pour explorer rapidement le contenu d'une table inconnue."
    ))
    def preview_table(session_id: str, table_name: str, limit: int = 10) -> str:
        """
        Génère et exécute automatiquement un SELECT * LIMIT sur la table demandée.
        """
        if limit > 100:
            limit = 100  # cap de sécurité

        sql = f'SELECT * FROM "{table_name}" LIMIT {limit}'
        logger.info(f"[session={session_id}] Preview table : {sql}")

        try:
            connector = get_connector(session_id)
            rows = connector.execute_query(sql)
            return _format_results(rows, max_rows=limit)

        except KeyError as e:
            return json.dumps({"status": "error", "error": str(e)})
        except Exception as e:
            logger.error(f"[session={session_id}] Erreur preview : {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "hint": f"Vérifier que la table '{table_name}' existe via list_tables."
            }, indent=2)