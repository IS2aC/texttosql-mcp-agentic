# connectors/supabase.py
import json
from decimal import Decimal
from datetime import date, datetime

import psycopg2
import psycopg2.extras
from psycopg2 import OperationalError, ProgrammingError, DatabaseError
from loguru import logger

from .base import BaseConnector


class SupabaseConnector(BaseConnector):
    """
    Connecteur Supabase (PostgreSQL managé).

    SSL obligatoire. Supporte les deux pool modes Supabase :
      - session     : port=5432  — connexion persistante, supporte les prepared statements
      - transaction : port=6543  — connexion courte via pgBouncer, pas de prepared statements

    Credentials attendus (noms exacts des variables Supabase) :
        DB_HOST      / host      : str  — ex: db.<ref>.supabase.co
        DB_PORT      / port      : int  — 5432 (session) ou 6543 (transaction)
        DB_NAME      / database  : str  — "postgres"
        DB_USER      / user      : str  — "postgres" ou "postgres.<ref>" (pooler)
        DB_PASSWORD  / password  : str  — mot de passe DB (pas la clé anon/service_role)
        DB_POOL_MODE / pool_mode : str  — "session" (défaut) ou "transaction"
        DB_SSLMODE   / sslmode   : str  — "require" (défaut, ne pas changer)
    """

    # Pool mode → port par défaut si non fourni explicitement
    _POOL_MODE_PORTS = {
        "session":     5432,
        "transaction": 6543,
    }

    def __init__(
        self,
        host: str       = None,
        port: int       = None,
        database: str   = "postgres",
        user: str       = None,
        password: str   = None,
        pool_mode: str  = "session",
        sslmode: str    = "require",
        # aliases directs depuis les clés .env Supabase
        DB_HOST: str     = None,
        DB_PORT: int     = None,
        DB_NAME: str     = None,
        DB_USER: str     = None,
        DB_PASSWORD: str = None,
        DB_POOL_MODE: str = None,
        DB_SSLMODE: str  = None,
        **kwargs,
    ):
        # Les clés DB_* sont prioritaires si fournies (copier-coller direct du .env)
        resolved_host      = DB_HOST      or host
        resolved_database  = DB_NAME      or database
        resolved_user      = DB_USER      or user
        resolved_password  = DB_PASSWORD  or password
        resolved_pool_mode = (DB_POOL_MODE or pool_mode or "session").lower()
        resolved_sslmode   = DB_SSLMODE   or sslmode or "require"

        # Port : DB_PORT > port explicite > déduit du pool_mode
        if DB_PORT:
            resolved_port = int(DB_PORT)
        elif port:
            resolved_port = int(port)
        else:
            resolved_port = self._POOL_MODE_PORTS.get(resolved_pool_mode, 5432)

        self.pool_mode = resolved_pool_mode

        self.config = {
            "host":            resolved_host,
            "port":            resolved_port,
            "dbname":          resolved_database,
            "user":            resolved_user,
            "password":        resolved_password,
            "sslmode":         resolved_sslmode,
            "connect_timeout": 10,
        }

    # ===============================
    # Connexion
    # ===============================
    def _get_connection(self):
        return psycopg2.connect(**self.config)

    def test_connection(self) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            logger.info(
                f"[Supabase] Connexion OK → {self.config['host']}:{self.config['port']}"
                f"/{self.config['dbname']} (pool_mode={self.pool_mode})"
            )
            return True
        except OperationalError as e:
            logger.error(f"[Supabase] Échec connexion : {e}")
            raise ConnectionError(
                f"Impossible de se connecter à Supabase : {str(e).strip()}. "
                "Vérifier host, port, database, user, password et que SSL est activé."
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
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if isinstance(obj, memoryview):
            return obj.tobytes().decode("utf-8", errors="replace")
        raise TypeError(f"Type non sérialisable : {type(obj)}")

    # ===============================
    # list_tables
    # ===============================
    def list_tables(self) -> list[str]:
        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_schema NOT LIKE 'pg_toast%'
              AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
            return [row["table_name"] for row in rows]

        except (OperationalError, DatabaseError) as e:
            logger.error(f"[Supabase] list_tables error : {e}")
            raise RuntimeError(f"Erreur Supabase : {str(e).strip()}")

    # ===============================
    # get_columns
    # ===============================
    def get_columns(self, table_name: str) -> list[dict]:
        sql = """
            SELECT
                column_name    AS name,
                data_type      AS type,
                is_nullable    AS nullable,
                column_default AS default
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_name = %s
            ORDER BY ordinal_position
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (table_name,))
                    rows = cur.fetchall()
            return [
                {
                    "name":     row["name"],
                    "type":     row["type"],
                    "nullable": row["nullable"] == "YES",
                    "default":  row["default"],
                }
                for row in rows
            ]

        except (OperationalError, DatabaseError) as e:
            logger.error(f"[Supabase] get_columns error : {e}")
            raise RuntimeError(f"Erreur Supabase : {str(e).strip()}")

    # ===============================
    # execute_query
    # ===============================
    def execute_query(self, sql: str) -> list[dict]:
        sql = sql.replace("\\n", "\n").strip()
        logger.info(f"[Supabase] Exécution : {sql}")

        conn   = None
        cursor = None
        try:
            conn   = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)

            if cursor.description is not None:
                rows = cursor.fetchall()
                conn.commit()
                serialized = json.loads(
                    json.dumps([dict(row) for row in rows], default=self._serialize)
                )
                return serialized

            conn.commit()
            return []

        except ProgrammingError as e:
            if conn:
                conn.rollback()
            logger.error(f"[Supabase] Erreur SQL : {e}")
            raise RuntimeError(f"{str(e).strip()}")

        except DatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"[Supabase] Erreur base : {e}")
            raise RuntimeError(f"{str(e).strip()}")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"[Supabase] Erreur inattendue : {e}")
            raise

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            logger.debug("[Supabase] Connexion fermée.")

    # ===============================
    # get_primary_keys
    # ===============================
    def get_primary_keys(self, table_name: str) -> list[str]:
        sql = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema    = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (table_name,))
                    rows = cur.fetchall()
            return [row["column_name"] for row in rows]

        except (OperationalError, DatabaseError) as e:
            logger.error(f"[Supabase] get_primary_keys error : {e}")
            raise RuntimeError(f"Erreur Supabase : {str(e).strip()}")

    # ===============================
    # get_foreign_keys
    # ===============================
    def get_foreign_keys(self, table_name: str) -> list[dict]:
        sql = """
            SELECT
                kcu.column_name                AS column,
                ccu.table_name                 AS foreign_table,
                ccu.column_name                AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema    = kcu.table_schema
            JOIN information_schema.referential_constraints rc
              ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON rc.unique_constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
              AND tc.table_name = %s
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (table_name,))
                    rows = cur.fetchall()
            return [dict(row) for row in rows]

        except (OperationalError, DatabaseError) as e:
            logger.error(f"[Supabase] get_foreign_keys error : {e}")
            raise RuntimeError(f"Erreur Supabase : {str(e).strip()}")

    # ===============================
    # get_full_schema_with_relations
    # ===============================
    def get_full_schema_with_relations(self) -> dict:
        tables = self.list_tables()
        schema = {}
        for table in tables:
            schema[table] = {
                "columns":      self.get_columns(table),
                "primary_keys": self.get_primary_keys(table),
                "foreign_keys": self.get_foreign_keys(table),
            }
        return schema