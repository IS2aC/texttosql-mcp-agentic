# connectors/excel_csv.py
import pandas as pd
import duckdb
from .base import BaseConnector

class ExcelCSVConnector(BaseConnector):
    def __init__(self, file_path: str, **kwargs):
        self.file_path = file_path
        ext = file_path.split(".")[-1].lower()
        self.df = pd.read_excel(file_path) if ext in ["xlsx","xls"] else pd.read_csv(file_path)
        self.table_name = file_path.split("/")[-1].split(".")[0]

    def list_tables(self):
        return [self.table_name]

    def get_columns(self, table_name: str):
        return [{"name": c, "type": str(self.df[c].dtype), "nullable": True} 
                for c in self.df.columns]

    def execute_query(self, sql: str):
        # duckdb peut requêter un DataFrame directement
        locals()[self.table_name] = self.df
        result = duckdb.query(sql).df()
        return result.to_dict(orient="records")

    def test_connection(self):
        return len(self.df) >= 0