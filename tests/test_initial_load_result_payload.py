from app.models.initial_load_result import InitialLoadExecutionResult
from app.utils.initial_load_result_payload import initial_load_result_to_payload


def test_initial_load_result_to_payload():
    result = InitialLoadExecutionResult(
        success=True,
        executed_count=1,
        skipped_count=0,
        load_batch_id="batch_1",
        rows_loaded=100,
        started_at="2026-04-13T10:00:00+00:00",
        finished_at="2026-04-13T10:01:00+00:00",
        instantiation_candidate_scn=123456,
        raw_output="ok",
        error_code=None,
        error_message=None,
        request_artifact="req.json",
        response_artifact="resp.json",
    )

    payload = initial_load_result_to_payload(result)

    assert payload["success"] is True
    assert payload["load_batch_id"] == "batch_1"
    assert payload["rows_loaded"] == 100
    assert payload["instantiation_candidate_scn"] == 123456