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
    # Paths — SHA256 credentials
    # ===============================
    def _cache_key(self) -> str:
        raw = f"{self.host_name}:{self.port}:{self.database_name}:{self.user_name}:{self.password}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _base_dir(self) -> str:
        return os.path.join(os.path.dirname(__file__), "system_prompts")

    def generate_prompt_path(self) -> str:
        """Chemin du system prompt complet (cache principal)."""
        return os.path.join(self._base_dir(), f"{self._cache_key()}.txt")

    def _context_path(self) -> str:
        """Chemin du context_text brut (.ctx) — persisté pour les refresh futurs."""
        return os.path.join(self._base_dir(), f"{self._cache_key()}.ctx")

    # ===============================
    # Context text — lecture / écriture
    # ===============================
    def save_context_text(self, context_text: str) -> None:
        """Sauvegarde le context_text brut pour pouvoir le réutiliser au refresh."""
        if not context_text:
            return
        os.makedirs(self._base_dir(), exist_ok=True)
        with open(self._context_path(), "w", encoding="utf-8") as f:
            f.write(context_text)
        print(f"[cache] Context text sauvegardé → {self._context_path()}")

    def load_context_text(self) -> str:
        """Charge le context_text persisté. Retourne '' si absent."""
        ctx_path = self._context_path()
        if not os.path.exists(ctx_path):
            return ""
        with open(ctx_path, "r", encoding="utf-8") as f:
            return f.read()

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
TABLE FORMATTING — MANDATORY
---------------------------------------

If query_data returns MULTIPLE ROWS (2 or more) with MULTIPLE COLUMNS:
You MUST format the result as a Markdown table using | pipes |,
with a header row and a separator row (|---|---|...).

Example:
| Contract | Status | Premium |
|----------|--------|---------|
| CTR-001  | ACTIF  | 3,001   |
| CTR-002  | ACTIF  | 3,002   |

NEVER use numbered lists (1. 2. 3.) or bullet points (- field : value)
to present multiple records with the same fields.
Bullet points are reserved ONLY for a single record's details
or non-tabular summaries (e.g. lists of distinct table/column names).

---------------------------------------
TABLE DISCOVERY
---------------------------------------

If unsure about table names or columns:
Call list_tables or columns_of(table_name) before generating SQL.
"""

    # ===============================
    # Schéma technique
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
                   kcu.referenced_table_schema, kcu.referenced_table_name,
                   kcu.referenced_column_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
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

    def count_tables(self) -> int:
        """Retourne le nombre de tables — utile pour le feedback du refresh."""
        schema_str = self.column_data()
        return schema_str.count("**public.")

    # ===============================
    # Appel Groq — base de connaissance
    # ===============================
    def api_call(self, schema_info: str, context_text: str = "") -> str:
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
        os.makedirs(self._base_dir(), exist_ok=True)
        with open(self.generate_prompt_path(), "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"[cache] Prompt sauvegardé → {self.generate_prompt_path()}")

    # ===============================
    # Point d'entrée — construction
    # ===============================
    def construct_system_prompt(self, context_text: str = "") -> str:
        """
        Construit ou charge le system prompt.
        - Si context_text fourni → sauvegarde le .ctx + invalide le cache
        - Si pas de context_text → réutilise le .ctx existant si présent
        Retourne toujours le chemin du fichier cache.
        """
        prompt_path = self.generate_prompt_path()

        # Résolution du context_text :
        # 1. Priorité au context_text passé en paramètre (nouveau upload)
        # 2. Sinon, réutilise le .ctx persisté (refresh sans nouveau fichier)
        if context_text:
            self.save_context_text(context_text)
        else:
            context_text = self.load_context_text()

        # Invalider le cache si context_text fourni
        if context_text and os.path.exists(prompt_path):
            os.remove(prompt_path)
            print(f"[cache] Invalidé → {prompt_path}")

        if os.path.exists(prompt_path):
            print(f"[cache] Prompt existant chargé → {prompt_path}")
            return prompt_path

        # Génération complète
        print("[cache] Génération du prompt — récupération du schéma...")
        schema_info = self.column_data()

        print("[cache] Appel Groq...")
        if context_text:
            print("[cache] Context text transmis à Groq ✓")
        data_context = self.api_call(schema_info, context_text)

        prompt = self.generate_prompt(data_context, schema_info)
        self.save_system_prompt(prompt)

        return prompt_path

    # ===============================
    # Refresh — force la régénération
    # ===============================
    def refresh(self, new_context_text: str = "") -> tuple[str, int]:
        """
        Force la régénération complète du system prompt.
        - new_context_text : nouveau .txt uploadé (optionnel)
          Si absent, réutilise le .ctx persisté.
        Retourne (prompt_path, tables_count).
        """
        prompt_path = self.generate_prompt_path()

        # Résolution du context_text
        if new_context_text:
            self.save_context_text(new_context_text)
            context_text = new_context_text
            print(f"[refresh] Nouveau context text ({len(context_text)} chars) sauvegardé")
        else:
            context_text = self.load_context_text()
            if context_text:
                print(f"[refresh] Context text existant réutilisé ({len(context_text)} chars)")
            else:
                print("[refresh] Pas de context text — régénération schéma seul")

        # Suppression forcée du cache
        if os.path.exists(prompt_path):
            os.remove(prompt_path)
            print(f"[refresh] Cache supprimé → {prompt_path}")

        # Régénération
        print("[refresh] Récupération du schéma depuis la DB...")
        schema_info  = self.column_data()
        tables_count = schema_info.count("**public.")

        print(f"[refresh] {tables_count} tables détectées — appel Groq...")
        data_context = self.api_call(schema_info, context_text)

        prompt = self.generate_prompt(data_context, schema_info)
        self.save_system_prompt(prompt)

        print(f"[refresh] Terminé — {tables_count} tables")
        return prompt_path, tables_count