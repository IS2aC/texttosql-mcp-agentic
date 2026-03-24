
# system_prompt_generator.py
# import os
# from collections import defaultdict
# from groq import Groq
# from dotenv import load_dotenv

# load_dotenv("/home/isaac/mcp-agentic-analytics/client/.env")


# class SystemPromptGenerator:
#     def __init__(self, database_name, user_name, password, host_name, port,
#                  db_type="postgresql", sslmode=None):
#         self.database_name = database_name
#         self.user_name = user_name
#         self.password = password
#         self.host_name = host_name
#         self.port = port
#         self.db_type = db_type
#         # SSL : "require" par défaut pour Supabase, None pour les autres
#         self.sslmode = sslmode or ("require" if db_type == "supabase" else None)

#     # ===============================
#     # Path du prompt
#     # ===============================
#     def generate_prompt_path(self):
#         base_prompt_path = "/home/isaac/mcp-agentic-analytics/client/system_prompts/"
#         prompt_key = f"{self.database_name}-{self.user_name}-{self.password}-{self.host_name}-{self.port}.txt"
#         return base_prompt_path + prompt_key

#     # ===============================
#     # Génération du DEFAULT_PROMPT
#     # ===============================
#     def generate_prompt(self, DATABASE_CONTEXT, DATABASE_SCHEMA):
#         if self.db_type == "mysql":
#             date_functions = "- DATE_FORMAT()\n- YEAR() / MONTH() / DAY()\n- DATEDIFF()\n- NOW()"
#             db_label = "MySQL"
#         elif self.db_type == "supabase":
#             date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
#             db_label = "Supabase (PostgreSQL)"
#         else:
#             date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
#             db_label = "PostgreSQL"

#         DEFAULT_PROMPT = f"""
# ------------------------------
# VERY IMPORTANT :
# LANGUAGE RULE — ABSOLUTE PRIORITY:
# Always respond in the same language as the user's message.
# If the user writes in French -> respond in French.
# If the user writes in English -> respond in English.
# Never switch languages mid-response.
# ------------------------------

# You are a senior SQL analytics AI connected to a live {db_label} database via tools.

# You are schema-aware. You MUST strictly rely on the schema provided below.

# ---------------------------------------
# DATABASE CONTEXT
# ---------------------------------------
# {DATABASE_CONTEXT}

# ---------------------------------------
# DATABASE SCHEMA
# ---------------------------------------
# {DATABASE_SCHEMA}

# ---------------------------------------
# CRITICAL EXECUTION RULES
# ---------------------------------------

# RULE 1 — EXECUTE FIRST, EXPLAIN AFTER

# For ANY question involving:
# - data
# - metrics
# - trends
# - comparisons
# - aggregations
# - ranking
# - filtering
# - time analysis
# - percentages
# - growth
# - distributions

# You MUST:

# STEP 1 — Immediately call query_data with SQL
# STEP 2 — Read the result
# STEP 3 — Provide a concise explanation

# NEVER:
# - show SQL before executing
# - say "Here is the query"
# - narrate reasoning

# Correct flow:
# [tool call: query_data] → [result received] → final explanation

# ---------------------------------------
# RULE 2 — NEVER SHOW RAW SQL FIRST
# ---------------------------------------

# SQL must live inside tool calls only.
# If the user explicitly asks to see the query,
# you may show it AFTER execution.

# ---------------------------------------
# RULE 3 — STRICT SAFETY
# ---------------------------------------

# Only SELECT statements are allowed.

# Never generate:
# INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, GRANT

# ---------------------------------------
# SCHEMA INTELLIGENCE
# ---------------------------------------

# You must:
# - infer relationships from column names
# - detect foreign keys by *_id naming patterns
# - join tables when logically required
# - avoid Cartesian products
# - use explicit JOIN syntax

# ---------------------------------------
# ADVANCED ANALYTICS CAPABILITIES
# ---------------------------------------

# Use these techniques when appropriate:

# 1) JOINs — always explicit
# 2) CTE (WITH) — for multi-step logic
# 3) Window functions:
# - LAG()
# - LEAD()
# - SUM() OVER()
# - RANK()
# - DENSE_RANK()
# - ROW_NUMBER()
# 4) Subqueries — when filtering on aggregates
# 5) Date handling:
# {date_functions}
# 6) Safe percentage:
# ROUND(100.0 * (a - b) / NULLIF(b, 0), 2)

# ---------------------------------------
# ERROR SELF-CORRECTION
# ---------------------------------------

# If query_data returns error:
# 1. Read error carefully
# 2. Identify wrong column, alias, join or syntax
# 3. Fix it
# 4. Retry immediately (max 3 attempts)

# ---------------------------------------
# RESPONSE STYLE
# ---------------------------------------

# After result:

# - Start with the insight
# - Format numbers clearly:
# 1,234
# $12,500.00
# +8.2%
# - Mention peaks/trends when relevant
# - Keep concise
# - Do NOT repeat the question
# - Do NOT explain SQL logic

# ---------------------------------------
# TABLE DISCOVERY
# ---------------------------------------

# If unsure about table names or columns:
# Call:
# - list_tables
# - columns_of(table_name)

# Before generating SQL.
# """
#         return DEFAULT_PROMPT

#     # ===============================
#     # Récupération du schéma
#     # ===============================
#     def column_data(self):
#         if self.db_type == "mysql":
#             return self._column_data_mysql()
#         else:  # postgresql, supabase, demo → tous psycopg2
#             return self._column_data_postgresql()

#     def _column_data_postgresql(self):
#         import psycopg2

#         column_query = """
#             SELECT 
#                 c.table_schema, c.table_name, c.column_name,
#                 c.data_type, c.character_maximum_length,
#                 c.numeric_precision, c.numeric_scale, c.is_nullable
#             FROM information_schema.columns c
#             JOIN information_schema.tables t 
#                 ON c.table_schema = t.table_schema 
#                 AND c.table_name = t.table_name
#             WHERE t.table_type = 'BASE TABLE'
#                 AND c.table_schema = 'public'
#             ORDER BY c.table_name, c.ordinal_position;
#         """
#         fk_query = """
#             SELECT tc.table_schema, tc.table_name, kcu.column_name,
#                 ccu.table_schema AS foreign_table_schema,
#                 ccu.table_name AS foreign_table_name,
#                 ccu.column_name AS foreign_column_name
#             FROM information_schema.table_constraints AS tc
#             JOIN information_schema.key_column_usage AS kcu
#                 ON tc.constraint_name = kcu.constraint_name
#                 AND tc.table_schema = kcu.table_schema
#             JOIN information_schema.referential_constraints AS rc
#                 ON tc.constraint_name = rc.constraint_name
#             JOIN information_schema.constraint_column_usage AS ccu
#                 ON rc.unique_constraint_name = ccu.constraint_name
#             WHERE tc.constraint_type = 'FOREIGN KEY'
#                 AND tc.table_schema = 'public';
#         """

#         # Paramètres de connexion de base
#         connect_kwargs = dict(
#             dbname=self.database_name,
#             user=self.user_name,
#             password=self.password,
#             host=self.host_name,
#             port=self.port,
#         )
#         # SSL ajouté uniquement si nécessaire (Supabase l'exige)
#         if self.sslmode:
#             connect_kwargs["sslmode"] = self.sslmode

#         with psycopg2.connect(**connect_kwargs) as conn:
#             with conn.cursor() as cur:
#                 cur.execute(column_query)
#                 columns = cur.fetchall()
#                 cur.execute(fk_query)
#                 fks = cur.fetchall()

#         return self._build_schema(columns, fks)

#     def _column_data_mysql(self):
#         import mysql.connector

#         conn = mysql.connector.connect(
#             host=self.host_name,
#             port=int(self.port),
#             database=self.database_name,
#             user=self.user_name,
#             password=self.password,
#         )
#         cursor = conn.cursor()

#         cursor.execute("""
#             SELECT 
#                 c.table_schema, c.table_name, c.column_name,
#                 c.data_type, c.character_maximum_length,
#                 c.numeric_precision, c.numeric_scale, c.is_nullable
#             FROM information_schema.columns c
#             JOIN information_schema.tables t 
#                 ON c.table_schema = t.table_schema 
#                 AND c.table_name = t.table_name
#             WHERE t.table_type = 'BASE TABLE'
#                 AND c.table_schema = %s
#             ORDER BY c.table_schema, c.table_name, c.ordinal_position;
#         """, (self.database_name,))
#         columns = cursor.fetchall()

#         cursor.execute("""
#             SELECT 
#                 kcu.table_schema, kcu.table_name, kcu.column_name,
#                 kcu.referenced_table_schema,
#                 kcu.referenced_table_name,
#                 kcu.referenced_column_name
#             FROM information_schema.key_column_usage kcu
#             JOIN information_schema.table_constraints tc
#                 ON tc.constraint_name = kcu.constraint_name
#                 AND tc.table_schema = kcu.table_schema
#             WHERE tc.constraint_type = 'FOREIGN KEY'
#                 AND kcu.table_schema = %s;
#         """, (self.database_name,))
#         fks = cursor.fetchall()

#         cursor.close()
#         conn.close()

#         return self._build_schema(columns, fks)

#     # ===============================
#     # Construction commune du schéma
#     # ===============================
#     def _build_schema(self, columns, fks):
#         fk_map = {}
#         for row in fks:
#             table_schema, table_name, column_name, \
#             foreign_schema, foreign_table, foreign_column = row
#             if foreign_table:
#                 fk_map[(table_schema, table_name, column_name)] = \
#                     f"(FK → {foreign_schema}.{foreign_table}.{foreign_column})"

#         tables = defaultdict(list)
#         for row in columns:
#             table_schema, table_name, column_name, data_type, \
#             char_len, num_precision, num_scale, is_nullable = row

#             if data_type == "character varying" and char_len:
#                 formatted_type = f"varchar({char_len})"
#             elif data_type in ("numeric", "decimal") and num_precision:
#                 formatted_type = f"{data_type}({num_precision},{num_scale or 0})"
#             else:
#                 formatted_type = data_type

#             nullable = "" if is_nullable == "YES" else " NOT NULL"
#             column_def = f"{column_name} {formatted_type}{nullable}"

#             fk_info = fk_map.get((table_schema, table_name, column_name))
#             if fk_info:
#                 column_def += f" {fk_info}"

#             tables[(table_schema, table_name)].append(column_def)

#         result = "## Database Schema\n\n"
#         for (schema, table), cols in tables.items():
#             result += f"**{schema}.{table}**\n"
#             for col in cols:
#                 result += f"- {col}\n"
#             result += "\n"

#         return result

#     # ===============================
#     # Appel LLM pour le contexte
#     # ===============================
#     def api_call(self, data_schema):
#         client_groq = Groq(api_key=os.getenv("GROQ_API"))
#         LLM_GROQ = "llama-3.3-70b-versatile"

#         chat_completion = client_groq.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a helpful assistant that explains database architecture and business objectives."
#                 },
#                 {
#                     "role": "user",
#                     "content": f"Explain in 1 lines how this database works: {data_schema}",
#                 }
#             ],
#             model=LLM_GROQ
#         )
#         return chat_completion.choices[0].message.content

#     # ===============================
#     # Sauvegarde du prompt
#     # ===============================
#     def save_system_prompt(self, prompt):
#         prompt_path = self.generate_prompt_path()
#         os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
#         with open(prompt_path, "w") as f:
#             f.write(prompt)
#         print(f"Prompt saved to {prompt_path}")

#     # ===============================
#     # Point d'entrée principal
#     # ===============================
#     def construct_system_prompt(self):
#         if os.path.exists(self.generate_prompt_path()):
#             print("Prompt already exists. Loading from file.")
#             with open(self.generate_prompt_path(), "r") as f:
#                 prompt = f.read()
#             print(f"{prompt[:1000]}...")
#         else:
#             schema_info = self.column_data()
#             print("-" * 80)
#             print(schema_info)
#             print("-" * 80)
#             data_context = self.api_call(schema_info)
#             print("-" * 80)
#             print(data_context)
#             print("-" * 80)
#             prompt = self.generate_prompt(data_context, schema_info)
#             self.save_system_prompt(prompt)






#########################################################################################################
#########################################################################################################
#########################################################################################################
#########################################################################################################
#########################################################################################################


# system_prompt_generator.py
import os
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv

# Chemin relatif au fichier lui-même — fonctionne partout (local, Docker, etc.)
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))


class SystemPromptGenerator:
    def __init__(self, database_name, user_name, password, host_name, port,
                 db_type="postgresql", sslmode=None):
        self.database_name = database_name
        self.user_name = user_name
        self.password = password
        self.host_name = host_name
        self.port = port
        self.db_type = db_type
        self.sslmode = sslmode or ("require" if db_type == "supabase" else None)

    # ===============================
    # Path du prompt
    # ===============================
    def generate_prompt_path(self):
        base_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompts")
        prompt_key = f"{self.database_name}-{self.user_name}-{self.password}-{self.host_name}-{self.port}.txt"
        return os.path.join(base_prompt_path, prompt_key)

    # ===============================
    # Génération du DEFAULT_PROMPT
    # ===============================
    def generate_prompt(self, DATABASE_CONTEXT, DATABASE_SCHEMA):
        if self.db_type == "mysql":
            date_functions = "- DATE_FORMAT()\n- YEAR() / MONTH() / DAY()\n- DATEDIFF()\n- NOW()"
            db_label = "MySQL"
        elif self.db_type == "supabase":
            date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
            db_label = "Supabase (PostgreSQL)"
        else:
            date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
            db_label = "PostgreSQL"

        DEFAULT_PROMPT = f"""
------------------------------
VERY IMPORTANT :
LANGUAGE RULE — ABSOLUTE PRIORITY:
Always respond in the same language as the user's message.
If the user writes in French -> respond in French.
If the user writes in English -> respond in English.
Never switch languages mid-response.
------------------------------

You are a senior SQL analytics AI connected to a live {db_label} database via tools.

You are schema-aware. You MUST strictly rely on the schema provided below.

---------------------------------------
DATABASE CONTEXT
---------------------------------------
{DATABASE_CONTEXT}

---------------------------------------
DATABASE SCHEMA
---------------------------------------
{DATABASE_SCHEMA}

---------------------------------------
CRITICAL EXECUTION RULES
---------------------------------------

RULE 1 — EXECUTE FIRST, EXPLAIN AFTER

For ANY question involving:
- data
- metrics
- trends
- comparisons
- aggregations
- ranking
- filtering
- time analysis
- percentages
- growth
- distributions

You MUST:

STEP 1 — Immediately call query_data with SQL
STEP 2 — Read the result
STEP 3 — Provide a concise explanation

NEVER:
- show SQL before executing
- say "Here is the query"
- narrate reasoning

Correct flow:
[tool call: query_data] → [result received] → final explanation

---------------------------------------
RULE 2 — NEVER SHOW RAW SQL FIRST
---------------------------------------

SQL must live inside tool calls only.
If the user explicitly asks to see the query,
you may show it AFTER execution.

---------------------------------------
RULE 3 — STRICT SAFETY
---------------------------------------

Only SELECT statements are allowed.

Never generate:
INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, GRANT

---------------------------------------
SCHEMA INTELLIGENCE
---------------------------------------

You must:
- infer relationships from column names
- detect foreign keys by *_id naming patterns
- join tables when logically required
- avoid Cartesian products
- use explicit JOIN syntax

---------------------------------------
ADVANCED ANALYTICS CAPABILITIES
---------------------------------------

Use these techniques when appropriate:

1) JOINs — always explicit
2) CTE (WITH) — for multi-step logic
3) Window functions:
- LAG()
- LEAD()
- SUM() OVER()
- RANK()
- DENSE_RANK()
- ROW_NUMBER()
4) Subqueries — when filtering on aggregates
5) Date handling:
{date_functions}
6) Safe percentage:
ROUND(100.0 * (a - b) / NULLIF(b, 0), 2)

---------------------------------------
ERROR SELF-CORRECTION
---------------------------------------

If query_data returns error:
1. Read error carefully
2. Identify wrong column, alias, join or syntax
3. Fix it
4. Retry immediately (max 3 attempts)

---------------------------------------
RESPONSE STYLE
---------------------------------------

After result:

- Start with the insight
- Format numbers clearly:
1,234
$12,500.00
+8.2%
- Mention peaks/trends when relevant
- Keep concise
- Do NOT repeat the question
- Do NOT explain SQL logic

---------------------------------------
TABLE DISCOVERY
---------------------------------------

If unsure about table names or columns:
Call:
- list_tables
- columns_of(table_name)

Before generating SQL.
"""
        return DEFAULT_PROMPT

    # ===============================
    # Récupération du schéma
    # ===============================
    def column_data(self):
        if self.db_type == "mysql":
            return self._column_data_mysql()
        else:  # postgresql, supabase, demo → tous psycopg2
            return self._column_data_postgresql()

    def _column_data_postgresql(self):
        import psycopg2

        column_query = """
            SELECT 
                c.table_schema, c.table_name, c.column_name,
                c.data_type, c.character_maximum_length,
                c.numeric_precision, c.numeric_scale, c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t 
                ON c.table_schema = t.table_schema 
                AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE'
                AND c.table_schema = 'public'
            ORDER BY c.table_name, c.ordinal_position;
        """
        fk_query = """
            SELECT tc.table_schema, tc.table_name, kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON rc.unique_constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public';
        """

        connect_kwargs = dict(
            dbname=self.database_name,
            user=self.user_name,
            password=self.password,
            host=self.host_name,
            port=self.port,
        )
        if self.sslmode:
            connect_kwargs["sslmode"] = self.sslmode

        with psycopg2.connect(**connect_kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute(column_query)
                columns = cur.fetchall()
                cur.execute(fk_query)
                fks = cur.fetchall()

        return self._build_schema(columns, fks)

    def _column_data_mysql(self):
        import mysql.connector

        conn = mysql.connector.connect(
            host=self.host_name,
            port=int(self.port),
            database=self.database_name,
            user=self.user_name,
            password=self.password,
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                c.table_schema, c.table_name, c.column_name,
                c.data_type, c.character_maximum_length,
                c.numeric_precision, c.numeric_scale, c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t 
                ON c.table_schema = t.table_schema 
                AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE'
                AND c.table_schema = %s
            ORDER BY c.table_schema, c.table_name, c.ordinal_position;
        """, (self.database_name,))
        columns = cursor.fetchall()

        cursor.execute("""
            SELECT 
                kcu.table_schema, kcu.table_name, kcu.column_name,
                kcu.referenced_table_schema,
                kcu.referenced_table_name,
                kcu.referenced_column_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND kcu.table_schema = %s;
        """, (self.database_name,))
        fks = cursor.fetchall()

        cursor.close()
        conn.close()

        return self._build_schema(columns, fks)

    # ===============================
    # Construction commune du schéma
    # ===============================
    def _build_schema(self, columns, fks):
        fk_map = {}
        for row in fks:
            table_schema, table_name, column_name, \
            foreign_schema, foreign_table, foreign_column = row
            if foreign_table:
                fk_map[(table_schema, table_name, column_name)] = \
                    f"(FK → {foreign_schema}.{foreign_table}.{foreign_column})"

        tables = defaultdict(list)
        for row in columns:
            table_schema, table_name, column_name, data_type, \
            char_len, num_precision, num_scale, is_nullable = row

            if data_type == "character varying" and char_len:
                formatted_type = f"varchar({char_len})"
            elif data_type in ("numeric", "decimal") and num_precision:
                formatted_type = f"{data_type}({num_precision},{num_scale or 0})"
            else:
                formatted_type = data_type

            nullable = "" if is_nullable == "YES" else " NOT NULL"
            column_def = f"{column_name} {formatted_type}{nullable}"

            fk_info = fk_map.get((table_schema, table_name, column_name))
            if fk_info:
                column_def += f" {fk_info}"

            tables[(table_schema, table_name)].append(column_def)

        result = "## Database Schema\n\n"
        for (schema, table), cols in tables.items():
            result += f"**{schema}.{table}**\n"
            for col in cols:
                result += f"- {col}\n"
            result += "\n"

        return result

    # ===============================
    # Appel LLM pour le contexte
    # ===============================
    def api_call(self, data_schema):
        client_groq = Groq(api_key=os.getenv("GROQ_API"))
        LLM_GROQ = "llama-3.3-70b-versatile"

        chat_completion = client_groq.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that explains database architecture and business objectives."
                },
                {
                    "role": "user",
                    "content": f"Explain in 1 lines how this database works: {data_schema}",
                }
            ],
            model=LLM_GROQ
        )
        return chat_completion.choices[0].message.content

    # ===============================
    # Sauvegarde du prompt
    # ===============================
    def save_system_prompt(self, prompt):
        prompt_path = self.generate_prompt_path()
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, "w") as f:
            f.write(prompt)
        print(f"Prompt saved to {prompt_path}")

    # ===============================
    # Point d'entrée principal
    # ===============================
    def construct_system_prompt(self):
        if os.path.exists(self.generate_prompt_path()):
            print("Prompt already exists. Loading from file.")
            with open(self.generate_prompt_path(), "r") as f:
                prompt = f.read()
            print(f"{prompt[:1000]}...")
        else:
            schema_info = self.column_data()
            print("-" * 80)
            print(schema_info)
            print("-" * 80)
            data_context = self.api_call(schema_info)
            print("-" * 80)
            print(data_context)
            print("-" * 80)
            prompt = self.generate_prompt(data_context, schema_info)
            self.save_system_prompt(prompt)