"""Owner: Kunal. FastAPI endpoints + audit log (logs/audit.jsonl).

Every /ask call writes one JSONL line: trace_id, question, answer_type, tools, verifier, latency_ms.
Run from repo root: uvicorn backend.api:app --reload
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import agent, report, tools

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "logs" / "audit.jsonl"
CHANGELOG = ROOT / "outputs" / "changelog.md"

app = FastAPI(title="Nimbus AI: Value Intelligence Assistant", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def log_audit(entry):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


@app.get("/health")
def health():
    return {"status": "ok", "as_of": str(tools.AS_OF)}


@app.post("/ask")
def ask(req: AskRequest):
    start = time.perf_counter()
    result = agent.ask(req.question)
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
    log_audit({"ts": datetime.now(timezone.utc).isoformat(), "question": req.question,
               "trace_id": result["trace_id"], "answer_type": result["answer_type"],
               "answer": result["answer"], "tools_invoked": result["tools_invoked"],
               "verifier": result["verifier"], "mode": result["mode"],
               "latency_ms": result["latency_ms"]})
    return result


@app.get("/scorecard")
def scorecard(initiative: str | None = None, metric: str | None = None):
    result = tools.get_scorecard(initiative, metric)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/report")
def weekly_report():
    path = report.weekly_report()
    return {"written": str(path.relative_to(ROOT)), "markdown": path.read_text(encoding="utf-8")}


@app.get("/changelog")
def changelog():
    if not CHANGELOG.exists():
        raise HTTPException(status_code=404, detail="Run python -m backend.clean_data first")
    return {"markdown": CHANGELOG.read_text(encoding="utf-8")}


@app.get("/audit")
def audit(limit: int = 20):
    if not AUDIT.exists():
        return {"entries": []}
    lines = AUDIT.read_text(encoding="utf-8").strip().splitlines()[-limit:]
    return {"entries": [json.loads(line) for line in lines]}
