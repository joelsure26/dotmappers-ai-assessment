from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .database import initialize_database
from .llm import parse_intent
from .query_engine import execute

app = FastAPI(title="DOTMappers AI Support Analytics", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent.parent

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/health")
def health():
    return {"status": "ok", "service": "DOTMappers-ai-support-analytics"}

@app.post("/query")
def natural_language_query(request: QueryRequest):
    try:
        intent, model_source = parse_intent(request.question)
        result = execute(intent)
        return {"question": request.question, "intent": intent, "model_source": model_source, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/anomalies")
def anomalies():
    try:
        intent = {"intent": "anomalies", "filters": {}}
        return execute(intent)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/", response_class=HTMLResponse)
def ui():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
