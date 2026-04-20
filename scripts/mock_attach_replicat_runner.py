from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/mock_attach_replicat_runner.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])

    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    commands = request_payload.get("commands", [])

    now = datetime.now(timezone.utc).isoformat()
    group_name = commands[0]["replicat_group"] if commands else None

    response_payload = {
        "success": True,
        "executed_count": len(commands),
        "skipped_count": 0,
        "group_name": group_name,
        "applied_tables_count": len(commands),
        "started_at": now,
        "finished_at": now,
        "raw_output": "Mock attach replicat runner completed successfully.",
        "error_code": None,
        "error_message": None,
        "restart_performed": True,
        "rollback_performed": False,
    }

    response_path.write_text(
        json.dumps(response_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())