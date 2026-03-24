# tools/schema_tools.py
from session import get_connector
import json

def get_schema_tools(mcp):

    @mcp.tool(description=(
        "Liste toutes les tables disponibles dans la source de données de la session. "
        "Appeler cet outil en premier si l'utilisateur ne précise pas de table."
    ))
    def list_tables(session_id: str) -> str:
        try:
            connector = get_connector(session_id)
            tables = connector.list_tables()

            if not tables:
                return "Aucune table trouvée pour cette source de données."

            result = "📊 Tables disponibles :\n\n"
            result += "\n".join(f"• {t}" for t in tables)
            return result

        except KeyError as e:
            return json.dumps({"status": "error", "error": str(e)})
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(description=(
        "Inspecte les colonnes d'une table donnée : nom, type, nullable, valeur par défaut. "
        "Toujours appeler cet outil avant d'écrire une requête si les colonnes sont inconnues. "
        "Ne jamais deviner un nom de colonne."
    ))
    def columns_of(session_id: str, table_name: str) -> str:
        try:
            connector = get_connector(session_id)
            columns = connector.get_columns(table_name)

            if not columns:
                return f"Aucune colonne trouvée pour la table '{table_name}' (ou table inexistante)."

            result = f"📋 Colonnes de **{table_name}** :\n\n"
            for col in columns:
                nullable = "NULL" if col.get("nullable") else "NOT NULL"
                default = f" DEFAULT {col['default']}" if col.get("default") else ""
                result += f"• {col['name']} — {col['type']} {nullable}{default}\n"
            return result

        except KeyError as e:
            return json.dumps({"status": "error", "error": str(e)})
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(description=(
        "Retourne le schéma complet de toutes les tables de la session en une seule fois. "
        "Utiliser cet outil pour construire un contexte riche dans le sys prompt "
        "ou quand l'utilisateur pose une question sur plusieurs tables à la fois."
    ))
    def full_schema(session_id: str) -> str:
        """
        Retourne le schéma complet : toutes les tables + toutes leurs colonnes.
        Utile pour l'injection dans le sys prompt dynamique.
        """
        try:
            connector = get_connector(session_id)
            tables = connector.list_tables()

            if not tables:
                return "Aucune table trouvée."

            schema = {}
            for table in tables:
                columns = connector.get_columns(table)
                schema[table] = [
                    {
                        "name": col["name"],
                        "type": col["type"],
                        "nullable": col.get("nullable", True),
                        "default": col.get("default", None),
                    }
                    for col in columns
                ]

            # Format lisible pour le LLM
            result = "🗂️ Schéma complet :\n\n"
            for table_name, cols in schema.items():
                result += f"### {table_name}\n"
                for col in cols:
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    default = f" DEFAULT {col['default']}" if col["default"] else ""
                    result += f"  • {col['name']} — {col['type']} {nullable}{default}\n"
                result += "\n"

            return result

        except KeyError as e:
            return json.dumps({"status": "error", "error": str(e)})
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})