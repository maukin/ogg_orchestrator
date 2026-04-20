from pathlib import Path

from app.executors.prepare_source_executor import DryRunPrepareExecutor
from app.models.deployment import DeploymentAction, DeploymentPlan
from app.models.enums import (
    LoadMethod,
    ReplicationMode,
    TableState,
    ValidationStatus,
)
from app.models.registry import TableRegistryRecord
from app.services.prepare_source_service import PrepareSourceService
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
                state=TableState.PLANNED,
                validation_status=ValidationStatus.UNKNOWN,
                prepared_for_instantiation=False,
                registration_scn=None,
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

    def mark_prepared_for_instantiation(self, table_id: str, deployment_id: str, registration_scn: int):
        self.records[table_id].prepared_for_instantiation = True
        self.records[table_id].registration_scn = registration_scn

class DummyEventRepo:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)


def _artifacts_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_prepare_source_moves_table_to_prepared():
    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()
    state_machine = StateMachineService()
    executor = DryRunPrepareExecutor()

    service = PrepareSourceService(
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

    artifacts_dir = _artifacts_dir("prepare_source_success")
    service.run_prepare(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=artifacts_dir,
        mode="DRY_RUN",
    )

    assert registry_repo.records["T1"].state == TableState.PREPARED
    assert len(event_repo.events) == 2
    assert (artifacts_dir / "source_prepare_commands.sql").exists()
    assert (artifacts_dir / "source_prepare_commands.json").exists()
    assert registry_repo.records["T1"].prepared_for_instantiation is True
    assert registry_repo.records["T1"].registration_scn is not None
