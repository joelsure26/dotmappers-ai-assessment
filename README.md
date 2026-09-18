# DOTMappers AI Engineer Assessment — AI Support Analytics

An end-to-end AI system for querying and monitoring customer-support tickets. It ingests the provided 500-row CSV, stores it in SQLite, uses an LLM for natural-language intent understanding, exposes REST endpoints, and provides a minimal browser UI.

## Features
- CSV ingestion and validation into SQLite.
- Natural-language analytics through an LLM (Ollama by default).
- Anomaly detection for unusually long resolution times and unresolved High/Critical tickets older than 24 hours.
- FastAPI REST API.
- Minimal web UI served by FastAPI.
- Deterministic fallback parsing is included only to keep the demo usable when Ollama is temporarily unavailable; normal assessment operation should use Ollama.

## Architecture
```text
support_tickets.csv
       |
       v
 Pandas ingestion
       |
       v
 SQLite database <---- Query Engine
       |                    ^
       |                    |
       +---- FastAPI <--- LLM intent parser (Ollama)
                  |
                  v
            Browser UI
```

## Requirements
- Python 3.10+
- Ollama installed locally
- A local Ollama model. The default is `llama3.2:3b`.

## Setup
### 1. Create virtual environment
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Install/start Ollama
Install Ollama from its official website, then pull the model:
```powershell
ollama pull llama3.2:3b
```
Make sure Ollama is running before testing natural-language queries.

Optional environment variables:
```powershell
$env:OLLAMA_MODEL="llama3.2:3b"
$env:OLLAMA_URL="http://localhost:11434/api/generate"
```

### 3. Start the application
From the project root:
```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the UI.
API docs: `http://127.0.0.1:8000/docs`

## REST API
- `GET /health` — service health check.
- `POST /query` — natural-language query. Example body:
```json
{"question":"How many tickets are currently open?"}
```
- `GET /anomalies` — anomaly report.

## Example queries
- How many tickets are currently open?
- Which agent resolved the most tickets?
- Show me all Critical tickets not resolved within 12 hours.
- What is the average customer rating for Technical category tickets?
- Are there any anomalies in resolution times this week?

## Anomaly logic
1. **Long resolution:** tickets with resolution time above a statistical threshold derived from the resolved-ticket distribution.
2. **Business-rule anomaly:** unresolved High/Critical tickets older than 24 hours.

The dataset's dates are from 2024, so the "older than 24 hours" rule is evaluated against the current system time. For a historical/week-specific implementation, the reference timestamp can be changed to a requested reporting date.

## LLM design
The LLM does not generate SQL. It maps the user's question to a small allow-listed intent schema. The application then executes fixed, parameterized SQL. This reduces SQL-injection risk and makes the system easier to test and explain.

## Known limitations
- Ollama and a local model must be installed for genuine LLM-powered intent parsing.
- The current anomaly endpoint uses the current system time for the 24-hour business rule.
- The UI is intentionally minimal for the assessment.
- The dataset is small (500 rows), so SQLite is sufficient; a production-scale system could use PostgreSQL and a background ingestion pipeline.
