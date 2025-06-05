# Technical Proposal: ChipChip AI Marketing Agent

**Author:** Abdulmunim Jundurahman
**Date:** June 5, 2025
**Project:** Take-Home Assessment for AI Agent Developer Role

## 1. Chosen Approach & Rationale

To address the project goal of creating an AI agent for marketing stakeholders, this proof-of-concept (PoC) employs a **Multi-Stage, Agentic Approach using LangChain Expression Language (LCEL)**. This layered architecture provides superior control, reliability, and extensibility compared to a single, monolithic chain.

The agent's reasoning process is broken down into three distinct, specialized stages:

1.  **SQL Generation:** A dedicated LLM chain analyzes the user's natural language question, conversational history, and the database schema to generate a syntactically correct ClickHouse SQL query. This specialization ensures the highest possible accuracy for data retrieval.

2.  **Answer Synthesis:** After the SQL query is executed, a separate LLM chain receives the original question, the generated SQL, and the data returned from the database. Its sole purpose is to synthesize a concise, user-friendly, and non-technical natural language answer. This decouples the final response from the raw database output.

3.  **Visualization Intelligence:** In parallel with answer synthesis, a third LLM chain analyzes the user's question and the query results to determine if a visualization is appropriate. It returns a structured JSON object specifying the best chart type (`bar`, `line`, `table`, etc.) and the data mapping required, enabling a frontend to dynamically render insightful charts.

**Rationale:**
-   **Reliability:** By breaking down the complex task into smaller, specialized sub-tasks, each chain can be prompted and optimized for its specific purpose, leading to more reliable and accurate results.
-   **Control & Debuggability:** This approach gives us full control over the data flow between steps, making it easier to debug issues at each stage of the process (SQL generation, data execution, answer synthesis, chart suggestion).
-   **Extensibility:** New capabilities (e.g., a data analysis tool, anomaly detection) can be added as new, independent stages in the agent's workflow without disrupting existing logic.
-   **User Experience:** Explicitly generating both a natural language answer and a chart suggestion provides a richer, more actionable experience for the end-user.

## 2. Architecture Diagram

The following diagram illustrates the flow of a user request through the system, from the client to the various backend components and back.

[I will include the image here]

## 3. Technology Stack

-   **Backend Framework**: FastAPI
-   **Programming Language**: Python 3.10+
-   **AI Framework**: LangChain (specifically LangChain Expression Language - LCEL)
-   **LLM Provider**: Google Gemini (via `langchain-google-genai`)
-   **Data Warehouse**: ClickHouse
-   **Session Store**: Redis
-   **Containerization**: Docker, Docker Compose
-   **Data Handling**: Pandas
-   **API Schema Validation**: Pydantic

## 4. History & Memory Management

Conversational context is crucial for handling follow-up questions. This architecture implements robust session management using Redis:

-   Each user conversation is assigned a unique `session_id`, managed by the client and passed with each API request.
-   The `RedisChatMessageHistory` class from LangChain is used to store and retrieve the history of questions and answers for each `session_id`.
-   The chat history is passed into the SQL Generation prompt, giving the LLM the necessary context to understand follow-up questions (e.g., "What about for last month?").
-   A Time-To-Live (TTL) is set on Redis keys to automatically clear out idle sessions.

## 5. Limitations & Future Improvements

This PoC successfully demonstrates the core functionality but has clear areas for enhancement in a production environment.

**Limitations:**

-   **Prompt Sensitivity**: The quality of the generated SQL is highly dependent on the quality and specificity of the prompt engineering.
-   **Complex Query Handling**: While capable, extremely complex analytical questions that require multi-step SQL queries or procedural logic might still pose a challenge.
-   **Security**: The current implementation assumes trusted inputs. A production system would require robust validation and safeguards against SQL injection, even with the LLM as an intermediary.
-   **No Frontend**: The PoC focuses exclusively on the backend API.

**Future Improvements:**

-   **Interactive Frontend**: Develop a web interface (e.g., using React or Streamlit) to provide a user-friendly way to interact with the agent and render the suggested charts.
-   **Advanced Agentic Tools**: Enhance the agent with more tools beyond SQL, such as a Python REPL for performing complex data analysis, calculations, or transformations that are difficult to do in pure SQL.
-   **Enhanced Error Correction**: Implement a feedback loop where SQL execution errors are passed back to the LLM, allowing it to self-correct its generated query.
-   **Cost & Performance Monitoring**: Integrate monitoring for LLM token usage, query execution times, and API latency to manage costs and ensure performance at scale.

