import json
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/dynamic-metadata", tags=["Dynamic Metadata Assurance"])

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "dynamic_assurance" / "latest_metadata_assurance.json"
RUN_LOCK = threading.Lock()


@router.get("/latest")
def latest():
    if not REPORT.exists():
        raise HTTPException(status_code=404, detail="Run metadata assurance first")

    return json.loads(REPORT.read_text(encoding="utf-8"))


@router.post("/run")
def run_all():
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Assurance already running")

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "app.services.dynamic_gold_metadata_assurance"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )

        if completed.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=(completed.stderr or completed.stdout)[-2000:],
            )

        if not REPORT.exists():
            raise HTTPException(status_code=500, detail="Report was not generated")

        return json.loads(REPORT.read_text(encoding="utf-8"))

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Assurance exceeded 180 seconds")
    finally:
        RUN_LOCK.release()
