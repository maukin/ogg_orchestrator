from __future__ import annotations

from app.models.executor import ExecutorResult


def executor_result_to_payload(result: ExecutorResult | None) -> dict:
    if result is None:
        return {
            "success": None,
            "executed_count": None,
            "skipped_count": None,
            "raw_output": None,
            "error_code": None,
            "error_message": "Executor returned no result.",
            "http_status": None,
            "request_artifact": None,
            "response_artifact": None,
        }

    return {
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