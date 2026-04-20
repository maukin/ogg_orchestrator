from pathlib import Path

from app.executors.attach_extract_executor import FileOnlyAttachExtractExecutor
from app.models.deployment import DeploymentAction, DeploymentPlan
from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import TableRegistryRecord
from app.services.attach_extract_service import AttachExtractService
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
                state=TableState.PREPARED,
                validation_status=ValidationStatus.UNKNOWN,
                prepared_for_instantiation=False,
                registration_scn=None,
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

    def mark_cdc_capture_attached(self, table_id: str, deployment_id: str):
        self.records[table_id].state = TableState.CDC_CAPTURE_ATTACHED

    def mark_error(self, table_id: str, deployment_id: str, error_code, error_message):
        self.records[table_id].state = TableState.ERROR
        self.records[table_id].last_error_code = error_code
        self.records[table_id].last_error_message = error_message


class DummyEventRepo:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)


def _artifacts_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_attach_extract_moves_table_to_cdc_capture_attached():
    artifacts_dir = _artifacts_dir("attach_extract_success")
    extract_dir = artifacts_dir / "cdc" / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "EXT_01.tables.prm").write_text("TABLE SRC.ORDERS;\n", encoding="utf-8")

    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()
    service = AttachExtractService(
        registry_repo=registry_repo,
        event_repo=event_repo,
        state_machine=StateMachineService(),
        executor=FileOnlyAttachExtractExecutor(),
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

    result = service.run_attach(
        deployment_id="dep1",
        plan=plan,
        artifacts_dir=artifacts_dir,
        mode="FILE_ONLY",
    )

    assert result is not None
    assert result.success is True
    assert registry_repo.records["T1"].state == TableState.CDC_CAPTURE_ATTACHED
    assert len(event_repo.events) == 2
