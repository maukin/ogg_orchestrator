from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.services.reconciliation_service import ReconciliationService


class DummyProbeResult:
    def __init__(self, success: bool, error_message: str | None = None):
        self.success = success
        self.error_message = error_message
        self.error_code = "HTTP_500" if not success else None


def test_reconciliation_marks_extract_probe_failure_as_blocking():
    desired = [
        DesiredTableConfig(
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
        )
    ]

    registry = [
        TableRegistryRecord(
            table_id="SRCDB:PDB1:SRC.ORDERS->TGTDB:PDB2:DDS.ORDERS",
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
    ]

    svc = ReconciliationService()
    report = svc.build_report(
        deployment_id="dep1",
        environment_name="dev",
        desired_configs=desired,
        current_registry=registry,
        extract_probe_results={"EXT_01": DummyProbeResult(False, "Extract down")},
        replicat_probe_results={},
    )

    assert len(report.rows) == 1
    assert report.rows[0].is_blocked is True
    assert report.rows[0].block_reason == "EXTRACT_PROBE_FAILED:EXT_01"