# connectors/postgresql.py
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from datetime import date, datetime
from loguru import logger
from .base import BaseConnector


class PostgreSQLConnector(BaseConnector):

    def __init__(self, host: str, port: int = 5432, database: str = None,
                 user: str = None, password: str = None, **kwargs):
        self.config = {
            "host": host,
            "port": int(port),
            "database": database,
            "user": user,
            "password": password,
        }

    # ===============================
    # Connexion
    # ===============================
    def _get_connection(self):
        return psycopg2.connect(**self.config)

    def test_connection(self) -> bool:
        """
        Vérifie que les credentials sont valides.
        Appelé au moment du register_session — fail fast.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            logger.info(f"[PostgreSQL] Connexion OK → {self.config['host']}:{self.config['port']}/{self.config['database']}")
            return True
        except psycopg2.OperationalError as e:
            logger.error(f"[PostgreSQL] Échec connexion : {e}")
            raise ConnectionError(
                f"Impossible de se connecter à PostgreSQL : {str(e).strip()}. "
                "Vérifier host, port, database, user et password."
            )

    # ===============================
    # Sérialisation des types PG
    # ===============================
    @staticmethod
    def _serialize(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type non sérialisable : {type(obj)}")

    # ===============================
    # list_tables
    # ===============================
    def list_tables(self) -> list[str]:
        """
        Liste toutes les tables du schéma public.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    rows = cursor.fetchall()
            return [row["table_name"] for row in rows]

        except psycopg2.Error as e:
            logger.error(f"[PostgreSQL] list_tables error : {e}")
            raise RuntimeError(f"Erreur PostgreSQL : {str(e).strip()}")

    # ===============================
    # get_columns
    # ===============================
    def get_columns(self, table_name: str) -> list[dict]:
        """
        Retourne les colonnes d'une table :
        name, type, nullable, default.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT
                            column_name   AS name,
                            data_type     AS type,
                            is_nullable   AS nullable,
                            column_default AS default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    rows = cursor.fetchall()

            return [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "nullable": row["nullable"] == "YES",
                    "default": row["default"],
                }
                for row in rows
            ]

        except psycopg2.Error as e:
            logger.error(f"[PostgreSQL] get_columns error : {e}")
            raise RuntimeError(f"Erreur PostgreSQL : {str(e).strip()}")

    # ===============================
    # execute_query
    # ===============================
    def execute_query(self, sql: str) -> list[dict]:
        """
        Exécute un SELECT et retourne les résultats sous forme
        de liste de dicts sérialisables.
        La vérification read-only est déjà faite dans query_tools.
        """
        sql = sql.replace("\\n", "\n").strip()
        logger.info(f"[PostgreSQL] Exécution : {sql}")

        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql)

            if cursor.description is not None:
                rows = cursor.fetchall()
                conn.commit()
                import json
                # On passe par JSON pour normaliser les types PG
                serialized = json.loads(
                    json.dumps([dict(row) for row in rows], default=self._serialize)
                )
                return serialized

            conn.commit()
            return []

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"[PostgreSQL] Erreur execute_query : {e}")
            raise RuntimeError(
                f"{str(e).strip()} | pgcode={getattr(e, 'pgcode', None)}"
            )

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"[PostgreSQL] Erreur inattendue : {e}")
            raise

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            logger.debug("[PostgreSQL] Connexion fermée.")

    # ===============================
    # Utilitaires avancés (optionnels)
    # ===============================
    def get_primary_keys(self, table_name: str) -> list[str]:
        """
        Retourne les colonnes qui sont clés primaires d'une table.
        Utile pour enrichir le contexte du LLM.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_schema = 'public'
                          AND tc.table_name = %s
                        ORDER BY kcu.ordinal_position
                    """, (table_name,))
                    rows = cursor.fetchall()
            return [row["column_name"] for row in rows]

        except psycopg2.Error as e:
            logger.error(f"[PostgreSQL] get_primary_keys error : {e}")
            raise RuntimeError(f"Erreur PostgreSQL : {str(e).strip()}")

    def get_foreign_keys(self, table_name: str) -> list[dict]:
        """
        Retourne les foreign keys d'une table.
        Très utile pour que le LLM comprenne les relations
        et génère des JOIN corrects automatiquement.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT
                            kcu.column_name          AS column,
                            ccu.table_name           AS foreign_table,
                            ccu.column_name          AS foreign_column
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage ccu
                          ON ccu.constraint_name = tc.constraint_name
                         AND ccu.table_schema = tc.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_schema = 'public'
                          AND tc.table_name = %s
                    """, (table_name,))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except psycopg2.Error as e:
            logger.error(f"[PostgreSQL] get_foreign_keys error : {e}")
            raise RuntimeError(f"Erreur PostgreSQL : {str(e).strip()}")

    def get_full_schema_with_relations(self) -> dict:
        """
        Retourne le schéma complet avec colonnes, PK et FK.
        Idéal pour construire un sys prompt très riche
        qui permet au LLM de générer des JOIN sans se tromper.

        Format retourné :
        {
            "table_name": {
                "columns": [...],
                "primary_keys": [...],
                "foreign_keys": [...]
            },
            ...
        }
        """
        tables = self.list_tables()
        schema = {}
        for table in tables:
            schema[table] = {
                "columns": self.get_columns(table),
                "primary_keys": self.get_primary_keys(table),
                "foreign_keys": self.get_foreign_keys(table),
            }
        return schema