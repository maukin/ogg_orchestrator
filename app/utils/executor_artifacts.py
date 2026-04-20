from __future__ import annotations

from pathlib import Path
import json

from app.models.executor import ExecutorResult


def write_executor_result_artifact(
    result: ExecutorResult,
    artifacts_dir: str | Path,
    filename: str,
) -> str:
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "success": result.success,
        "executed_count": result.executed_count,
        "skipped_count": result.skipped_count,
        "raw_output": result.raw_output,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "http_status": result.http_status,
        "request_artifact": result.request_artifact,
        "response_artifact": result.response_artifact,
    }

    path = out_dir / filename
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)