from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain_experimental.sql import SQLDatabaseChain
from datetime import datetime

from src.core.config import settings

# initilize
try:
    llm = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0, # we want a deterministic responses
        convert_system_message_to_human=True
    )
    print(f"LLM ({settings.LLM_MODEL_NAME}) initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR initializing LLM: {e}")
    llm = None # Ensure llm is None if initialization fails

db_uri = (
    f"clickhouse://{settings.CLICKHOUSE_USERNAME}:{settings.CLICKHOUSE_PASSWORD}"
    f"@{settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}/{settings.CLICKHOUSE_DATABASE}"
)
db = None
if llm: # Only proceed if LLM is available
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
        # db remains None
else:
    print("LLM not initialized, skipping LangChain SQLDatabase setup.")


# --- Prompt Template for SQL Chain --- 
# TODO: (Munim) Use prompt managment system to manage, version and experiment different prompts
# Starting with Agenta

CUSTOM_PROMPT_TEMPLATE_POC = """Given an input question, first create a syntactically correct {dialect} query to run against the provided PoC tables, then look at the results of the query and return the answer.
You MUST use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Only use the tables listed below, which are designed for this PoC:
{table_info}

Key ClickHouse reminders:
- Dates: `toDate('YYYY-MM-DD')`, `toDateTime('YYYY-MM-DD HH:MM:SS')`. `DateTime64` is often used.
- Functions: `toDayOfWeek(date)` (1=Mon, 7=Sun), `toHour(dateTime)`, `formatDateTime(dateTime, '%Y-%m')` for year-month.
- Assume today is {current_date} for relative date queries like "last weekend" or "last month".
- `users_poc.registration_date` is the signup date. `orders_poc.order_date` is the purchase date.
- `products_poc.category_name` directly contains category like 'Fresh Produce'.
- `users_poc.is_group_leader` is a Boolean.
- `groups_poc.group_leader_id` links to `users_poc.user_id`.
- `group_members_poc.linked_order_id` links a group participation to a specific order in `orders_poc`.
If the question is a follow-up, consider the preceding conversation stored in the 'chat_history'.

Chat History:
{chat_history}

Question: {input}""" 

sql_chain_prompt = None
if db and llm: # Ensure db and llm are successfully initialized
    sql_chain_prompt = PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE_POC,
        input_variables=["input", "table_info", "dialect", "chat_history"], # Sth different from the notebook: chat_history
        partial_variables={"current_date": datetime.now().strftime('%Y-%m-%d')}
    )
    print("SQL Chain Prompt Template created.")
else:
    print("SQL Chain Prompt Template not created due to missing LLM or DB connection.")
