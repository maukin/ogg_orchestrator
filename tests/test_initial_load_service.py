from pathlib import Path

from app.executors.initial_load_executor import DryRunInitialLoadExecutor
from app.models.deployment import DeploymentAction, DeploymentPlan
from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import TableRegistryRecord
from app.services.initial_load_service import InitialLoadService
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
                state=TableState.CDC_CAPTURE_ATTACHED,
                validation_status=ValidationStatus.UNKNOWN,
                prepared_for_instantiation=True,
                registration_scn=123456,
                instantiation_candidate_scn=None,
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

    def update_state(
        self,
        table_id: str,
        state: TableState,
        deployment_id: str,
        error_code=None,
        error_message=None,
    ):
        self.records[table_id].state = state

    def mark_initial_load_started(self, table_id: str, deployment_id: str):
        self.records[table_id].state = TableState.INITIAL_LOAD_RUNNING

    def mark_initial_load_done(
        self,
        table_id: str,
        deployment_id: str,
        actual_load_batch_id: str | None = None,
    ):
        self.records[table_id].state = TableState.INITIAL_LOAD_DONE
        self.records[table_id].actual_load_batch_id = actual_load_batch_id

    def mark_error(
        self,
        table_id: str,
        deployment_id: str,
        error_code: str | None,
        error_message: str | None,
    ):
        self.records[table_id].state = TableState.ERROR
        self.records[table_id].last_error_code = error_code
        self.records[table_id].last_error_message = error_message

    def set_instantiation_candidate_scn(
        self,
        table_id: str,
        deployment_id: str,
        instantiation_candidate_scn: int | None,
    ):
        self.records[table_id].instantiation_candidate_scn = instantiation_candidate_scn

class DummyEventRepo:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)


def _artifacts_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_initial_load_moves_table_to_initial_load_done():
    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()
    state_machine = StateMachineService()
    executor = DryRunInitialLoadExecutor()

    service = InitialLoadService(
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
                payload={
                    "reason": "TEST",
                    "desired_load_method": "DATAPUMP",
                },
            )
        ],
    )

    artifacts_dir = _artifacts_dir("initial_load_success")
    result = service.run_initial_load(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=artifacts_dir,
        mode="DRY_RUN",
    )

    assert result is not None
    assert result.success is True
    assert result.load_batch_id is not None
    assert registry_repo.records["T1"].state == TableState.INITIAL_LOAD_DONE
    assert len(event_repo.events) == 2
    assert (artifacts_dir / "initial_load_commands.json").exists()
    assert (artifacts_dir / "initial_load_result.json").exists()
