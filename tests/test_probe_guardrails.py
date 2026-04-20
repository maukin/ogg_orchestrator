from app.models.executor import ExecutorResult
from app.models.deployment import DeploymentPlan
from app.models.registry import DesiredTableConfig
from app.models.enums import LoadMethod, ReplicationMode
from app.services.deployment_execution_summary_service import DeploymentExecutionSummaryService


class DummyProbeResult:
    def __init__(self, success: bool, error_code=None, error_message=None):
        self.success = success
        self.http_status = 500 if not success else 200
        self.request_artifact = "probe_request.json"
        self.response_artifact = "probe_response.json"
        self.raw_output = "fail" if not success else "ok"
        self.error_code = error_code
        self.error_message = error_message


def test_probe_result_can_be_reflected_in_execution_summary():
    svc = DeploymentExecutionSummaryService()

    summary = svc.build_summary(
        deployment_id="dep1",
        environment_name="dev",
        step_results=[
            ("probe_extract_status:EXT_01", DummyProbeResult(False, "HTTP_500", "Extract down")),
        ],
    )

    assert len(summary.step_results) == 1
    assert summary.step_results[0].step_name == "probe_extract_status:EXT_01"
    assert summary.step_results[0].success is False
    assert summary.step_results[0].error_code == "HTTP_500"