from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.services.rerun_analysis_service import RerunAnalysisService


def test_rerun_analysis_marks_active_table_as_already_active():
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

    current = [
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
            state=TableState.ACTIVE,
            validation_status=ValidationStatus.PASSED,
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

    svc = RerunAnalysisService()
    report = svc.build_report(
        deployment_id="dep1",
        environment_name="dev",
        desired_configs=desired,
        current_registry=current,
    )

    assert len(report.table_statuses) == 1
    assert report.table_statuses[0].category == "ALREADY_ACTIVE"