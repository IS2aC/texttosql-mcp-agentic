# connectors/mysql.py
import json
from decimal import Decimal
from datetime import date, datetime

import mysql.connector
from mysql.connector import Error as MySQLError
from loguru import logger

from .base import BaseConnector


class MySQLConnector(BaseConnector):

    def __init__(self, host: str, port: int = 3306, database: str = None,
                 user: str = None, password: str = None, **kwargs):
        self.config = {
            "host":     host,
            "port":     int(port),
            "database": database,
            "user":     user,
            "password": password,
        }

    # ===============================
    # Connexion
    # ===============================
    def _get_connection(self):
        return mysql.connector.connect(**self.config)

    def test_connection(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()  
            cursor.close()
            conn.close()
            logger.info(f"[MySQL] Connexion OK → {self.config['host']}:{self.config['port']}/{self.config['database']}")
            return True
        except MySQLError as e:
            logger.error(f"[MySQL] Échec connexion : {e}")
            raise ConnectionError(
                f"Impossible de se connecter à MySQL : {str(e).strip()}. "
                "Vérifier host, port, database, user et password."
            )

    # ===============================
    # Sérialisation des types MySQL
    # ===============================
    @staticmethod
    def _serialize(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        raise TypeError(f"Type non sérialisable : {type(obj)}")

    # ===============================
    # list_tables
    # ===============================
    def list_tables(self) -> list[str]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (self.config["database"],))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [row["table_name"] for row in rows]

        except MySQLError as e:
            logger.error(f"[MySQL] list_tables error : {e}")
            raise RuntimeError(f"Erreur MySQL : {str(e).strip()}")

    # ===============================
    # get_columns
    # ===============================
    def get_columns(self, table_name: str) -> list[dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    column_name    AS name,
                    data_type      AS type,
                    is_nullable    AS nullable,
                    column_default AS `default`
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name   = %s
                ORDER BY ordinal_position
            """, (self.config["database"], table_name))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [
                {
                    "name":     row["name"],
                    "type":     row["type"],
                    "nullable": row["nullable"] == "YES",
                    "default":  row["default"],
                }
                for row in rows
            ]

        except MySQLError as e:
            logger.error(f"[MySQL] get_columns error : {e}")
            raise RuntimeError(f"Erreur MySQL : {str(e).strip()}")

    # ===============================
    # execute_query
    # ===============================
    def execute_query(self, sql: str) -> list[dict]:
        sql = sql.replace("\\n", "\n").strip()
        logger.info(f"[MySQL] Exécution : {sql}")

        conn   = None
        cursor = None
        try:
            conn   = self._get_connection()
            cursor = conn.cursor(dictionary=True)
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

        except MySQLError as e:
            if conn:
                conn.rollback()
            logger.error(f"[MySQL] Erreur execute_query : {e}")
            raise RuntimeError(
                f"{str(e).strip()} | errno={getattr(e, 'errno', None)}"
            )

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"[MySQL] Erreur inattendue : {e}")
            raise

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            logger.debug("[MySQL] Connexion fermée.")

    # ===============================
    # get_primary_keys
    # ===============================
    def get_primary_keys(self, table_name: str) -> list[str]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema    = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema    = %s
                  AND tc.table_name      = %s
                ORDER BY kcu.ordinal_position
            """, (self.config["database"], table_name))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [row["column_name"] for row in rows]

        except MySQLError as e:
            logger.error(f"[MySQL] get_primary_keys error : {e}")
            raise RuntimeError(f"Erreur MySQL : {str(e).strip()}")

    # ===============================
    # get_foreign_keys
    # ===============================
    def get_foreign_keys(self, table_name: str) -> list[dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    kcu.column_name          AS `column`,
                    kcu.referenced_table_name  AS foreign_table,
                    kcu.referenced_column_name AS foreign_column
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema    = kcu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.table_schema   = %s
                  AND kcu.table_name     = %s
            """, (self.config["database"], table_name))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [dict(row) for row in rows]

        except MySQLError as e:
            logger.error(f"[MySQL] get_foreign_keys error : {e}")
            raise RuntimeError(f"Erreur MySQL : {str(e).strip()}")

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