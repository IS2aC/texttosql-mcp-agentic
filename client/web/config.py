# client/web/config.py
# import os
# from dotenv import load_dotenv
# load_dotenv("/home/isaac/mcp-agentic-analytics/client/.env")

# class Config:
#     SECRET_KEY     = os.urandom(24)
#     OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL")
#     MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
#     MAX_TOOL_RETRIES = 3
#     DANGEROUS_TOOLS  = ["drop_table", "create_table", "create_user"]

#     DEMO_CREDENTIALS = {
#         "host":     os.getenv("DEMO_DB_HOST"),
#         "port":     int(os.getenv("DEMO_DB_PORT", 5432)),
#         "database": os.getenv("DEMO_DB_NAME"),
#         "user":     os.getenv("DEMO_DB_USER"),
#         "password": os.getenv("DEMO_DB_PASSWORD"),
#     }

#     DB_TYPES = {
#         "postgresql": "PostgreSQL",
#         "mysql":      "MySQL",
#         "excel":      "Excel",
#         "csv":        "CSV",
#         "demo":       "Demo",
#     }



################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################


# client/web/config.py
# import os
# from dotenv import load_dotenv

# load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# class Config:
#     SECRET_KEY       = os.getenv("SECRET_KEY", os.urandom(24).hex())
#     OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL")
#     MCP_SERVER_URL   = os.getenv("MCP_SERVER_URL")
#     MAX_TOOL_RETRIES = 3
#     DANGEROUS_TOOLS  = ["drop_table", "create_table", "create_user"]

#     DEMO_CREDENTIALS = {
#         "host":     os.getenv("DEMO_DB_HOST"),
#         "port":     int(os.getenv("DEMO_DB_PORT", 5432)),
#         "database": os.getenv("DEMO_DB_NAME"),
#         "user":     os.getenv("DEMO_DB_USER"),
#         "password": os.getenv("DEMO_DB_PASSWORD"),
#     }

#     DB_TYPES = {
#         "postgresql": "PostgreSQL",
#         "mysql":      "MySQL",
#         "excel":      "Excel",
#         "csv":        "CSV",
#         "supabase":   "Supabase",
#         "demo":       "Demo",
#     }


################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################

# client/web/config.py
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class Config:
    SECRET_KEY       = os.getenv("SECRET_KEY", os.urandom(24).hex())
    OLLAMA_HOST      = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL")
    MCP_SERVER_URL   = os.getenv("MCP_SERVER_URL")
    MAX_TOOL_RETRIES = 3
    DANGEROUS_TOOLS  = ["drop_table", "create_table", "create_user"]

    DEMO_CREDENTIALS = {
        "host":     os.getenv("DEMO_DB_HOST"),
        "port":     int(os.getenv("DEMO_DB_PORT", 5432)),
        "database": os.getenv("DEMO_DB_NAME"),
        "user":     os.getenv("DEMO_DB_USER"),
        "password": os.getenv("DEMO_DB_PASSWORD"),
    }

    DB_TYPES = {
        "postgresql": "PostgreSQL",
        "mysql":      "MySQL",
        "excel":      "Excel",
        "csv":        "CSV",
        "supabase":   "Supabase",
        "demo":       "Demo",
    }