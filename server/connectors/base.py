# connectors/base.py
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    
    @abstractmethod
    def list_tables(self) -> list[str]:
        pass

    @abstractmethod
    def get_columns(self, table_name: str) -> list[dict]:
        pass

    @abstractmethod
    def execute_query(self, sql: str) -> list[dict]:
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        pass