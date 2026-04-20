from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python mock_initial_load_runner.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])

    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    commands = request_payload.get("commands", [])

    now = datetime.now(timezone.utc).isoformat()

    response_payload = {
        "success": True,
        "executed_count": len(commands),
        "skipped_count": 0,
        "load_batch_id": f"mock_batch_{len(commands)}",
        "rows_loaded": 0,
        "started_at": now,
        "finished_at": now,
        "instantiation_candidate_scn": None,
        "raw_output": "Mock initial load runner completed successfully.",
        "error_code": None,
        "error_message": None,
    }

    response_path.write_text(
        json.dumps(response_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Mock initial load completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())