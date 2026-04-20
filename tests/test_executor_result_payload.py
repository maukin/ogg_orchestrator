from app.models.executor import ExecutorResult
from app.utils.executor_result_payload import executor_result_to_payload


def test_executor_result_to_payload():
    result = ExecutorResult(
        success=True,
        executed_count=2,
        skipped_count=1,
        raw_output="ok",
        error_code=None,
        error_message=None,
        http_status=200,
        request_artifact="req.json",
        response_artifact="resp.json",
    )

    payload = executor_result_to_payload(result)

    assert payload["success"] is True
    assert payload["executed_count"] == 2
    assert payload["skipped_count"] == 1
    assert payload["http_status"] == 200
    assert payload["request_artifact"] == "req.json"
    assert payload["response_artifact"] == "resp.json"