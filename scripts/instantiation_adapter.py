from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import oracledb


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/instantiation_adapter.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])

    request_payload = json.loads(read_text(request_path))
    commands = request_payload.get("commands", [])
    started_at = utc_now()

    if not commands:
        write_json(
            response_path,
            {
                "success": True,
                "executed_count": 0,
                "skipped_count": 0,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": "No instantiation commands.",
                "error_code": None,
                "error_message": None,
            },
        )
        return 0

    target_connect = require_env("TARGET_DB_CONNECT_STRING")
    source_db_global_name = require_env("SOURCE_DB_GLOBAL_NAME")

    try:
        conn = oracledb.connect(target_connect)
        cur = conn.cursor()

        executed_count = 0

        for cmd in commands:
            source_object_name = f"{cmd['source_schema']}.{cmd['source_table']}"
            instantiation_scn = int(cmd["instantiation_scn"])

            cur.execute(
                """
                BEGIN
                  DBMS_APPLY_ADM.SET_TABLE_INSTANTIATION_SCN(
                    source_object_name   => :source_object_name,
                    source_database_name => :source_database_name,
                    instantiation_scn    => :instantiation_scn
                  );
                END;
                """,
                {
                    "source_object_name": source_object_name,
                    "source_database_name": source_db_global_name,
                    "instantiation_scn": instantiation_scn,
                },
            )
            executed_count += 1

        conn.commit()
        cur.close()
        conn.close()

        write_json(
            response_path,
            {
                "success": True,
                "executed_count": executed_count,
                "skipped_count": 0,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": "Instantiation SCN applied successfully.",
                "error_code": None,
                "error_message": None,
            },
        )
        return 0

    except Exception as exc:
        write_json(
            response_path,
            {
                "success": False,
                "executed_count": 0,
                "skipped_count": 0,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": None,
                "error_code": "INSTANTIATION_EXCEPTION",
                "error_message": str(exc),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())