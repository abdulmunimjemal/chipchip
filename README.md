# ChipChip AI Marketing Agent

This project is an AI-powered data agent built with FastAPI that allows non-technical marketing stakeholders to ask natural language questions and receive insightful answers, including auto-generated charts, from a ClickHouse database.

## Core Features

-   **Natural Language to SQL**: Translates user questions into complex SQL queries.
-   **Conversational Memory**: Maintains conversation context for follow-up questions using Redis for session management.
-   **Multi-Layered AI Reasoning**:
    1.  **SQL Generation**: Creates a robust SQL query to fetch the correct data.
    2.  **Answer Synthesis**: Formulates a clean, human-readable answer from the query results.
    3.  **Chart Suggestion**: Intelligently determines if a chart is needed and suggests the best type (bar, line, table, etc.).
-   **Chart-Ready Data**: Formats the data payload specifically for easy rendering by a frontend charting library.
-   **Containerized**: The entire application stack (FastAPI, ClickHouse, Redis) is managed via Docker Compose for easy setup and deployment.

## Tech Stack

-   **Backend**: FastAPI, Python 3.10+
-   **AI / LLM**: LangChain, Google Gemini
-   **Database**: ClickHouse
-   **Session Store**: Redis
-   **Containerization**: Docker, Docker Compose
-   **Dependency Management**: Poetry

## Project Structure

The source code is organized for clarity and scalability:

```

src/
├── api/              # API endpoint definitions (routers)
├── core/             # Core application logic and settings (config, LLM setup)
├── db/               # Database related modules 
├── schemas/          # Pydantic models for API request/response validation
└── services/         # Business logic (the AI Agent service)

````

## Setup and Running the Project

Follow these steps to get the application running locally.

### Prerequisites

-   Docker and Docker Compose
-   Python 3.10+ and Poetry
-   Git
-   A Google AI API Key

### 1. Clone the Repository

```bash
git clone https://github.com/abdulmunimjemal/chipchip.git
cd chipchip
````

### 2\. Configure Environment

Create a `.env` file in the root of the project by copying the example below. 
(Or you can find an example under `src/.env.example`)

Fill in your `GOOGLE_API_KEY`.

**.env file:**

```env
# --- Google AI ---
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY_HERE"

# --- LLM Model ---
# Use the latest stable model or a specific preview you have access to
LLM_MODEL_NAME="models/gemini-2.5-flash-preview-04-17" 

# --- Docker Service Names (Do not change unless you edit docker-compose.yml) ---
CLICKHOUSE_HOST="clickhouse-server"
CLICKHOUSE_PORT="8123"
CLICKHOUSE_USERNAME="default"
CLICKHOUSE_PASSWORD=""
CLICKHOUSE_DATABASE="chipchip_db"

REDIS_HOST="redis"
REDIS_PORT="6379"
REDIS_PASSWORD=""
```

### 3\. Build and Run Services

This single command will build the FastAPI app's Docker image and start all services (FastAPI, ClickHouse, Redis).

```bash
docker-compose up --build -d
```

The FastAPI application will be available at `http://localhost:8000`.

### 4\. Initialize the Database (First-Time Setup)

After the containers are running, you need to initialize the database with the schema and sample data. Run these two commands from your project root directory.

**a. Create the database tables:**

```bash
docker exec -i chipchip-clickhouse clickhouse-client --database="chipchip_db" --multiquery < ./data/create_tables_poc.sql
```

**b. Populate the tables with sample data:**
*(This script runs locally and connects to the ClickHouse container)*

```bash
python ./data/generate_sample_data_poc.py
```

Your application is now fully set up and ready to accept API requests.

## API Usage

The interactive API documentation (Swagger UI) is available at:
**[http://localhost:8000/api/v1/docs](https://www.google.com/search?q=http://localhost:8000/api/v1/docs)**

You can use the docs to test the endpoint or use a tool like `curl`.

### Example API Calls

**1. Initial Request (Starting a new conversation)**

Omit the `session_id`. The server will generate one and return it in the response.

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/ask' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "Show me the number of users for each registration channel."
}'
```

**2. Follow-up Request (Continuing the conversation)**

Use the `session_id` you received from the previous response to maintain context.

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/ask' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "Which of those has the most users?",
  "session_id": "the_session_id_from_the_previous_response"
}'
```
