import psycopg2
import requests, json, os
from collections import defaultdict
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
load_dotenv(".env")



class SystemPromptGenerator:
    def __init__(self, database_name, user_name, password, host_name, port):
        self.database_name = database_name
        self.user_name = user_name
        self.password = password
        self.host_name = host_name
        self.port = port

    def generate_prompt_path(self):
        base_prompt_path = "/home/isaac/mcp-agentic-analytics/client/system_prompts/"
        prompt_key = f"{self.database_name}-{self.user_name}-{self.password}-{self.host_name}-{self.port}.txt"
        return base_prompt_path + prompt_key


    def generate_prompt(self, DATABASE_CONTEXT, DATABASE_SCHEMA):

        DEFAULT_PROMPT  =  f"""
------------------------------
VERY IMPORTANT :
LANGUAGE RULE — ABSOLUTE PRIORITY:
Always respond in the same language as the user's message.
If the user writes in French -> respond in French.
If the user writes in English -> respond in English.
Never switch languages mid-response.
------------------------------

You are a senior SQL analytics AI connected to a live PostgreSQL database via tools.

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
- say “Here is the query”
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
- DATE_TRUNC()
- EXTRACT()
- TO_CHAR()
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
POSTGRESQL WINDOW FUNCTION RULES
---------------------------------------

- Never nest window functions.
- Never place a window function inside another window function.
- Never use window functions inside aggregate functions.
- If multiple window operations are needed:
    → Use a CTE to separate steps.
- Always compute aggregations first,
  then apply window functions in an outer SELECT.

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

    
    def column_data(self):

        column_query = """
            SELECT 
                c.table_schema,
                c.table_name,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t 
                ON c.table_schema = t.table_schema 
                AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE'
                AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
                AND c.table_schema NOT LIKE 'pg_toast%'
            ORDER BY 
                c.table_schema,
                c.table_name,
                c.ordinal_position;
        """

        fk_query = """
            SELECT
                tc.table_schema,
                tc.table_name,
                kcu.column_name,
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
            WHERE tc.constraint_type = 'FOREIGN KEY';
        """

        with psycopg2.connect(
            dbname=self.database_name,
            user=self.user_name,
            password=self.password,
            host=self.host_name,
            port=self.port
        ) as conn:
            
            with conn.cursor() as cur:
                # =========================
                # Colonnes
                # =========================
                cur.execute(column_query)
                columns = cur.fetchall()

                # =========================
                # Foreign keys
                # =========================
                cur.execute(fk_query)
                fks = cur.fetchall()

        # =========================
        # Structuration FK
        # =========================
        fk_map = {}

        for row in fks:
            table_schema, table_name, column_name, \
            foreign_schema, foreign_table, foreign_column = row

            fk_map[(table_schema, table_name, column_name)] = \
                f"(FK → {foreign_schema}.{foreign_table}.{foreign_column})"

        # =========================
        # Structuration Tables
        # =========================
        tables = defaultdict(list)

        for row in columns:
            table_schema = row[0]
            table_name = row[1]
            column_name = row[2]
            data_type = row[3]
            char_len = row[4]
            num_precision = row[5]
            num_scale = row[6]
            is_nullable = row[7]

            # Reconstruction type
            if data_type == "character varying" and char_len:
                formatted_type = f"varchar({char_len})"
            elif data_type == "numeric" and num_precision:
                if num_scale:
                    formatted_type = f"numeric({num_precision},{num_scale})"
                else:
                    formatted_type = f"numeric({num_precision})"
            else:
                formatted_type = data_type

            nullable = "" if is_nullable == "YES" else " NOT NULL"

            column_def = f"{column_name} {formatted_type}{nullable}"

            # Ajout FK si existe
            fk_info = fk_map.get((table_schema, table_name, column_name))
            if fk_info:
                column_def += f" {fk_info}"

            tables[(table_schema, table_name)].append(column_def)

        # =========================
        # Construction finale
        # =========================
        result = "## Database Schema\n\n"

        for (schema, table), cols in tables.items():
            result += f"**{schema}.{table}**\n"
            for col in cols:
                result += f"- {col}\n"
            result += "\n"

        return result


    def api_call(self, data_schema):
        client_groq = Groq(api_key=os.getenv("GROQ_API"))
        LLM_GROQ = "llama-3.3-70b-versatile"

        chat_completion = client_groq.chat.completions.create(
            messages=[
                # Set an optional system message. This sets the behavior of the
                # assistant and can be used to provide specific instructions for
                # how it should behave throughout the conversation.
                {
                    "role": "system",
                    "content": "You are a helpful assistant that explains database architecture and business objectives."
                },
                # Set a user message for the assistant to respond to.
                {
                    "role": "user",
                    "content": f"Explain in 1 lines how this database works: {data_schema}",
                }
            ],

            # The language model which will generate the completion.
            model=LLM_GROQ
        )

        # Print the completion returned by the LLM.
        data_context  =  chat_completion.choices[0].message.content
        return data_context

    def save_system_prompt(self, prompt):
        prompt_path = self.generate_prompt_path()
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, "w") as f:
            f.write(prompt)
        print(f"Prompt saved to {prompt_path}")

    def construct_system_prompt(self):

        if os.path.exists(self.generate_prompt_path()):
            print("Prompt already exists. Loading from file.")
            with open(self.generate_prompt_path(), "r") as f:
                prompt = f.read()
            print(f"{prompt[:1000]}...")  # Print the first 1000 characters of the prompt

            return self.generate_prompt_path()
        else:
            schema_info = self.column_data()
            print("------------------------------------------------------------------------------")
            print("------------------------------------------------------------------------------")
            print(schema_info)
            print("------------------------------------------------------------------------------")
            print("------------------------------------------------------------------------------")
            data_context = self.api_call(schema_info)
            print("------------------------------------------------------------------------------")
            print("------------------------------------------------------------------------------")
            print(data_context)
            print("------------------------------------------------------------------------------")
            print("------------------------------------------------------------------------------")
            prompt = self.generate_prompt(data_context, schema_info)
            self.save_system_prompt(prompt)

            return self.generate_prompt_path()



    