from app.models.enums import TableState
from app.services.step_execution_policy_service import StepExecutionPolicyService


def test_policy_execute_when_state_matches():
    svc = StepExecutionPolicyService()
    decision = svc.evaluate(
        table_id="T1",
        current_state=TableState.PLANNED,
        expected_state=TableState.PLANNED,
        success_state=TableState.PREPARED,
    )
    assert decision.decision == "EXECUTE"


def test_policy_skip_when_state_is_already_further():
    svc = StepExecutionPolicyService()
    decision = svc.evaluate(
        table_id="T1",
        current_state=TableState.CDC_CAPTURE_ATTACHED,
        expected_state=TableState.PREPARED,
        success_state=TableState.CDC_CAPTURE_ATTACHED,
    )
    assert decision.decision == "SKIP"


def test_policy_invalid_when_state_is_too_early():
    svc = StepExecutionPolicyService()
    decision = svc.evaluate(
        table_id="T1",
        current_state=TableState.PLANNED,
        expected_state=TableState.PREPARED,
        success_state=TableState.CDC_CAPTURE_ATTACHED,
    )
    assert decision.decision == "INVALID_STATE"