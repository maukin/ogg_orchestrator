from pathlib import Path

from app.executors.instantiation_executor import DryRunInstantiationExecutor
from app.models.deployment import DeploymentAction, DeploymentPlan
from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import TableRegistryRecord
from app.services.instantiation_service import InstantiationService
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService


class DummyRegistryRepo:
    def __init__(self):
        self.records = {
            "T1": TableRegistryRecord(
                table_id="T1",
                source_system="SRCDB",
                source_pdb="PDB1",
                source_schema="SRC",
                source_table="ORDERS",
                target_system="TGTDB",
                target_pdb="PDB2",
                target_schema="DDS",
                target_table="ORDERS",
                desired_enabled=True,
                desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
                desired_extract_group="EXT_01",
                desired_replicat_group="REP_01",
                desired_load_method=LoadMethod.DATAPUMP,
                desired_priority="NORMAL",
                desired_size_class="MEDIUM",
                primary_key=("ID",),
                metadata_file="metadata/orders.json",
                actual_extract_group=None,
                actual_replicat_group=None,
                actual_load_batch_id=None,
                state=TableState.INITIAL_LOAD_DONE,
                validation_status=ValidationStatus.UNKNOWN,
                prepared_for_instantiation=False,
                registration_scn=123456,
                instantiation_scn=None,
                initial_load_started_at=None,
                initial_load_finished_at=None,
                cdc_capture_attached_at=None,
                cdc_apply_attached_at=None,
                activated_at=None,
                last_deployment_id=None,
                last_error_code=None,
                last_error_message=None,
                created_at=None,
                updated_at=None,
            )
        }

    def get_by_table_id(self, table_id: str):
        return self.records.get(table_id)

    def update_state(self, table_id: str, state: TableState, deployment_id: str, error_code=None, error_message=None):
        self.records[table_id].state = state

    def record_instantiation(self, table_id: str, deployment_id: str, instantiation_scn: int):
        self.records[table_id].instantiation_scn = instantiation_scn

    def mark_error(self, table_id: str, deployment_id: str, error_code=None, error_message=None):
        self.records[table_id].state = TableState.ERROR
        self.records[table_id].last_error_code = error_code
        self.records[table_id].last_error_message = error_message

class DummyEventRepo:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)


class NoResultInstantiationExecutor:
    def execute(self, commands, artifacts_dir):
        return None


def _artifacts_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_instantiation_moves_table_to_instantiated():
    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()
    state_machine = StateMachineService()
    executor = DryRunInstantiationExecutor()

    service = InstantiationService(
        registry_repo=registry_repo,
        event_repo=event_repo,
        state_machine=state_machine,
        executor=executor,
        step_policy=StepExecutionPolicyService(),
    )

    plan = DeploymentPlan(
        deployment_id="dep1",
        environment_name="dev",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        actions=[
            DeploymentAction(
                action_type="PLAN_INITIAL_LOAD",
                table_id="T1",
                group_name="REP_01",
                payload={"reason": "TEST"},
            )
        ],
    )

    service.run_instantiation(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=_artifacts_dir("instantiation_success"),
        action="APPLY",
    )

    assert registry_repo.records["T1"].state == TableState.INSTANTIATED
    assert len(event_repo.events) == 1
    assert (_artifacts_dir("instantiation_success") / "instantiation_commands.sql").exists()
    assert (_artifacts_dir("instantiation_success") / "instantiation_commands.json").exists()
    assert registry_repo.records["T1"].instantiation_scn is not None


def test_instantiation_marks_error_when_executor_returns_no_result():
    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()
    state_machine = StateMachineService()
    executor = NoResultInstantiationExecutor()

    service = InstantiationService(
        registry_repo=registry_repo,
        event_repo=event_repo,
        state_machine=state_machine,
        executor=executor,
        step_policy=StepExecutionPolicyService(),
    )

    plan = DeploymentPlan(
        deployment_id="dep1",
        environment_name="dev",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        actions=[
            DeploymentAction(
                action_type="PLAN_INITIAL_LOAD",
                table_id="T1",
                group_name="REP_01",
                payload={"reason": "TEST"},
            )
        ],
    )

    result = service.run_instantiation(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=_artifacts_dir("instantiation_no_result"),
        action="PLAN_ONLY",
    )

    assert result is not None
    assert result.success is False
    assert result.error_code == "EXECUTOR_NO_RESULT"
    assert registry_repo.records["T1"].state == TableState.ERROR
    assert registry_repo.records["T1"].instantiation_scn is None
    assert any(event.event_type.value == "ERROR_OCCURRED" for event in event_repo.events)


def test_instantiation_supports_cdc_only_after_capture_attach():
    registry_repo = DummyRegistryRepo()
    registry_repo.records["T1"].state = TableState.CDC_CAPTURE_ATTACHED
    registry_repo.records["T1"].desired_replication_mode = ReplicationMode.CDC_ONLY

    event_repo = DummyEventRepo()
    state_machine = StateMachineService()
    executor = DryRunInstantiationExecutor()

    service = InstantiationService(
        registry_repo=registry_repo,
        event_repo=event_repo,
        state_machine=state_machine,
        executor=executor,
        step_policy=StepExecutionPolicyService(),
    )

    plan = DeploymentPlan(
        deployment_id="dep1",
        environment_name="dev",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        actions=[
            DeploymentAction(
                action_type="PLAN_CDC_ONLY",
                table_id="T1",
                group_name="REP_01",
                payload={"reason": "TEST"},
            )
        ],
    )

    result = service.run_instantiation(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=_artifacts_dir("instantiation_cdc_only"),
        action="APPLY",
    )

    assert result is not None
    assert result.success is True
    assert registry_repo.records["T1"].state == TableState.INSTANTIATED
    assert registry_repo.records["T1"].instantiation_scn == 123456
