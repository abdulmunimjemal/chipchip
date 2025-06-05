from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from datetime import datetime
from typing import Optional

from src.core.config import settings

# --- LLM and DB Initialization ---
llm: Optional[Runnable] = None
db: Optional[SQLDatabase] = None

try:
    llm = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0
    )
    db_uri = (
        f"clickhouse://{settings.CLICKHOUSE_USERNAME}:{settings.CLICKHOUSE_PASSWORD}"
        f"@{settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}/{settings.CLICKHOUSE_DATABASE}"
    )
    db = SQLDatabase.from_uri(
        db_uri,
        sample_rows_in_table_info=1,
        include_tables=settings.POC_TABLE_NAMES
    )
    print("LLM and Database connections initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR initializing LLM or DB connection: {e}")


# --- 1. Prompt & Chain for SQL Generation ---
SQL_GENERATION_TEMPLATE = """Given an input question (which may include chat history) and a database schema, your task is to generate a syntactically correct {dialect} query to answer the user's 'Current Question'.

Instructions:
- Only use the tables listed in the schema: {table_info}
- Use the 'Chat History' for context if it's relevant.
- **IMPORTANT**: The SQL query you generate MUST be plain text without any markdown fences.
- Use the `Current Date` for relative date expressions like "last weekend".

Current Date for reference: {current_date}

Input for LLM:
{input}

SQL Query:"""

sql_generation_prompt = None
sql_generation_chain: Optional[Runnable] = None
if db and llm:
    sql_generation_prompt = PromptTemplate(
        template=SQL_GENERATION_TEMPLATE,
        input_variables=["input", "table_info", "dialect"],
        partial_variables={"current_date": datetime.now().strftime('%Y-%m-%d')}
    )
    sql_generation_chain = sql_generation_prompt | llm | StrOutputParser()


# --- 2. Prompt & Chain for Final Answer Synthesis ---
ANSWER_SYNTHESIS_TEMPLATE = """Given the original user question, the SQL query that was executed, and the data returned by that query, please formulate a concise and user-friendly natural language answer.

Original User Question: {question}
SQL Query Executed: {sql_query}
Data Returned by SQL Query: {sql_result_data}

Instructions:
- If the "Data Returned" is empty or says 'no data', clearly state that no matching information was found.
- Do not repeat the SQL query or raw data.
- Answer the "Original User Question" directly and naturally based on the data. For lists of names, you can say: "The following X were found: Name A, Name B, and Name C."

Natural Language Answer:"""

answer_synthesis_chain: Optional[Runnable] = None
if llm:
    answer_synthesis_prompt = PromptTemplate.from_template(ANSWER_SYNTHESIS_TEMPLATE)
    answer_synthesis_chain = answer_synthesis_prompt | llm | StrOutputParser()


# --- 3. Prompt & Chain for Chart Suggestion ---
CHART_SUGGESTION_TEMPLATE = """Given an original user question and the data returned from a query, decide if a chart is a helpful visualization and what kind.

Original User Question: {question}
Data Returned by Query: {sql_result_data}

Instructions:
- The `chart_type` must be one of: 'bar', 'line', 'pie', 'table', or 'none'.
- **Respond ONLY with a single JSON object.** Do not add any text or markdown fences.

Example (Bar Chart): {{"chart_needed": true, "chart_type": "bar", "title": "Users by Channel", "x_axis_column": "registration_channel", "y_axis_columns": ["user_count"]}}
Example (No Chart): {{"chart_needed": false, "chart_type": "none", "title": "", "x_axis_column": null, "y_axis_columns": []}}

Your Turn:"""

chart_suggestion_chain: Optional[Runnable] = None
if llm:
    chart_suggestion_prompt = PromptTemplate.from_template(CHART_SUGGESTION_TEMPLATE)
    chart_suggestion_chain = chart_suggestion_prompt | llm | StrOutputParser()