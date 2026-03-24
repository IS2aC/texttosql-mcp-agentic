# session.py
from connectors.base import BaseConnector
from connectors.postgresql import PostgreSQLConnector
from connectors.excel_csv import ExcelCSVConnector
from connectors.mysql import MySQLConnector
from connectors.supabase import SupabaseConnector

CONNECTOR_MAP = {
    "postgresql": PostgreSQLConnector,
    "mysql": MySQLConnector,
    "excel": ExcelCSVConnector,
    "csv": ExcelCSVConnector,
    "demo": PostgreSQLConnector,
    "supabase": SupabaseConnector
}


_sessions: dict[str, BaseConnector] = {}

def register_session(session_id: str, db_type: str, credentials: dict) -> str:
    connector_class = CONNECTOR_MAP.get(db_type.lower())
    if not connector_class:
        raise ValueError(f"Type non supporté : {db_type}")
    
    connector = connector_class(**credentials)
    connector.test_connection()  # fail fast
    _sessions[session_id] = connector
    return f"Session {session_id} enregistrée ({db_type})"

def get_connector(session_id: str) -> BaseConnector:
    connector = _sessions.get(session_id)
    if not connector:
        raise KeyError(f"Session inconnue : {session_id}. Re-soumettez vos credentials.")
    return connector

def close_session(session_id: str):
    _sessions.pop(session_id, None)