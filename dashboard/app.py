from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json, os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "remediation_history.jsonl")

@app.get("/api/alerts")
def get_alerts():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE) as f:
        records = [json.loads(line) for line in f if line.strip()]
    return sorted(records, key=lambda r: r["time"], reverse=True)

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")