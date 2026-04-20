from __future__ import annotations

from app.models.attach_replicat_result import AttachReplicatExecutionResult


def attach_replicat_result_to_payload(result: AttachReplicatExecutionResult | None) -> dict:
    if result is None:
        return {
            "success": None,
            "executed_count": None,
            "skipped_count": None,
            "group_name": None,
            "applied_tables_count": None,
            "started_at": None,
            "finished_at": None,
            "raw_output": None,
            "error_code": None,
            "error_message": "Attach replicat executor returned no result.",
            "request_artifact": None,
            "response_artifact": None,
            "restart_performed": result.restart_performed,
            "rollback_performed": result.rollback_performed,
        }

    return {
        "success": result.success,
        "executed_count": result.executed_count,
        "skipped_count": result.skipped_count,
        "group_name": result.group_name,
        "applied_tables_count": result.applied_tables_count,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "raw_output": result.raw_output,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "request_artifact": result.request_artifact,
        "response_artifact": result.response_artifact,
        "restart_performed": result.restart_performed,
        "rollback_performed": result.rollback_performed,
    }