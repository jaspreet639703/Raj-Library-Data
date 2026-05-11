"""
api/app.py — FastAPI endpoints for Hugging Face Spaces deployment.
Provides health check + manual trigger + status + CSV download.
"""

import asyncio
import os
import json
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.storage import get_all_records, export_csv
from scraper.checkpoint import load_checkpoint, reset_checkpoint

app = FastAPI(title="Dholpur Library Scraper")
_scraper_task = None


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/status")
def status():
    completed = load_checkpoint()
    records = get_all_records()
    return {
        "completed_jobs": len(completed),
        "total_records": len(records),
        "tehsils_done": list({r["tehsil"] for r in records}),
    }


@app.post("/start")
async def start(background_tasks: BackgroundTasks):
    global _scraper_task
    from scraper.main import run
    background_tasks.add_task(run)
    return {"message": "Scraper started in background. Check /status for progress."}


@app.get("/export")
def export():
    path = export_csv()
    if os.path.exists(path):
        return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))
    return JSONResponse({"error": "No data yet"}, status_code=404)


@app.post("/reset")
def reset():
    reset_checkpoint()
    return {"message": "Checkpoint cleared. Next /start will re-scrape everything."}
