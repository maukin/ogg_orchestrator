from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus, EventType
from app.models.registry import TableRegistryRecord
from app.orchestration.deployment_orchestrator import DeploymentOrchestrator
from app.services.planner_service import PlannerService
from app.services.state_machine_service import StateMachineService
from app.services.grouping_service import GroupingService
from app.services.artifact_renderer import ArtifactRenderer
from app.services.rerun_analysis_service import RerunAnalysisService
from app.services.deployment_execution_summary_service import DeploymentExecutionSummaryService
from app.services.reconciliation_service import ReconciliationService
from app.services.cdc_config_render_service import CDCConfigRenderService


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
                state=TableState.ERROR,
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
                last_error_code="X",
                last_error_message="boom",
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


class DummyEventRepo:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)


def test_replan_error_table_moves_error_to_planned():
    registry_repo = DummyRegistryRepo()
    event_repo = DummyEventRepo()

    orchestrator = DeploymentOrchestrator(
        registry_repo=registry_repo,
        event_repo=event_repo,
        deployment_repo=None,
        group_repo=None,
        planner_service=PlannerService(),
        state_machine=StateMachineService(),
        grouping_service=GroupingService(),
        artifact_renderer=ArtifactRenderer(),
        prepare_source_service=None,
        attach_extract_service=None,
        initial_load_service=None,
        instantiation_service=None,
        attach_replicat_service=None,
        activation_service=None,
        rerun_analysis_service=RerunAnalysisService(),
        deployment_execution_summary_service=DeploymentExecutionSummaryService(),
        extract_status_probe_service=None,
        replicat_status_probe_service=None,
        reconciliation_service=ReconciliationService(),
        cdc_config_render_service=CDCConfigRenderService(),
    )

    orchestrator.replan_error_table(
        table_id="T1",
        deployment_id="dep1",
    )

    assert registry_repo.records["T1"].state == TableState.PLANNED
    assert len(event_repo.events) == 1
    assert event_repo.events[0].event_type == EventType.ROLLBACK_DONE