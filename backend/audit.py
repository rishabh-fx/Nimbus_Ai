# 	Maintains activity logs
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "audit.jsonl"

_lock = Lock()


def write_audit_log(action: str, status: str, details: str = ""):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "status": status,
        "details": details[:500]
    }

    with _lock:
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")

