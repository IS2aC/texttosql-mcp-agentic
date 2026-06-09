# system_prompt_generator.py
import os
import hashlib
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))


class SystemPromptGenerator:
    def __init__(self, database_name, user_name, password, host_name, port,
                 db_type="postgresql", sslmode=None):
        self.database_name = database_name
        self.user_name     = user_name
        self.password      = password
        self.host_name     = host_name
        self.port          = port
        self.db_type       = db_type
        self.sslmode       = sslmode or ("require" if db_type == "supabase" else None)

    # ===============================
    # Path du cache — SHA256 credentials
    # ===============================
    def generate_prompt_path(self) -> str:
        """
        Clé = SHA256(host:port:database:user:password)
        Stable pour une même DB, indépendant du contexte métier.
        """
        base = os.path.join(os.path.dirname(__file__), "system_prompts")
        raw  = f"{self.host_name}:{self.port}:{self.database_name}:{self.user_name}:{self.password}"
        key  = hashlib.sha256(raw.encode()).hexdigest()
        return os.path.join(base, f"{key}.txt")

    # ===============================
    # Génération du prompt final
    # ===============================
    def generate_prompt(self, DATABASE_CONTEXT: str, DATABASE_SCHEMA: str) -> str:
        if self.db_type == "mysql":
            date_functions = "- DATE_FORMAT()\n- YEAR() / MONTH() / DAY()\n- DATEDIFF()\n- NOW()"
            db_label = "MySQL"
        elif self.db_type == "supabase":
            date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
            db_label = "Supabase (PostgreSQL)"
        else:
            date_functions = "- DATE_TRUNC()\n- EXTRACT()\n- TO_CHAR()"
            db_label = "PostgreSQL"

        return f"""
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
DATABASE CONTEXT & BUSINESS KNOWLEDGE
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

For ANY question involving data, metrics, trends, comparisons,
aggregations, ranking, filtering, time analysis, percentages,
growth, or distributions:

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
Never generate: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, GRANT

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

1) JOINs — always explicit
2) CTE (WITH) — for multi-step logic
3) Window functions: LAG(), LEAD(), SUM() OVER(), RANK(), DENSE_RANK(), ROW_NUMBER()
4) Subqueries — when filtering on aggregates
5) Date handling:
{date_functions}
6) Safe percentage: ROUND(100.0 * (a - b) / NULLIF(b, 0), 2)

---------------------------------------
ERROR SELF-CORRECTION
---------------------------------------

If query_data returns error:
1. Read error carefully
2. Identify wrong column, alias, join or syntax
3. Fix it
4. Retry immediately (max 3 attempts)

---------------------------------------
POSTGRESQL WINDOW FUNCTION RULES
---------------------------------------

- Never nest window functions.
- Never place a window function inside another window function.
- Never use window functions inside aggregate functions.
- If multiple window operations needed → use a CTE to separate steps.
- Always compute aggregations first, then apply window functions in outer SELECT.

---------------------------------------
RESPONSE STYLE
---------------------------------------

After result:
- Start with the insight
- Format numbers clearly: 1,234 / $12,500.00 / +8.2%
- Mention peaks/trends when relevant
- Keep concise
- Do NOT repeat the question
- Do NOT explain SQL logic

---------------------------------------
TABLE DISCOVERY
---------------------------------------

If unsure about table names or columns:
Call list_tables or columns_of(table_name) before generating SQL.
"""

    # ===============================
    # Récupération du schéma technique
    # ===============================
    def column_data(self) -> str:
        if self.db_type == "mysql":
            return self._column_data_mysql()
        return self._column_data_postgresql()

    def _column_data_postgresql(self) -> str:
        import psycopg2

        column_query = """
            SELECT c.table_schema, c.table_name, c.column_name,
                   c.data_type, c.character_maximum_length,
                   c.numeric_precision, c.numeric_scale, c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t
                ON c.table_schema = t.table_schema AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE' AND c.table_schema = 'public'
            ORDER BY c.table_name, c.ordinal_position;
        """
        fk_query = """
            SELECT tc.table_schema, tc.table_name, kcu.column_name,
                   ccu.table_schema, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON rc.unique_constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
        """
        kw = dict(dbname=self.database_name, user=self.user_name,
                  password=self.password, host=self.host_name, port=self.port)
        if self.sslmode:
            kw["sslmode"] = self.sslmode

        with psycopg2.connect(**kw) as conn:
            with conn.cursor() as cur:
                cur.execute(column_query); columns = cur.fetchall()
                cur.execute(fk_query);    fks     = cur.fetchall()
        return self._build_schema(columns, fks)

    def _column_data_mysql(self) -> str:
        import mysql.connector
        conn   = mysql.connector.connect(host=self.host_name, port=int(self.port),
                                         database=self.database_name,
                                         user=self.user_name, password=self.password)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.table_schema, c.table_name, c.column_name,
                   c.data_type, c.character_maximum_length,
                   c.numeric_precision, c.numeric_scale, c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t
                ON c.table_schema = t.table_schema AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE' AND c.table_schema = %s
            ORDER BY c.table_schema, c.table_name, c.ordinal_position;
        """, (self.database_name,))
        columns = cursor.fetchall()
        cursor.execute("""
            SELECT kcu.table_schema, kcu.table_name, kcu.column_name,
                   kcu.referenced_table_schema, kcu.referenced_table_name, kcu.referenced_column_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND kcu.table_schema = %s;
        """, (self.database_name,))
        fks = cursor.fetchall()
        cursor.close(); conn.close()
        return self._build_schema(columns, fks)

    def _build_schema(self, columns, fks) -> str:
        fk_map = {}
        for row in fks:
            ts, tn, cn, fs, ft, fc = row
            if ft:
                fk_map[(ts, tn, cn)] = f"(FK → {fs}.{ft}.{fc})"

        tables = defaultdict(list)
        for row in columns:
            ts, tn, cn, dt, cl, np, ns, nullable = row
            if dt == "character varying" and cl:
                fmt = f"varchar({cl})"
            elif dt in ("numeric", "decimal") and np:
                fmt = f"{dt}({np},{ns or 0})"
            else:
                fmt = dt
            null_str = "" if nullable == "YES" else " NOT NULL"
            col_def  = f"{cn} {fmt}{null_str}"
            fk_info  = fk_map.get((ts, tn, cn))
            if fk_info:
                col_def += f" {fk_info}"
            tables[(ts, tn)].append(col_def)

        result = "## Database Schema\n\n"
        for (schema, table), cols in tables.items():
            result += f"**{schema}.{table}**\n"
            for col in cols:
                result += f"- {col}\n"
            result += "\n"
        return result

    # ===============================
    # Appel Groq — génération base de connaissance
    # ===============================
    def api_call(self, schema_info: str, context_text: str = "") -> str:
        """
        Groq reçoit le schéma technique + les règles métier (si fournies)
        et génère une base de connaissance enrichie pour le system prompt.
        """
        client_groq = Groq(api_key=os.getenv("GROQ_API"))

        user_content = f"Here is the technical schema of the database:\n\n{schema_info}"

        if context_text:
            user_content += (
                f"\n\nHere are the business rules and domain knowledge provided "
                f"by the database owner:\n\n{context_text}"
                f"\n\nBased on the schema AND the business rules above, generate a comprehensive "
                f"business knowledge base for this database. Include: "
                f"table purposes, column meanings, value encodings, normalization rules "
                f"(e.g. always use UPPER() for status fields), join strategies, "
                f"and any domain-specific logic the SQL agent must know to answer "
                f"analytics questions correctly. Be precise and exhaustive."
            )
        else:
            user_content += (
                "\n\nBased on the schema above, explain in 2-3 sentences "
                "how this database works and what it manages."
            )

        chat_completion = client_groq.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert data architect and business analyst. "
                        "Your role is to produce precise, structured knowledge bases "
                        "that help SQL agents query databases correctly."
                    )
                },
                {"role": "user", "content": user_content}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=2500,
        )
        return chat_completion.choices[0].message.content

    # ===============================
    # Sauvegarde
    # ===============================
    def save_system_prompt(self, prompt: str) -> None:
        prompt_path = self.generate_prompt_path()
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Prompt saved → {prompt_path}")

    # ===============================
    # Point d'entrée principal
    # ===============================
    def construct_system_prompt(self, context_text: str = "") -> str:
        """
        Construit ou recharge le system prompt depuis le cache.

        - Sans context_text : charge le cache si existant, sinon génère.
        - Avec context_text : invalide le cache existant et régénère
          en passant les règles métier à Groq pour enrichir la base
          de connaissance → sauvegardé dans le cache.

        Retourne toujours le chemin du fichier cache.
        """
        prompt_path = self.generate_prompt_path()

        # Invalider le cache si un contexte métier est fourni
        if context_text and os.path.exists(prompt_path):
            os.remove(prompt_path)
            print(f"[cache] Invalidé (contexte métier fourni) → {prompt_path}")

        if os.path.exists(prompt_path):
            print(f"[cache] Prompt existant chargé → {prompt_path}")
            return prompt_path

        # Génération complète
        print("[cache] Nouveau prompt — récupération du schéma...")
        schema_info = self.column_data()
        print("-" * 60)
        print(schema_info)
        print("-" * 60)

        print("[cache] Appel Groq — génération base de connaissance...")
        if context_text:
            print("[cache] Contexte métier transmis à Groq ✓")
        data_context = self.api_call(schema_info, context_text)
        print("-" * 60)
        print(data_context)
        print("-" * 60)

        prompt = self.generate_prompt(data_context, schema_info)
        self.save_system_prompt(prompt)

        return prompt_path