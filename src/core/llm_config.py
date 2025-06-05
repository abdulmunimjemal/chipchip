# src/core/llm_config.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # Added for the synthesis chain
from datetime import datetime, timedelta

from src.core.config import settings

try:
    llm = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0, # deterministic output for SQL generation
    )
    print(f"LLM ({settings.LLM_MODEL_NAME}) initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR initializing LLM: {e}")
    llm = None

db_uri = (
    f"clickhouse://{settings.CLICKHOUSE_USERNAME}:{settings.CLICKHOUSE_PASSWORD}"
    f"@{settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}/{settings.CLICKHOUSE_DATABASE}"
)
db = None
if llm: 
    try:
        db = SQLDatabase.from_uri(
            db_uri,
            sample_rows_in_table_info=1,
            include_tables=settings.POC_TABLE_NAMES
        )
        print(f"LangChain SQLDatabase connected to {settings.CLICKHOUSE_DATABASE} "
              f"with tables: {db.get_usable_table_names()}")
    except Exception as e:
        print(f"CRITICAL ERROR connecting LangChain SQLDatabase: {e}")
else:
    print("LLM not initialized, skipping LangChain SQLDatabase setup.")


# TODO: (Munim) Add a way to version, manage and experiment with prompt templates
# Prolly you will use Agenta

CUSTOM_PROMPT_FOR_SQL_GENERATION_ONLY = """Given the following input (which includes chat history if available, followed by the 'Current Question') and the database schema, your task is to generate a syntactically correct {dialect} query to answer the 'Current Question'.

**Instructions for SQL Generation:**
1.  Only use the tables listed in the schema below:
{table_info}
2.  Pay close attention to the 'Current Question' to understand the user's intent.
3.  Use the 'Chat History' for context if it's provided and relevant.
4.  **IMPORTANT**: The SQL query you generate MUST be plain text. Do NOT include any markdown fences like ```sql or ```.
5.  Use the `Current Date for reference` when interpreting relative date expressions like "last weekend" or "last month".

Current Date for reference: {current_date}.
Interpreting 'last weekend' for ClickHouse `toDayOfWeek()` (Monday=1, Sunday=7):
  `last_sunday_date = toDate('{current_date}') - (toDayOfWeek(toDate('{current_date}')) % 7)`
  `last_saturday_date = last_sunday_date - 1 DAY`
  Use these calculated dates for filtering `order_date`, for example: `WHERE toDate(order_date) IN (last_saturday_date, last_saturday_date + 1 DAY)` or `WHERE toDate(order_date) = last_saturday_date OR toDate(order_date) = last_sunday_date`.
  Alternatively, for a range query on a DateTime field: `order_date >= toDateTime(last_saturday_date) AND order_date < toDateTime(last_sunday_date + INTERVAL 1 DAY)`.

Input for LLM (contains history and current question):
{input}

SQL Query:"""

sql_chain_prompt = None
if db and llm:
    sql_chain_prompt = PromptTemplate(
        template=CUSTOM_PROMPT_FOR_SQL_GENERATION_ONLY,
        input_variables=["input", "table_info", "dialect"],
        partial_variables={"current_date": datetime.now().strftime('%Y-%m-%d')}
    )
    print("SQL Chain Prompt Template created (for SQL generation only).")
else:
    print("SQL Chain Prompt Template not created due to missing LLM or DB connection.")


# --- Prompt Template for Final Answer Synthesis ---
ANSWER_SYNTHESIS_TEMPLATE = """Given the original user question, the SQL query that was executed to answer it, and the result obtained from the database, please formulate a concise and user-friendly natural language answer.

Original User Question:
{question}

SQL Query Executed:
{sql_query}

Data Returned by SQL Query:
{sql_result_data}

**Instructions for your Answer:**
- If the "Data Returned by SQL Query" is empty (e.g., "Query returned no data.", or an empty list/table), clearly state that no matching information was found.
- Do not just repeat the SQL query or the raw data in your answer.
- Focus on directly answering the "Original User Question" using the information from "Data Returned by SQL Query".
- Keep the answer natural and easy for a non-technical person to understand.

Natural Language Answer:"""

answer_synthesis_prompt = None
answer_synthesis_chain = None 

if llm: # LLM must be available
    answer_synthesis_prompt = PromptTemplate(
        template=ANSWER_SYNTHESIS_TEMPLATE,
        input_variables=["question", "sql_query", "sql_result_data"]
    )
    answer_synthesis_chain = LLMChain(
        llm=llm,
        prompt=answer_synthesis_prompt,
        verbose=True # for debugging this new chain's behavior
    )
    print("Answer Synthesis LLMChain created.")
else:
    print("Answer Synthesis LLMChain not created due to missing LLM.")