from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python scripts/ogg_start_process.py <extract|replicat> <process_name> <response.json>")
        return 2

    process_type = sys.argv[1].strip().lower()
    process_name = sys.argv[2].strip().upper()
    response_path = Path(sys.argv[3])

    if process_type not in {"extract", "replicat"}:
        raise RuntimeError(f"Unsupported process_type: {process_type}")

    started_at = utc_now()

    adminclient_path = require_env("OGG_ADMINCLIENT_PATH")
    admin_url = require_env("OGG_ADMIN_URL")
    deployment = require_env("OGG_ADMIN_DEPLOYMENT")
    username = require_env("OGG_ADMIN_USER")
    password = require_env("OGG_ADMIN_PASSWORD")

    command_name = "EXTRACT" if process_type == "extract" else "REPLICAT"

    admin_script = "\n".join(
        [
            f'CONNECT {admin_url} DEPLOYMENT {deployment} AS {username} PASSWORD "{password}"',
            f"START {command_name} {process_name}",
            f"INFO {command_name} {process_name}",
            "EXIT",
            "",
        ]
    )

    try:
        completed = subprocess.run(
            [adminclient_path],
            input=admin_script,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )

        payload = {
            "success": completed.returncode == 0,
            "process_type": process_type,
            "process_name": process_name,
            "started_at": started_at,
            "finished_at": utc_now(),
            "stdout_text": completed.stdout,
            "stderr_text": completed.stderr,
            "returncode": completed.returncode,
            "error_code": None if completed.returncode == 0 else f"EXIT_{completed.returncode}",
            "error_message": None if completed.returncode == 0 else "AdminClient START failed.",
        }
        write_json(response_path, payload)
        return 0 if completed.returncode == 0 else 1

    except Exception as exc:
        write_json(
            response_path,
            {
                "success": False,
                "process_type": process_type,
                "process_name": process_name,
                "started_at": started_at,
                "finished_at": utc_now(),
                "stdout_text": None,
                "stderr_text": None,
                "returncode": None,
                "error_code": "ADMINCLIENT_EXCEPTION",
                "error_message": str(exc),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())