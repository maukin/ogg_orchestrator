from app.models.executor import ExecutorResult
from app.services.deployment_execution_summary_service import DeploymentExecutionSummaryService


def test_build_execution_summary():
    svc = DeploymentExecutionSummaryService()

    summary = svc.build_summary(
        deployment_id="dep1",
        environment_name="dev",
        step_results=[
            (
                "prepare_source",
                ExecutorResult(
                    success=True,
                    executed_count=2,
                    skipped_count=0,
                    raw_output="ok",
                    error_code=None,
                    error_message=None,
                    http_status=200,
                    request_artifact="req.json",
                    response_artifact="resp.json",
                ),
            ),
            ("attach_extract", None),
        ],
    )

    assert summary.deployment_id == "dep1"
    assert len(summary.step_results) == 2
    assert summary.step_results[0].step_name == "prepare_source"
    assert summary.step_results[0].success is True
    assert summary.step_results[1].step_name == "attach_extract"
    assert summary.step_results[1].success is None