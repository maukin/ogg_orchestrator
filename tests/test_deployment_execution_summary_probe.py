from app.models.deployment_reporting import DeploymentExecutionSummary
from app.services.deployment_execution_summary_service import DeploymentExecutionSummaryService


class DummyProbeResult:
    def __init__(self):
        self.success = True
        self.http_status = None
        self.request_artifact = "probe_request.json"
        self.response_artifact = "probe_response.json"
        self.raw_output = "ok"
        self.error_code = None
        self.error_message = None


def test_execution_summary_supports_probe_results():
    svc = DeploymentExecutionSummaryService()

    summary = svc.build_summary(
        deployment_id="dep1",
        environment_name="dev",
        step_results=[
            ("probe_extract_status:EXT_01", DummyProbeResult()),
        ],
    )

    assert summary.deployment_id == "dep1"
    assert len(summary.step_results) == 1
    assert summary.step_results[0].step_name == "probe_extract_status:EXT_01"
    assert summary.step_results[0].success is True
    assert summary.step_results[0].request_artifact == "probe_request.json"