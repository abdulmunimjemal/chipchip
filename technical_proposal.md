# Technical Proposal & Architecture: ChipChip AI Marketing Agent

**Abdulmunim Jundurahman**
**Date:** June 5, 2025

## 1. Chosen Approach & Rationale

The proposed AI agent will employ a **Natural Language Interface to SQL (NLI-to-SQL)** approach, augmented with a Large Language Model (LLM). This approach is well-suited for the task of translating natural language marketing questions into actionable database queries.

* **NLI-to-SQL:** This directly addresses the core requirement of querying a structured database (ClickHouse) using natural language.
* **LLM (Gemini Flash 2.5):** An LLM is essential for understanding the nuances of natural language, including intent, entities, and relationships within the questions. Gemini Flash 1.5 Pro offers a good balance of capability and accessibility (via its free tier API).
* **LangChain Framework:** LangChain will be used to streamline the development process. It provides modules for LLM integration, prompt management, database interaction (SQLDatabaseChain), and memory.

**Rationale:**
* **Accuracy:** Modern LLMs, when provided with proper schema context and well-crafted prompts, can generate accurate SQL queries.
* **Flexibility:** This approach can handle a wide variety of queries, including those requiring joins, aggregations, and filtering, as demonstrated by the sample questions.
* **Scalability (Conceptual):** While this PoC focuses on a defined schema, the NLI-to-SQL approach can be extended with more sophisticated schema mapping and query validation for larger, more complex databases.
* **Speed of Development:** Using existing LLMs and frameworks like LangChain allows for rapid PoC development.

## 2. Architecture Diagram

+-----------------------+      +----------------------+      +---------------------+
|   User Interface      |&lt;---->|      AI Agent        |&lt;---->|  ChipChip Database  |
| (Jupyter/Streamlit)   |      |   (LangChain/LLM)    |      |    (ClickHouse)     |
+-----------------------+      +----------------------+      +---------------------+
^                               |
|                               | User Query
| Processed Answer              |
| (Text, Table, Chart           |
|  Suggestion)                  v
|                      +----------------------+
|                      |   Query Understanding  |
|                      |        (LLM)         |
|                      +----------------------+
|                               |
|                               | NL Query
|                               v
|                      +----------------------+
|                      |   SQL Generation     |
|                      |   (LLM + Schema)     |
|                      +----------------------+
|                               |
|                               | SQL Query
|                               v
|                      +----------------------+      +-----------------+
|                      |  Database Connector  |----->|  History/Memory |
|                      |   (ClickHouse Driver)|      |   (LangChain)   |
|                      +----------------------+      +-----------------+
|                               |
|                               | Query Results
|                               v
|                      +----------------------+
|                      |  Response Formatter  |
|                      +----------------------+
|                                ^
+--------------------------------+



**Components:**

1.  **User Interface (UI):** A simple interface (Jupyter Notebook for PoC, potentially Streamlit for demo) for users to input natural language questions.
2.  **AI Agent (LangChain & LLM):**
    * **Query Understanding (LLM):** Parses the user's natural language query to understand intent and extract key parameters.
    * **SQL Generation (LLM + Schema):** The LLM, primed with the ClickHouse database schema, generates the appropriate SQL query.
    * **Database Connector (ClickHouse Driver):** Executes the generated SQL query against the ClickHouse database.
    * **Response Formatter:** Processes the database results into a user-friendly format (text summary, formatted table). It will also suggest appropriate chart types based on the nature of the data (e.g., time series -> line chart, categorical comparison -> bar chart).
    * **History/Memory Management (LangChain):** Retains conversational context to handle follow-up questions and improve interaction quality.
3.  **ChipChip Database (ClickHouse):** The simulated ClickHouse database containing the marketing, sales, and user data.

## 3. Technology Stack

* **Programming Language:** Python 3.9+
* **LLM:** Google Gemini Flash 2.5 (via `google-generativeai` SDK or LangChain integration)
* **Framework:** LangChain (for agent structure, LLM integration, SQL chains, memory)
* **Database:** ClickHouse (simulated locally using Docker, or a cloud instance if preferred)
* **Database Driver:** `clickhouse-connect`
* **Data Manipulation:** Pandas (for data generation and result handling)
* **Development Environment:** Jupyter Notebook
* **Optional UI for Demo:** Streamlit
* **Version Control:** Git

**Rationale for Choices:**
* **Python:** Rich ecosystem for AI/ML, data science, and web development.
* **Gemini Flash 1.5 Pro:** Capable model with a free tier suitable for PoC development.
* **LangChain:** Simplifies building LLM-powered applications, providing necessary abstractions for chains, agents, and memory.
* **ClickHouse:** As specified in the assessment requirements. It's an OLAP database well-suited for analytical queries.
* **Pandas:** Industry standard for data manipulation in Python.
* **Jupyter Notebook:** Ideal for iterative development, experimentation, and demonstrating the agent's capabilities step-by-step.

## 4. History & Memory Management

Conversational context will be managed using LangChain's built-in memory modules. Specifically:

* **`ConversationBufferMemory`:** This will store the history of the conversation directly. For each new query, the recent history can be passed back to the LLM along with the new query. This helps the LLM understand follow-up questions, references to previous turns (e.g., "what about for product X?" after a general query), and maintain a more natural conversational flow.
* **Schema Awareness in History:** The memory will primarily store the natural language interaction. The database schema itself is provided to the LLM as part of the prompt for SQL generation, rather than stored in the conversational memory for each turn.

The LLM will be prompted to consider the conversation history when generating SQL queries or formulating responses, ensuring that the agent's replies are contextually relevant.

## 5. Limitations & Future Improvements

**Limitations of PoC:**

* **Sample Data Volume:** The generated sample data will be illustrative, not voluminous, which might not reflect performance on a large-scale production database.
* **SQL Generation Accuracy:** While LLMs are powerful, complex or ambiguous queries might lead to incorrect SQL. The PoC will rely on prompt engineering; a robust error detection/correction loop for SQL (e.g., try-except for SQL execution, feeding errors back to LLM) will be basic.
* **Schema Evolution:** The agent is tightly coupled with the provided schema. Changes to the schema would require updating the information provided to the LLM.
* **Security:** Direct SQL generation from LLM output has potential security risks (SQL injection) if not carefully managed. For a PoC, we assume trusted input or use database permissions to limit actions, but production systems would need more robust safeguards.
* **Advanced Visualizations:** The PoC will primarily suggest chart types or output data suitable for charting. Direct generation of complex interactive charts is out of scope but can be integrated with libraries like Plotly/Matplotlib if a Streamlit UI is built.
* **Real-time Data:** The PoC uses static sample data. Integration with a live, updating database would require further considerations.

**Future Improvements:**

* **Robust SQL Validation & Correction:** Implement a module to validate generated SQL syntax and semantics before execution, potentially with a feedback loop to the LLM for self-correction.
* **Advanced RAG (Retrieval Augmented Generation):** For more complex scenarios or if ChipChip had extensive documentation on metrics/KPI definitions, RAG could be used to retrieve relevant context to help the LLM formulate better queries or explanations. (Though unstructured data is out of scope for this PoC).
* **User Authentication & Authorization:** Implement proper security measures for accessing data.
* **Interactive Visualizations:** Integrate libraries like Plotly or Matplotlib to generate charts directly within the agent's response (especially if deployed as a web app).
* **Automated Schema Ingestion:** Develop a mechanism to automatically ingest and represent the database schema for the LLM, making the agent adaptable to schema changes.
* **Performance Optimization:** For larger datasets, optimize query generation and execution.
* **Feedback Mechanism:** Allow users to provide feedback on the agent's answers to help fine-tune the system.
* **Intent Disambiguation:** For ambiguous queries, the agent could ask clarifying questions.
