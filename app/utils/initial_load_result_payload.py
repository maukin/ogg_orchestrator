from __future__ import annotations

from app.models.initial_load_result import InitialLoadExecutionResult


def initial_load_result_to_payload(result: InitialLoadExecutionResult | None) -> dict:
    if result is None:
        return {
            "success": None,
            "executed_count": None,
            "skipped_count": None,
            "load_batch_id": None,
            "rows_loaded": None,
            "started_at": None,
            "finished_at": None,
            "instantiation_candidate_scn": None,
            "raw_output": None,
            "error_code": None,
            "error_message": "Initial load executor returned no result.",
            "request_artifact": None,
            "response_artifact": None,
        }

    return {
        "success": result.success,
        "executed_count": result.executed_count,
        "skipped_count": result.skipped_count,
        "load_batch_id": result.load_batch_id,
        "rows_loaded": result.rows_loaded,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "instantiation_candidate_scn": result.instantiation_candidate_scn,
        "raw_output": result.raw_output,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "request_artifact": result.request_artifact,
        "response_artifact": result.response_artifact,
    }